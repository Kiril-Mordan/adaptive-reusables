"""
Workflow Auto Assembler (WAA) is an experimental schema-first workflow synthesis tool.
It uses an LLM to assemble simple executable workflows from a task description, target
input/output models, and a catalog of available typed tools.

WAA is built around a narrow idea: instead of asking the model to solve a task
directly, expose tools through explicit schemas and let the model construct a linear
workflow whose intermediate states can be validated and tested. The resulting workflow
is persisted as an explicit artifact with I/O mappings, which makes it inspectable,
re-runnable, and easier to validate than a transient agent trace.

### Why Workflow-Auto-Assembler?

WAA treats tool selection and wiring as a schema-matching problem. When the required
capabilities exist in the available tool catalog, the assembled workflow can behave
like a larger typed function composed from smaller typed functions.

This package should be read as experimental adaptive tooling rather than a claim of
general autonomous planning. Its strongest use case is simple linear workflow assembly
under explicit schema constraints, with runner-based validation used to check that the
assembled workflow satisfies the requested output contract.
"""

import attrs
import attrsx

import uuid
import json
from copy import deepcopy
from typing import Type, Optional, List, Dict, Callable
from pydantic import BaseModel, Field

from .components.wa_general_models import (
    LlmFunctionItem, 
    WorkflowErrorType, 
    WorkflowError, 
    create_avc_items, 
    LlmFunctionItemInput, 
    make_uid)
from .components.llm_handler import LlmHandler
from .components.workflow_check import WorkflowCheck, WorkflowCheckResponse
from .components.workflow_planner import WorkflowPlanner, WorkflowPlannerResponse
from .components.workflow_adaptor import WorkflowAdaptor, WorkflowAdaptorResponse
from .components.input_collector import InputCollector
from .components.output_comparer import OutputComparer
from .components.workflow_runner import WorkflowRunner, TestedWorkflow, TestedWorkflowBatch

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "Experimental schema-first workflow synthesis tool for assembling simple typed workflows from existing functions.",
}

class PlanningStepsResp(BaseModel):
    planner : Optional[WorkflowPlannerResponse] = Field(default = None, description = "Planning steps of workflow creation.")
    planner_iters : Optional[List[WorkflowPlannerResponse]] = Field(default = [], description = "Snapshot of planning steps of workflow creation at each reset.")
    adaptor : Optional[WorkflowAdaptorResponse] = Field(default = None, description = "Adapting steps of workflow creation.")
    adaptor_iters : Optional[List[WorkflowAdaptorResponse]] = Field(default = [], description = "Snapshot of adapting steps of workflow creation at each reset.")
    tester : Optional[TestedWorkflow | TestedWorkflowBatch] = Field(default = None, description = "Testing step of workflow creation.") 
    planner_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if planner needs reset during retry.")
    adaptor_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if adaptor needs reset during retry.")
    testing_errors : Optional[List[WorkflowError]] = Field(default = [], description = "Errors during testing workflow.")
    test_retries : int = Field(default = 0, description = "Retries completed during planning and testing loop.")

class WorkflowDescription(BaseModel):
    task_description : Optional[str] = Field(default = None, description="Description of the workflow.")
    input_model_json : Optional[dict] = Field(default = None, description="Input model for workflow.")
    output_model_json : Optional[dict] = Field(default = None, description="Output model for workflow.")

class AssembledWorkflow(BaseModel):
    id : str = Field(description = "Unique id for task based on hash of inputs")
    input_id : str = Field(description = "Unique id for task inputs based on hash of inputs")
    init_check : Optional[WorkflowCheckResponse] = Field(default = None, description = "Initial check.")
    planning : Optional[PlanningStepsResp] = Field(default = PlanningStepsResp(), description = "Responses from planning steps.")
    workflow_possible : Optional[bool] = Field(default = None, description = "Indicates if workflow could be planned given provided tools.")
    workflow_completed : Optional[bool] = Field(default = False, description = "Indicates if workflow was completed in the preset amount of retries.")
    workflow : Optional[dict] = Field(default = None, description = "Planned and tested workflow.")
    description : Optional[WorkflowDescription] = Field(default = WorkflowDescription(), description = "Workflow description.")
    loops : Optional[int] = Field(default = 1, description = "Retries completed during planning and testing loop.")

@attrsx.define(handler_specs = {
        #"shouter" : Shouter,
        "llm_handler" : LlmHandler,
        "check" : WorkflowCheck,
        "planner" : WorkflowPlanner,
        "adaptor" : WorkflowAdaptor,
        "runner" : WorkflowRunner,
        "input_collector" : InputCollector,
        "output_comparer" : OutputComparer
    },
    logger_chaining={
        #'loggerLvl' : True
        'logger' : True
        })
class WorkflowAutoAssembler:

    workflow_error_types = attrs.field(default=WorkflowErrorType)
    workflow_error = attrs.field(default=WorkflowError)

    available_functions: List[LlmFunctionItem] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else deepcopy(v),
    )
    available_callables: Dict[str, Callable] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else dict(v),
    )

    max_output_unexpected : int = attrs.field(default=3)
    max_retry : int = attrs.field(default=10)
    reset_loops : int = attrs.field(default=2)

    def __attrs_post_init__(self):

        self._initialize_input_collector_h()
        
        self._initialize_output_comparer_h()
        self._initialize_llm_handler_h()
        self._initialize_planner_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "available_functions" : self.available_functions,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "max_retry" : self.max_retry
        })
        self._initialize_adaptor_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "input_collector_h" : self.input_collector_h,
            "available_functions" : self.available_functions,
            "llm_function_item_class" : LlmFunctionItem,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "max_retry" : self.max_retry
        })
        self._initialize_runner_h(uparams = {
            "output_comparer_h" : self.output_comparer_h,
            "available_functions" : self.available_functions,
            "available_callables" : self.available_callables,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
        })
        self._initialize_check_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "available_functions" : self.available_functions,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "max_retry" : self.max_retry
        })

    def _update_reset_logic(self, wa_resp : AssembledWorkflow):

        tester_error = None
        if wa_resp.planning.tester is not None:
            tester_error = wa_resp.planning.tester.error

        if tester_error is None:
            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = False
            wa_resp.workflow_completed = True
            self.logger.debug(f"Workflow completed after {wa_resp.planning.test_retries + 1} planning loops!")

            return wa_resp

        self.logger.debug(f"Updating reset logic based on error: {tester_error}",
                          label = tester_error.error_type.name,
                          save_vars = ["wa_resp.planning.tester.error"])

        if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
            if "differences_by_case" in tester_error.additional_info and "differences" not in tester_error.additional_info:
                flat_differences = []
                for case_diff in tester_error.additional_info.get("differences_by_case", []):
                    case_id = case_diff.get("case_id")
                    for diff in case_diff.get("differences", []):
                        diff_item = dict(diff)
                        diff_item["case_id"] = case_id
                        flat_differences.append(diff_item)
                tester_error.additional_info["differences"] = flat_differences

        wa_resp.planning.planner_iters.append(wa_resp.planning.planner)
        wa_resp.planning.adaptor_iters.append(wa_resp.planning.adaptor)

        if tester_error.error_type is WorkflowErrorType.RUNNER:
            wa_resp.planning.planner.errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = True
            wa_resp.planning.adaptor_rerun_needed = True
            wa_resp.planning.adaptor = None

        if tester_error.error_type is WorkflowErrorType.PLANNING_HF:
            wa_resp.planning.planner.errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = True
            wa_resp.planning.adaptor_rerun_needed = True
            wa_resp.planning.adaptor = None

        if tester_error.error_type is WorkflowErrorType.OUTPUTS_UNEXPECTED:

            n_output_unexpected = len([err for err in wa_resp.planning.testing_errors if err is WorkflowErrorType.OUTPUTS_UNEXPECTED])
            n_planning_reset = len([err for err in wa_resp.planning.testing_errors if err is WorkflowErrorType.PLANNING_RESET])

            n_prev_output_unexpected = 0
            if n_planning_reset > 0:
                n_prev_output_unexpected = n_output_unexpected%n_planning_reset

            failed_cases = []
            if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
                failed_cases = tester_error.additional_info.get("failed_cases", [])


            if n_prev_output_unexpected < self.max_output_unexpected:

                # If the same output fields keep failing, escalate to planner reset sooner.
                if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
                    differences = tester_error.additional_info.get("differences", [])
                    if differences:
                        failing_paths = sorted({d.get("path") for d in differences if d.get("path")})
                        tester_error.additional_info["failing_paths"] = failing_paths

                        prev_paths = set()
                        for err in reversed(wa_resp.planning.testing_errors):
                            if getattr(err, "error_type", None) is WorkflowErrorType.OUTPUTS_UNEXPECTED:
                                prev_paths.update(err.additional_info.get("failing_paths", []))
                        if prev_paths and set(failing_paths) & prev_paths:
                            tester_error.error_type = WorkflowErrorType.PLANNING_RESET
                            wa_resp.planning.planner.errors.append(tester_error)
                            wa_resp.planning.planner_rerun_needed = True
                            wa_resp.planning.adaptor_rerun_needed = True
                            wa_resp.planning.adaptor = None
                            wa_resp.planning.testing_errors.append(tester_error)
                            wa_resp.planning.tester.error = None
                            return wa_resp

                wa_resp.planning.adaptor.all_errors.append(tester_error)

                wa_resp.planning.planner_rerun_needed = False
                wa_resp.planning.adaptor_rerun_needed = True
            else:
                if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
                    differences = tester_error.additional_info.get("differences", [])
                    if differences:
                        failing_paths = sorted({d.get("path") for d in differences if d.get("path")})
                        tester_error.additional_info["failing_paths"] = failing_paths

                tester_error.error_type = WorkflowErrorType.PLANNING_RESET
                wa_resp.planning.planner.errors.append(tester_error)

                wa_resp.planning.planner_rerun_needed = True
                wa_resp.planning.adaptor_rerun_needed = True
                wa_resp.planning.adaptor = None

        if tester_error.error_type is WorkflowErrorType.OUTPUTS_FAILURE:
            wa_resp.planning.adaptor.all_errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True

        if tester_error.error_type is WorkflowErrorType.ADAPTOR_JSON:
            wa_resp.planning.adaptor.all_errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True

        wa_resp.planning.testing_errors.append(tester_error)
        wa_resp.planning.tester.error = None

        return wa_resp

    def _init_wa_obj(self, 
        task_description : str,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        loops : int = 1,
        init_check : Optional[WorkflowCheckResponse] = None,
        ):

        return AssembledWorkflow(
            id = uuid.uuid4().hex,
            input_id = make_uid(d = {
                "task_description" : task_description,
                "input_model" : input_model.model_json_schema() if input_model else "",
                "output_model" : output_model.model_json_schema() if output_model else ""
                }),
            init_check = init_check,
            description = WorkflowDescription(
                task_description = task_description,
                input_model_json = input_model.model_json_schema() if input_model else None,
                output_model_json = output_model.model_json_schema() if output_model else None
            ),
            loops = loops
        )

    async def plan_workflow(
        self,
        task_description : str, 
        test_params : List[Dict[str, Type[BaseModel]]] = None, 
        compare_params : dict = None,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        max_retry : Optional[int] = None,
        reset_loops : Optional[int] = None):

        """
        Uses LLM to plans workflow based on provided tools and description.
        """

        if max_retry is None:
            max_retry = self.max_retry
        
        if reset_loops is None:
            reset_loops = self.reset_loops

        wa_resp = self._init_wa_obj(
            task_description = task_description,
            input_model = input_model,
            output_model = output_model
        )

        self.logger.debug(f"Starting workflow planning ...", label = "START")

        while wa_resp.planning.test_retries in range(max_retry):

            if wa_resp.workflow_possible is None:

                wa_resp.init_check = await self.check_h.check_workflow(
                    task_description = task_description,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    checked_workflow = wa_resp.init_check
                )
                wa_resp.workflow_possible = wa_resp.init_check.workflow_possible

                if wa_resp.workflow_possible is None:
                    continue

                if wa_resp.workflow_possible is False:
                    self.logger.warning(f"Workflow planning is not possible!")
                    wa_resp.planning.planner_rerun_needed = False
                    wa_resp.planning.adaptor_rerun_needed = False
                    wa_resp.workflow_completed = False
                    break


            if wa_resp.planning.planner_rerun_needed:

                wa_resp.planning.planner = await self.planner_h.generate_workflow(
                    task_description = task_description,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    planned_workflow = wa_resp.planning.planner)

            if wa_resp.planning.adaptor_rerun_needed:

                wa_resp.planning.adaptor = await self.adaptor_h.adapt_workflow(
                    workflow=wa_resp.planning.planner.workflow, 
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    adapted_workflow = wa_resp.planning.adaptor
                )

            if wa_resp.init_check.workflow_possible \
                and test_params is not None \
                    and wa_resp.planning.adaptor is not None:

                wa_resp.planning.tester = self.runner_h.run_workflow(
                    workflow = wa_resp.planning.adaptor.workflow, 
                    test_params = test_params,
                    compare_params = compare_params,
                    output_model = output_model,
                    available_functions = available_functions,
                    available_callables = available_callables
                    )
                if task_description:
                    wa_resp.description.task_description = task_description
                
            wa_resp = self._update_reset_logic(
                wa_resp = wa_resp
            )

            if wa_resp.workflow_completed:
                break

            wa_resp.planning.test_retries += 1
            if wa_resp.planning.tester and wa_resp.planning.tester.error:
                self.logger.warning(
                    f"Planning loop failed with {wa_resp.planning.tester.error.error_type} during testing. Attempts left {max_retry - wa_resp.planning.test_retries} !")

            if wa_resp.planning.test_retries == (max(max_retry,1)-1):
                
                if reset_loops > 0:
                
                    self.logger.warning(
                        f"Planning failed to converge, reseting!")
                    reset_loops = reset_loops - 1
                    prev_check = wa_resp.init_check
                    wa_resp = self._init_wa_obj(
                        task_description = task_description,
                        input_model = input_model,
                        output_model = output_model,
                        loops = wa_resp.loops + 1,
                        init_check = prev_check,
                    )


        if wa_resp.init_check.workflow_possible and wa_resp.planning.adaptor:  
            wa_resp.workflow = wa_resp.planning.adaptor.workflow

        if wa_resp.workflow_completed:
            self.logger.debug("Workflow completed.", label = "COMPLETED")
        else:
            self.logger.warning("Workflow failed to converge.", label = "FAILED")

        return wa_resp

    async def run_workflow(
        self,
        workflow_object : AssembledWorkflow,
        task_description : str = None, 
        run_inputs : Type[BaseModel] = None, 
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        max_retry : Optional[int] = None,
        reset_loops : Optional[int] = None):

        """
        Uses LLM to plans workflow based on provided tools and description.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if reset_loops is None:
            reset_loops = self.reset_loops

        wa_resp = workflow_object.copy()
  
        if input_model is None:
            input_model = self.runner_h.json_schema_to_base_model(
                workflow_object.description.input_model_json)
        if output_model is None:
            output_model = self.runner_h.json_schema_to_base_model(
                workflow_object.description.output_model_json)

        while wa_resp.planning.test_retries in range(max_retry):

            if wa_resp.planning.planner_rerun_needed:

                wa_resp.planning.planner = await self.planner_h.generate_workflow(
                    task_description = task_description,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    planned_workflow = wa_resp.planning.planner
                )

            if wa_resp.planning.adaptor_rerun_needed:

                wa_resp.planning.adaptor = await self.adaptor_h.adapt_workflow(
                    workflow=wa_resp.planning.planner.workflow, 
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    adapted_workflow = wa_resp.planning.adaptor
                )

            if run_inputs:

                wa_resp.planning.tester = self.runner_h.run_workflow(
                    workflow = wa_resp.planning.adaptor.workflow, 
                    inputs = run_inputs,
                    output_model = output_model,
                    available_functions = available_functions,
                    available_callables = available_callables
                    )
                if task_description:
                    wa_resp.description.task_description = task_description
                else:
                    task_description = wa_resp.description.task_description
                

            wa_resp = self._update_reset_logic(
                wa_resp = wa_resp
            )

            if wa_resp.workflow_completed:
                break

            wa_resp.planning.test_retries += 1

            self.logger.warning(
                f"Planning loop failed with {wa_resp.planning.tester.error.error_type} during testing. Attempts left {max_retry - wa_resp.planning.test_retries} !")

            if wa_resp.planning.test_retries == (max(max_retry,1)-1):
                
                if reset_loops > 0:
                
                    self.logger.warning(
                        f"Planning failed to converge, reseting!")
                    reset_loops = reset_loops - 1
                    prev_check = wa_resp.init_check
                    wa_resp = self._init_wa_obj(
                        task_description = task_description,
                        input_model = input_model,
                        output_model = output_model,
                        loops = wa_resp.loops + 1,
                        init_check = prev_check,
                    )
            
        wa_resp.workflow = wa_resp.planning.adaptor.workflow

        return wa_resp.planning.tester.outputs[str(len(wa_resp.planning.tester.outputs)-1)]
