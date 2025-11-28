"""
This module contains methods to compare two output models.
"""

import attrs
import attrsx
from copy import deepcopy

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
import traceback
from enum import Enum

from typing import Iterable, get_origin, get_args, Union
from pydantic import BaseModel
import attrs


@attrsx.define()
class OutputComparer():

    ignore_optional: bool = attrs.field(
        default=True  
    )
    max_decimals: int | None = attrs.field(
        default=None 
    )

    ignore_fields: set[str] = attrs.field(
        factory=set,
        converter=set,    
    )

    ignore_types: set[type] = attrs.field(
        factory=set,
        converter=set,
    )

    def compare_models(
        self,
        expected: BaseModel,
        actual: BaseModel,
        *,
        ignore_optional: bool | None = None,
        max_decimals: int | None = None,
        ignore_fields: Iterable[str] | None = None,
        ignore_types: Iterable[type] | None = None,
    ) -> list[str]:
        """
        Compare two Pydantic models with options:

        - ignore_optional:
            If True, Optional[...] fields are skipped when either side is None.
            If None, use the instance's ignore_optional.
        - max_decimals:
            If set, floats are rounded to this many decimal places before comparing.
            If None, use the instance's max_decimals.
        - ignore_fields:
            Iterable of field *paths* or simple names to ignore, e.g.:
                {"created_at", "inner.secret"}.
            If None, use the instance's ignore_fields.
        - ignore_types:
            Iterable of Python types (based on field annotations) to ignore, e.g.:
                {datetime, UUID, YourCustomModel}.
            Optional[...] is unwrapped before checking.
            If None, use the instance's ignore_types.
        """
        # Compute effective config (instance defaults overridden by call-level args)
        eff_ignore_optional = self.ignore_optional if ignore_optional is None else ignore_optional
        eff_max_decimals = self.max_decimals if max_decimals is None else max_decimals
        eff_ignore_fields = self.ignore_fields if ignore_fields is None else set(ignore_fields)
        eff_ignore_types = self.ignore_types if ignore_types is None else set(ignore_types)

        # Temporarily override self.* so internals can just read from self
        old_ignore_optional = self.ignore_optional
        old_max_decimals = self.max_decimals
        old_ignore_fields = self.ignore_fields
        old_ignore_types = self.ignore_types

        self.ignore_optional = eff_ignore_optional
        self.max_decimals = eff_max_decimals
        self.ignore_fields = eff_ignore_fields
        self.ignore_types = eff_ignore_types

        try:
            diffs: list[str] = []
            self._compare_models(expected, actual, "", diffs)
            return diffs
        finally:
            # Restore instance state
            self.ignore_optional = old_ignore_optional
            self.max_decimals = old_max_decimals
            self.ignore_fields = old_ignore_fields
            self.ignore_types = old_ignore_types


    @staticmethod
    def _is_optional_type(t) -> bool:
        return get_origin(t) is Union and type(None) in get_args(t)

    @staticmethod
    def _base_type_for_ignore(t):
        if get_origin(t) is Union:
            args = [a for a in get_args(t) if a is not type(None)]
            if args:
                return args[0]
        return t

    def _get_field_types(self, model: BaseModel):
        cls = model.__class__

        if hasattr(cls, "model_fields"):  # Pydantic v2
            return {name: f.annotation for name, f in cls.model_fields.items()}

        if hasattr(cls, "__fields__"):    # Pydantic v1
            return {name: f.outer_type_ for name, f in cls.__fields__.items()}

        return cls.__annotations__

    def _should_ignore_path(self, path: str) -> bool:
        if path in self.ignore_fields:
            return True

        last = path.split(".")[-1]
        if last in self.ignore_fields:
            return True

        return False

    def _should_ignore_type(self, f_type) -> bool:
        if not self.ignore_types:
            return False

        base = self._base_type_for_ignore(f_type)

        for t in self.ignore_types:
            try:
                if isinstance(base, type) and isinstance(t, type):
                    if base is t or issubclass(base, t):
                        return True
            except TypeError:
                pass

            if base == t:
                return True

        return False

    def _compare_scalar(self, left, right, path: str, diffs: list[str]):
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            if self.max_decimals is not None:
                left = round(float(left), self.max_decimals)
                right = round(float(right), self.max_decimals)

        if left != right:
            diffs.append(f"{path}: {left!r} != {right!r}")

    def _compare_values(self, left, right, path: str, diffs: list[str]):
        
        if isinstance(left, BaseModel) and isinstance(right, BaseModel):
            self._compare_models(left, right, path, diffs)
            return

        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            if len(left) != len(right):
                diffs.append(f"{path}: length mismatch {len(left)} != {len(right)}")
            for i, (l_item, r_item) in enumerate(zip(left, right)):
                self._compare_values(l_item, r_item, f"{path}[{i}]", diffs)
            return

        if isinstance(left, dict) and isinstance(right, dict):
            keys = set(left) | set(right)
            for k in keys:
                kp = f"{path}[{k!r}]"
                if k not in left:
                    diffs.append(f"{kp}: missing on expected")
                elif k not in right:
                    diffs.append(f"{kp}: missing on actual")
                else:
                    self._compare_values(left[k], right[k], kp, diffs)
            return

        self._compare_scalar(left, right, path, diffs)

    def _compare_models(self, expected: BaseModel, actual: BaseModel,
                        base_path: str, diffs: list[str]):
        field_types = self._get_field_types(expected)

        for name, f_type in field_types.items():
            path = f"{base_path}.{name}" if base_path else name

            if self._should_ignore_path(path):
                continue
            if self._should_ignore_type(f_type):
                continue

            left = getattr(expected, name)
            try:
                right = getattr(actual, name)
            except AttributeError:
                diffs.append(f"{path}: missing on actual model")
                continue

            if self.ignore_optional and self._is_optional_type(f_type):
                if left is None or right is None:
                    continue

            self._compare_values(left, right, path, diffs)