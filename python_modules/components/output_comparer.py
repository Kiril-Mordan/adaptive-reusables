"""
This module contains methods to compare two output models.
"""

from copy import deepcopy
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any, Type, Iterable, get_origin, get_args, Union

import attrs
import attrsx
from pydantic import BaseModel


@attrsx.define()
class OutputComparer:
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
        workflow : List[dict] = None,
        *,
        ignore_optional: bool | None = None,
        max_decimals: int | None = None,
        ignore_fields: Iterable[str] | None = None,
        ignore_types: Iterable[type] | None = None,
    ) -> list[Dict[str, Any]]:
        """
        Compare two Pydantic models and return a list of diff dictionaries.

        Each diff entry has the shape:

            {
                "path": str,              # field path, e.g. "a.b[0]['c']"
                "diff_type": str,         # one of:
                                         #   "value_mismatch"
                                         #   "length_mismatch"
                                         #   "missing_in_expected"
                                         #   "missing_in_actual"
                "expected": Any,          # expected value (or length, or None if missing)
                "actual": Any,            # actual value (or length, or None if missing)
            }

        Options:

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
            diffs: list[Dict[str, Any]] = []
            self._compare_models(expected, actual, "", diffs)

            if workflow:
                diffs = [{**d, 
                "output" : workflow[len(workflow)-1]['args'][self._get_source_key(d["path"])],
                "source_step_id" : self._get_step_id_for_path(path = self._get_source_key(d["path"]), workflow = workflow), 
                "source" : self.classify_diff_item(path = d["path"], workflow = workflow)} for d in diffs]
            return diffs
        finally:
            # Restore instance state
            self.ignore_optional = old_ignore_optional
            self.max_decimals = old_max_decimals
            self.ignore_fields = old_ignore_fields
            self.ignore_types = old_ignore_types

    # ---------- helpers for classifying diff ----------

    
    def classify_diff_item(self, workflow, path):

        output_source, output_source_loc = self._get_source_from_path(workflow=workflow, path=path)

        output_source_c = self._classify_source(output_source = output_source)

        label = self._process_cs(output_source = output_source_c, app = output_source_loc)

        return label

    def _get_step_id_for_path(self,workflow, path):

        output = workflow[len(workflow)-1]['args'][path]

        step_id = -1

        if isinstance(output, list) or isinstance(output, dict):
            return step_id

        splits = output.split(".")
        if len(splits) > 1:
            step_id = int(splits[0])

            return step_id


    def _classify_source_item(self, output_source : str):

        if output_source.startswith("0.output"):
            return "user_input"

        if ".output." in output_source:
            return "function_output"

        return "llm_input"

    def _classify_source(self, output_source):

        if isinstance(output_source, list):
            return [self._classify_source(output_source=osi) for osi in output_source]

        if isinstance(output_source, dict):
            return {k : self._classify_source(output_source=v) for k,v in output_source.items()}

        if isinstance(output_source, str):
            return self._classify_source_item(output_source = output_source)

    def _process_cs(self, output_source, app):

        if app:

            apps = app.split(".")

            for a in apps:

                if "[" in a:
                    output_source = output_source[int(a.replace("[", "").replace("]", ""))] 
                elif "." in a:
                    output_source = output_source[a.replace(".", "")] 
                else:
                    output_source = output_source[a] 

        return output_source

    def _get_dir_source_from_path(self, workflow, path):

        split_conds = ["[", "."]

        for split_cond in split_conds:

            fields = path.split(split_cond)
            if len(fields) > 1:
                app = fields[1:]
                if split_cond in ["["]:
                    return split_cond + split_cond.join(app)
                return split_cond.join(app)

        return None

    def _get_source_from_path(self, workflow, path):

        field = self._get_source_key(path = path)

        app = self._get_dir_source_from_path(workflow = workflow, path = path)

        return workflow[-1]['args'][field] , app

    def _get_source_key(self, path):

        fields = path.split("[")

        if len(fields) == 1:
            fields = path.split(".")

        field = fields[0]

        return field

    # ---------- helpers for diff collection ----------

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
                # in case base or t are not class-like
                pass

            if base == t:
                return True

        return False

    def _add_diff(
        self,
        diffs: list[Dict[str, Any]],
        *,
        path: str,
        diff_type: str,
        expected: Any,
        actual: Any,
    ) -> None:
        diffs.append(
            {
                "path": path,
                "diff_type": diff_type,
                "expected": expected,
                "actual": actual,
            }
        )

    def _compare_scalar(self, left, right, path: str , diffs: list[Dict[str, Any]]):
        # Handle numeric rounding if configured
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            if self.max_decimals is not None:
                left = round(float(left), self.max_decimals)
                right = round(float(right), self.max_decimals)

        if left != right:
            self._add_diff(
                diffs,
                path=path,
                diff_type="value_mismatch",
                expected=left,
                actual=right,
            )

    def _compare_values(self, left, right, path: str, diffs: list[Dict[str, Any]]):
        # Nested models
        if isinstance(left, BaseModel) and isinstance(right, BaseModel):
            self._compare_models(left, right, path, diffs)
            return

        # Sequences
        if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
            if len(left) != len(right):
                self._add_diff(
                    diffs,
                    path=path,
                    diff_type="length_mismatch",
                    expected=len(left),
                    actual=len(right),
                )
            for i, (l_item, r_item) in enumerate(zip(left, right)):
                self._compare_values(l_item, r_item, f"{path}[{i}]", diffs)
            return

        # Dicts
        if isinstance(left, dict) and isinstance(right, dict):
            keys = set(left) | set(right)
            for k in keys:
                kp = f"{path}[{k!r}]"
                if k not in left:
                    # missing on expected
                    self._add_diff(
                        diffs,
                        path=kp,
                        diff_type="missing_in_expected",
                        expected=None,
                        actual=right.get(k),
                    )
                elif k not in right:
                    # missing on actual
                    self._add_diff(
                        diffs,
                        path=kp,
                        diff_type="missing_in_actual",
                        expected=left.get(k),
                        actual=None,
                    )
                else:
                    self._compare_values(left[k], right[k], kp, diffs)
            return

        # Fallback scalar comparison
        self._compare_scalar(left, right, path, diffs)

    def _compare_models(
        self,
        expected: BaseModel,
        actual: BaseModel,
        base_path: str,
        diffs: list[Dict[str, Any]],
    ):
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
                # field missing on actual model
                self._add_diff(
                    diffs,
                    path=path,
                    diff_type="missing_in_actual",
                    expected=left,
                    actual=None,
                )
                continue

            if self.ignore_optional and self._is_optional_type(f_type):
                if left is None or right is None:
                    # skip Optional[...] comparisons where one side is None
                    continue

            self._compare_values(left, right, path, diffs)
