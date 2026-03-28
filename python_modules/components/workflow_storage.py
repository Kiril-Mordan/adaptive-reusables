"""
This module contains methods to serialize and deserialize assembled workflows
without requiring component-to-component imports for concrete error models.
"""

from datetime import datetime, timezone
from enum import Enum
import importlib
import json
from pathlib import Path
from typing import Any

import attrs
import attrsx
from pydantic import BaseModel, Field, create_model


class SerializedWorkflowPayload(BaseModel):
    """Container for serialized workflow data."""

    payload: dict = Field(description="Serialized workflow payload.")


@attrsx.define()
class WorkflowStorage:
    """Serialize workflow objects into JSON-safe payloads and restore them."""

    workflow_error_types = attrs.field()
    workflow_error = attrs.field()
    model_class = attrs.field(default=None)
    workflow_cache = attrs.field(factory=dict)

    def _resolve_model_class(self, model_class: type[BaseModel] | None) -> type[BaseModel]:
        resolved_model_class = model_class or self.model_class
        if resolved_model_class is None:
            raise ValueError("model_class must be provided either at initialization or per method call.")
        return resolved_model_class

    def _make_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    def _get_storage_dir(self, storage_path: str | Path) -> Path:
        workflows_dir = Path(storage_path) / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        return workflows_dir

    def _sort_candidate_paths(self, paths: list[Path]) -> list[Path]:
        return sorted(paths, key=lambda path: path.name, reverse=True)

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return self._serialize_model(value)

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, dict):
            return {key: self._serialize_value(item) for key, item in value.items()}

        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]

        if isinstance(value, tuple):
            return [self._serialize_value(item) for item in value]

        return value

    def _serialize_model(self, model: BaseModel) -> dict:
        fields = {}
        for field_name in model.__class__.model_fields:
            fields[field_name] = self._serialize_value(getattr(model, field_name))

        return {
            "__workflow_storage__": "pydantic_model",
            "module": model.__class__.__module__,
            "name": model.__class__.__name__,
            "schema": model.model_json_schema(),
            "data": fields,
        }

    def serialize(self, workflow_object: BaseModel) -> dict:
        """Return a JSON-safe dictionary for an assembled workflow object."""

        return self._serialize_value(workflow_object)

    def serialize_json(self, workflow_object: BaseModel, **kwargs) -> str:
        """Return a JSON string for an assembled workflow object."""

        return json.dumps(self.serialize(workflow_object), **kwargs)

    def _json_schema_to_model(self, schema: dict) -> type[BaseModel]:
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        defs = {}
        for def_name, def_schema in schema.get("$defs", {}).items():
            fields = {}
            for name, prop in def_schema.get("properties", {}).items():
                py_type = type_mapping.get(prop.get("type", "string"), Any)
                default = ... if name in def_schema.get("required", []) else prop.get("default", None)
                if default is None and name not in def_schema.get("required", []):
                    py_type = py_type | None

                fields[name] = (
                    py_type,
                    Field(default, title=prop.get("title"), description=prop.get("description")),
                )
            defs[def_name] = create_model(def_schema["title"], **fields)

        fields = {}
        for name, prop in schema.get("properties", {}).items():
            if "$ref" in prop.get("items", {}):
                ref_name = prop["items"]["$ref"].split("/")[-1]
                py_type = list[defs[ref_name]]
                default = ... if name in schema.get("required", []) else None
            elif "$ref" in prop:
                ref_name = prop["$ref"].split("/")[-1]
                py_type = defs[ref_name]
                default = ... if name in schema.get("required", []) else None
            else:
                py_type = type_mapping.get(prop.get("type", "string"), Any)
                default = ... if name in schema.get("required", []) else prop.get("default", None)
                if default is None and name not in schema.get("required", []):
                    py_type = py_type | None

            fields[name] = (
                py_type,
                Field(default, title=prop.get("title"), description=prop.get("description")),
            )

        return create_model(schema["title"], **fields)

    def _load_model_class(self, module_name: str, class_name: str, schema: dict) -> tuple[type[BaseModel], bool]:
        if class_name == getattr(self.workflow_error, "__name__", None):
            return self.workflow_error, False

        try:
            module = importlib.import_module(module_name)
            model_class = getattr(module, class_name)
            if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                return model_class, False
        except (ImportError, AttributeError, TypeError):
            pass

        return self._json_schema_to_model(schema), True

    def _deserialize_plain_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            marker = value.get("__workflow_storage__")
            if marker == "pydantic_model":
                return {
                    key: self._deserialize_plain_value(item)
                    for key, item in value.get("data", {}).items()
                }

            return {key: self._deserialize_plain_value(item) for key, item in value.items()}

        if isinstance(value, list):
            return [self._deserialize_plain_value(item) for item in value]

        return value

    def _deserialize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            marker = value.get("__workflow_storage__")
            if marker == "pydantic_model":
                model_class, is_fallback_model = self._load_model_class(
                    module_name=value["module"],
                    class_name=value["name"],
                    schema=value["schema"],
                )
                if is_fallback_model:
                    model_data = {
                        key: self._deserialize_plain_value(item)
                        for key, item in value.get("data", {}).items()
                    }
                else:
                    model_data = {
                        key: self._deserialize_value(item)
                        for key, item in value.get("data", {}).items()
                    }
                return model_class.model_validate(model_data)

            return {key: self._deserialize_value(item) for key, item in value.items()}

        if isinstance(value, list):
            return [self._deserialize_value(item) for item in value]

        return value

    def deserialize(self, payload: dict, model_class: type[BaseModel] | None = None) -> BaseModel:
        """Restore a serialized workflow payload into the provided model class."""

        model_class = self._resolve_model_class(model_class)
        restored = self._deserialize_value(payload)
        if isinstance(restored, model_class):
            return restored
        return model_class.model_validate(restored)

    def deserialize_json(self, payload: str, model_class: type[BaseModel] | None = None) -> BaseModel:
        """Restore a serialized workflow payload from a JSON string."""

        return self.deserialize(json.loads(payload), model_class=model_class)

    def add_to_cache(self, workflow_object: BaseModel):
        """Add a workflow object to the in-memory cache keyed by input_id."""

        input_id = getattr(workflow_object, "input_id", None)
        if input_id is None:
            raise ValueError("Workflow object must define input_id to be cached.")

        self.workflow_cache[input_id] = workflow_object
        return workflow_object

    def save_workflow(
        self,
        workflow_object: BaseModel,
        storage_path: str | Path,
        indent: int = 2,
    ) -> Path:
        """Persist a workflow object to disk and update cache."""

        workflows_dir = self._get_storage_dir(storage_path=storage_path)
        timestamp = self._make_timestamp()

        workflow_to_save = workflow_object.model_copy(deep=True)
        if hasattr(workflow_to_save, "saved_at"):
            workflow_to_save.saved_at = timestamp

        input_id = getattr(workflow_to_save, "input_id", None)
        workflow_id = getattr(workflow_to_save, "id", None)
        if input_id is None or workflow_id is None:
            raise ValueError("Workflow object must define input_id and id to be saved.")

        filepath = workflows_dir / f"{input_id}_{workflow_id}_{timestamp}.json"
        filepath.write_text(
            self.serialize_json(workflow_to_save, indent=indent),
            encoding="utf-8",
        )

        self.add_to_cache(workflow_to_save)
        return filepath

    def _get_candidate_paths(
        self,
        storage_path: str | Path,
        input_id: str,
    ) -> list[Path]:
        workflows_dir = self._get_storage_dir(storage_path=storage_path)
        candidates = list(workflows_dir.glob(f"{input_id}_*.json"))
        return self._sort_candidate_paths(candidates)

    def load_latest_workflow(
        self,
        storage_path: str | Path,
        input_id: str,
        model_class: type[BaseModel] | None = None,
    ) -> BaseModel | None:
        """Load the newest stored workflow for the provided input_id."""

        model_class = self._resolve_model_class(model_class)
        candidate_paths = self._get_candidate_paths(storage_path=storage_path, input_id=input_id)
        if not candidate_paths:
            return None

        workflow_object = self.deserialize_json(
            candidate_paths[0].read_text(encoding="utf-8"),
            model_class=model_class,
        )
        self.add_to_cache(workflow_object)
        return workflow_object

    def load_latest_complete_workflow(
        self,
        storage_path: str | Path,
        input_id: str,
        model_class: type[BaseModel] | None = None,
    ) -> BaseModel | None:
        """Load the newest completed workflow for the provided input_id."""

        model_class = self._resolve_model_class(model_class)
        candidate_paths = self._get_candidate_paths(storage_path=storage_path, input_id=input_id)
        for candidate_path in candidate_paths:
            workflow_object = self.deserialize_json(
                candidate_path.read_text(encoding="utf-8"),
                model_class=model_class,
            )
            if getattr(workflow_object, "workflow_completed", False):
                self.add_to_cache(workflow_object)
                return workflow_object

        return None

    def _discover_input_ids(self, storage_path: str | Path) -> list[str]:
        workflows_dir = self._get_storage_dir(storage_path=storage_path)
        return sorted({
            parts[0]
            for filepath in workflows_dir.glob("*.json")
            for parts in [filepath.stem.rsplit("_", 2)]
            if len(parts) == 3
        })

    def load_workflows_to_cache(
        self,
        storage_path: str | Path,
        input_ids: list[str] | None,
        model_class: type[BaseModel] | None = None,
        latest_complete: bool = True,
    ) -> dict[str, BaseModel]:
        """Load workflows for provided input ids or all stored ids into the in-memory cache."""

        model_class = self._resolve_model_class(model_class)
        target_input_ids = input_ids if input_ids is not None else self._discover_input_ids(storage_path=storage_path)
        loader = self.load_latest_complete_workflow if latest_complete else self.load_latest_workflow

        loaded_items = [
            (
                input_id,
                loader(
                    storage_path=storage_path,
                    input_id=input_id,
                    model_class=model_class,
                ),
            )
            for input_id in target_input_ids
        ]

        return {
            input_id: workflow_object
            for input_id, workflow_object in loaded_items
            if workflow_object is not None
        }
