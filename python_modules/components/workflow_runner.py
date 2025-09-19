"""
This module contains methods to run and test llm generated and adapted workflows.
"""

import attrs
import attrsx

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel, Field, create_model
import traceback
from enum import Enum


class FunctionCallOutput(BaseModel):

    output: Optional[BaseModel] = Field(default=None, description="Output of the function successful run.")
    error: Optional[WorkflowError]  = Field(default=None, description="Error during function execution.")

    model_config = {
        "arbitrary_types_allowed": True
    }

class WorkflowItem(BaseModel):

    """
    Workflow item.
    """

    name : str
    args : dict

    
class TestedWorkflow(BaseModel):
    workflow : List[WorkflowItem]
    outputs : Dict[str, BaseModel]
    error : Optional[WorkflowError]

    model_config = {
        "arbitrary_types_allowed": True
    }

@attrsx.define()
class WorkflowRunner:

    available_callables : Dict[str, callable] = attrs.field(default=None)
    available_functions : List[LlmFunctionItem] = attrs.field(default=None)

    def _run_func(self, 
        func_name : str,
        func : callable, 
        inputs : Type[BaseModel]):

        error = None
        output = None
        try:
            output = func(inputs = inputs)
        except Exception as e:
            error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_type = WorkflowErrorType.RUNNER
            error = WorkflowError(
                error_message = error_message, 
                error_type = error_type,
                additional_info = {"ffunction" : func_name})

        return FunctionCallOutput(output = output, error = error)

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
        inputs : Type[BaseModel] = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        output_model : Type[BaseModel] = None,):

        """
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

        workflow = workflow.copy()

        outputs = {}

        if inputs : 
            outputs["0"] = inputs

        error = None
        
        for workflow_item in workflow:

            try:

                func_args = self._resolve_func_args(
                    outputs = outputs,
                    func_args = workflow_item["args"])

            except Exception as e:
                error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                error_type = WorkflowErrorType.INPUTS
                error = WorkflowError(
                    error_message = error_message,
                    error_type = error_type
                )
                break


            if workflow_item["name"] != "output_model":
                
                try:
                    func_item = [av for av in available_functions \
                        if av.name == workflow_item["name"]][0]
                except Exception as e:
                    error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    error_type = WorkflowErrorType.PLANNING_HF
                    error = WorkflowError(
                        error_message = error_message,
                        error_type = error_type
                    )
                    break

                try:
                    func_inputs = self.json_schema_to_base_model(func_item.input_schema_json)(**func_args)
                except Exception as e:
                    error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    error_type = WorkflowErrorType.ADAPTOR
                    error = WorkflowError(
                        error_message = error_message,
                        error_type = error_type
                    )
                    break

                output_struct = self._run_func(
                    func_name = workflow_item["name"],
                    func = available_callables[workflow_item["name"]],
                    inputs = func_inputs
                )
                
                if output_struct.error:
                        
                    error = output_struct.error
                    break
                
                output = output_struct.output


            else:
                try:
                    output = output_model(**func_args)
                except Exception as e:
                    error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    error_type = WorkflowErrorType.OUTPUTS
                    error = WorkflowError(
                        error_message = error_message,
                        error_type = error_type
                    )
                    break


            outputs[str(workflow_item["id"])] = output


        return TestedWorkflow(workflow = workflow, outputs = outputs, error = error)

