"""
This module contains methods to run and test llm generated and adapted workflows.
"""

import attrs
import attrsx

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, create_model


class LlmFunctionItem(BaseModel):

    """
    Function suitable for llm use. 
    """

    name : str
    description : str
    input_schema_json : dict
    output_schema_json : dict


@attrsx.define()
class WorkflowRunner:

    available_callables : Dict[str, callable] = attrs.field(default=None)
    available_functions : List[LlmFunctionItem] = attrs.field(default=None)

    def _run_func(self, 
        func : callable, 
        inputs : type(BaseModel)):

        output = func(inputs = inputs)

        return output

    def _resolve_func_args(self, 
        outputs: Dict[str, BaseModel], 
        func_args: Any) -> Any:
        
        if isinstance(func_args, dict):
            return {k: self._resolve_func_args(outputs, v) for k, v in func_args.items()}
        
        elif isinstance(func_args, list):
            return [self._resolve_func_args(outputs, v) for v in func_args]
        
        elif isinstance(func_args, str) and ".output." in func_args:
            try:
                step_id, path = func_args.split(".output.", 1)
                obj = outputs[step_id]
                for attr in path.split("."):
                    obj = getattr(obj, attr)
                return obj
            except Exception as e:
                raise ValueError(f"Failed to resolve reference '{func_args}': {e}")
        
        return func_args

    def json_schema_to_base_model(self, schema: dict) -> Dict[str, BaseModel]:
        """Build Pydantic models from a JSON schema with $defs and $ref."""

        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        defs = {}

        # build inline nested models
        for def_name, def_schema in schema.get("$defs", {}).items():
            fields = {}
            for name, prop in def_schema["properties"].items():
                py_type = type_mapping.get(prop.get("type", "string"), Any)
                default = ... if name in def_schema.get("required", []) else prop.get("default", None)
                if default is None and name not in def_schema.get("required", []):
                    py_type = Optional[py_type]

                fields[name] = (
                    py_type,
                    Field(default, title=prop.get("title"), description=prop.get("description"))
                )
            defs[def_name] = create_model(def_schema["title"], **fields)

        # now build the top-level model
        fields = {}
        for name, prop in schema["properties"].items():
            if "$ref" in prop.get("items", {}):  # array of nested objects
                ref_name = prop["items"]["$ref"].split("/")[-1]
                py_type = List[defs[ref_name]]
                default = ... if name in schema.get("required", []) else None
            else:
                py_type = type_mapping.get(prop.get("type", "string"), Any)
                default = ... if name in schema.get("required", []) else prop.get("default", None)
                if default is None and name not in schema.get("required", []):
                    py_type = Optional[py_type]

            fields[name] = (
                py_type,
                Field(default, title=prop.get("title"), description=prop.get("description"))
            )

        return create_model(schema["title"], **fields)

    def run_workflow(self, 
        workflow : List[dict], 
        inputs : type(BaseModel) = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        #input_model : type(BaseModel) = None,
        output_model : type(BaseModel) = None,):

        """s
        Runs llm planned workflow with provided inputs.
        """

        if available_functions is None:
            available_functions = self.available_functions

        if available_callables is None:
            available_callables = self.available_callables

        if available_functions is None:
            raise ValueError("Input available_functions : List[LlmFunctionItem] cannot be None!")

        if available_callables is None:
            raise ValueError("Input available_callables : Dict[str, callable] cannot be None!")

        if output_model:
            available_callables["output_model"] = output_model

        outputs = {}

        if inputs : 
            outputs["0"] = inputs

        for workflow_item in workflow:


            func_args = self._resolve_func_args(
                outputs = outputs,
                func_args = workflow_item["args"])


            if workflow_item["name"] != "output_model":

                func_item = [av for av in available_functions \
                    if av.name == workflow_item["name"]][0]

                func_inputs = self.json_schema_to_base_model(func_item.input_schema_json)(**func_args)

                output = self._run_func(
                    func = available_callables[workflow_item["name"]],
                    inputs = func_inputs
                )

            else:
                output = output_model(**func_args)

            outputs[str(workflow_item["id"])] = output


        return outputs
