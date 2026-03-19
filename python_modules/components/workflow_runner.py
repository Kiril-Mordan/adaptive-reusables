"""
This module contains methods to run and test llm generated and adapted workflows.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
import traceback
from typing import List, Optional, Dict, Any, Type, Iterable, Callable

import attrs
import attrsx
from pydantic import BaseModel, Field, create_model


@attrs.define(kw_only=True)
class OutputComparerMock(ABC):
    """Interface for comparing expected and actual outputs."""

    @abstractmethod
    def compare_models(
        self,
        expected: BaseModel,
        actual: BaseModel,
        *args,
        ignore_optional: bool = True,
        max_decimals: int | None = None,
        ignore_fields: Iterable[str] | None = None,
        ignore_types: Iterable[type] | None = None,
        **kwargs,
    ) -> list[str]:

        """
        Abstract method for comparing two outputs within pydantic models.
        """

        raise NotImplementedError

class FunctionCallOutput(BaseModel):
    """Output container for a single function execution."""

    output: Optional[BaseModel] = Field(default=None, description="Output of the function successful run.")
    error: Optional[BaseModel]  = Field(default=None, description="Error during function execution.")

    model_config = {
        "arbitrary_types_allowed": True
    }

class WorkflowItem(BaseModel):

    """
    Workflow item.
    """

    name : str = Field(description="Name of workflow step.")
    args : Optional[dict] = Field(description="Inputs for workflow step.")

    
class TestedWorkflow(BaseModel):
    """Results for a single workflow run."""

    workflow : List[WorkflowItem] = Field(description="Planned and tested workflow.")
    inputs : BaseModel = Field(description="Inputs for test run.")
    outputs : Dict[str, BaseModel] = Field(description="Outputs from test run.")
    error : Optional[BaseModel] = Field(default = None, description="Error that happened during last run/test.")

    model_config = {
        "arbitrary_types_allowed": True
    }

class TestedWorkflowBatch(BaseModel):
    """Batch results for multiple workflow runs."""

    workflow : List[WorkflowItem] = Field(description="Planned and tested workflow.")
    case_results : List[TestedWorkflow] = Field(description="Per-case workflow run results.")
    error : Optional[BaseModel] = Field(default = None, description="Aggregated error for all cases.")

    model_config = {
        "arbitrary_types_allowed": True
    }

@attrsx.define(handler_specs = {"output_comparer" : OutputComparerMock})
class WorkflowRunner:  # pylint: disable=not-callable
    """Runs and validates assembled workflows."""

    workflow_error_types = attrs.field()
    workflow_error: Callable[..., BaseModel] = attrs.field()

    
    available_functions: List[Any] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else deepcopy(v),
    )

    available_callables: Dict[str, Callable] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else dict(v),
    )

    def __attrs_post_init__(self):

        self._initialize_output_comparer_h()

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
            error_type = self.workflow_error_types.RUNNER
            error = self.workflow_error(
                error_message = error_message, 
                error_type = error_type,
                additional_info = {"ffunction" : func_name})

        return FunctionCallOutput(output = output, error = error)

    def _resolve_func_args(self, 
        outputs: Dict[str, BaseModel], 
        func_args: Any) -> Any:
        
        if isinstance(func_args, dict):
            return {k: self._resolve_func_args(outputs, v) for k, v in func_args.items()}
        
        if isinstance(func_args, list):
            return [self._resolve_func_args(outputs, v) for v in func_args]
        
        if isinstance(func_args, str) and ".output." in func_args:
            try:
                step_id, path = func_args.split(".output.", 1)
                obj = outputs[step_id]
                for attr in path.split("."):
                    obj = getattr(obj, attr)
                return obj
            except (KeyError, AttributeError, IndexError, TypeError, ValueError) as e:
                raise ValueError(f"Failed to resolve reference '{func_args}': {e}") from e
        
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

    def _run_single_case(self, 
        workflow : List[dict], 
        inputs : Type[BaseModel] = None,
        expected_outputs : Type[BaseModel] = None,
        compare_params : dict = None,
        available_functions : List[Any] = None,
        available_callables : Dict[str, callable] = None,
        output_model : Type[BaseModel] = None) -> TestedWorkflow:

        """
        Runs llm planned workflow with provided inputs for a single test case.
        """

        if available_functions is None:
            available_functions = self.available_functions

        if available_callables is None:
            available_callables = self.available_callables

        if available_functions is None:
            raise ValueError("Input available_functions cannot be None!")

        if available_callables is None:
            raise ValueError("Input available_callables : Dict[str, callable] cannot be None!")

        if output_model:
            available_callables["output_model"] = output_model

        if compare_params is None:
            compare_params = {}

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

                if func_args is None:
                    func_args = {}

            except (KeyError, IndexError, TypeError, ValueError) as e:
                error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                error_type = self.workflow_error_types.INPUTS
                error = self.workflow_error(
                    error_message = error_message,
                    error_type = error_type,
                    additional_info = {
                            "step_id" : workflow_item["id"],
                            "error_messages" : [error_message]}
                    
                )
                break


            if workflow_item["name"] != "output_model":
                
                try:
                    func_item = [av for av in available_functions \
                        if av.func_id == workflow_item["func_id"]][0]
                except (IndexError, KeyError, TypeError, ValueError) as e:
                    error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    error_type = self.workflow_error_types.PLANNING_HF
                    error = self.workflow_error(
                        error_message = error_message,
                        error_type = error_type
                    )
                    break

                try:
                    func_inputs = self.json_schema_to_base_model(func_item.input_schema_json)(**func_args)
                except (TypeError, ValueError) as e:
                    error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    error_type = self.workflow_error_types.ADAPTOR_JSON
                    error = self.workflow_error(
                        error_message = None,
                        error_type = error_type,
                        additional_info = {
                            "step_id" : workflow_item["id"],
                            "error_messages" : [error_message]}
                    )
                    break

                output_struct = self._run_func(
                    func_name = workflow_item["name"],
                    func = available_callables[workflow_item["func_id"]],
                    inputs = func_inputs
                )
                
                if output_struct.error:
                        
                    error = output_struct.error
                    break
                
                output = output_struct.output


            else:
                try:
                    output = output_model(**func_args)
                except (TypeError, ValueError) as e:
                    error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    error_type = self.workflow_error_types.OUTPUTS_FAILURE
                    error = self.workflow_error(
                        error_message = error_message,
                        error_type = error_type,
                        additional_info = {
                            "step_id" : workflow_item["id"],
                            "error_messages" : [error_message]}
                    )
                    break


            outputs[str(workflow_item["id"])] = output

        if expected_outputs is not None and error is None:

            differences = self.output_comparer_h.compare_models(
                expected = expected_outputs,
                actual = output,
                workflow = workflow,
                **compare_params
            )

            if differences:
                failing_step_ids = [
                    d.get("source_step_id")
                    for d in differences
                    if isinstance(d.get("source_step_id"), int) and d.get("source_step_id") >= 1
                ]
                step_id = failing_step_ids[0] if failing_step_ids else len(workflow)
                error_type = self.workflow_error_types.OUTPUTS_UNEXPECTED
                error = self.workflow_error(
                        error_message = "Actual outputs do not match expected!",
                        error_type = error_type,
                        additional_info = {
                            "step_id" : step_id,
                            "differences" : differences,
                            "failing_step_ids" : failing_step_ids}
                    )

        return TestedWorkflow(
            workflow = workflow, 
            inputs = inputs,
            outputs = outputs, 
            error = error)

    def run_workflow(self, 
        workflow : List[dict], 
        test_params : List[Dict[str, Type[BaseModel]]] = None,
        inputs : Type[BaseModel] = None,
        expected_outputs : Type[BaseModel] = None,
        compare_params : dict = None,
        available_functions : List[Any] = None,
        available_callables : Dict[str, callable] = None,
        output_model : Type[BaseModel] = None) -> TestedWorkflow | TestedWorkflowBatch:

        """
        Runs llm planned workflow with provided inputs.
        Returns TestedWorkflow for single-case or TestedWorkflowBatch for multi-case.
        """
        if test_params and (inputs is not None or expected_outputs is not None):
            raise ValueError("Provide either test_params or (inputs, expected_outputs), not both.")

        if test_params:
            case_results = []
            failed_cases = []
            differences_by_case = []
            failing_step_ids = []

            for idx, case in enumerate(test_params):
                case_result = self._run_single_case(
                    workflow = workflow,
                    inputs = case.get("inputs"),
                    expected_outputs = case.get("outputs"),
                    compare_params = compare_params,
                    available_functions = available_functions,
                    available_callables = available_callables,
                    output_model = output_model
                )

                case_results.append(case_result)
                if case_result.error is not None:
                    failed_cases.append(idx)
                    error_info = getattr(case_result.error, "additional_info", None)
                    if isinstance(error_info, dict):
                        differences = error_info.get("differences")
                        if differences:
                            differences_by_case.append({"case_id": idx, "differences": differences})
                        step_id = error_info.get("step_id")
                        if step_id is not None:
                            failing_step_ids.append(step_id)

            aggregated_error = None
            if failed_cases:
                error_types = []
                for case in case_results:
                    if case.error is not None:
                        error_types.append(getattr(case.error, "error_type", None))

                error_type = None
                if error_types:
                    error_type = error_types[0]
                    if any(et != error_type for et in error_types):
                        # Mixed failure modes across cases; collapse to a generic unexpected-outputs error.
                        error_type = self.workflow_error_types.OUTPUTS_UNEXPECTED
                else:
                    error_type = self.workflow_error_types.OUTPUTS_UNEXPECTED

                aggregated_error = self.workflow_error(
                    error_message = "One or more test cases failed.",
                    error_type = error_type,
                    additional_info = {
                        "failed_cases": failed_cases,
                        "differences_by_case": differences_by_case,
                        "failing_step_ids": failing_step_ids,
                        "error_types_by_case": error_types
                    }
                )

            return TestedWorkflowBatch(
                workflow = workflow,
                case_results = case_results,
                error = aggregated_error
            )

        return self._run_single_case(
            workflow = workflow,
            inputs = inputs,
            expected_outputs = expected_outputs,
            compare_params = compare_params,
            available_functions = available_functions,
            available_callables = available_callables,
            output_model = output_model
        )
