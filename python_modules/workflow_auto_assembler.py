"""
The module contains tools to generate a functional workflow with a use of llm given tool 
in a form of annotated functions.
"""

import attrs
import attrsx

import uuid
import json
from typing import Type
from pydantic import BaseModel, Field

from .components.wa_general_models import LlmFunctionItem, WorkflowErrorType, WorkflowError, create_avc_items, LlmFunctionItemInput, make_uid
from .components.llm_function.llm_handler import LlmHandler
from .components.workflow_check import WorkflowCheck, WorkflowCheckResponse
from .components.workflow_planner import WorkflowPlanner, WorkflowPlannerResponse
from .components.workflow_adaptor import WorkflowAdaptor, WorkflowAdaptorResponse
from .components.input_collector import InputCollector
from .components.output_comparer import OutputComparer
from .components.workflow_runner import WorkflowRunner, TestedWorkflow

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "LLM-based planner and orchestrator that turns existing code into complex functions.",
}

class PlanningStepsResp(BaseModel):
    planner : Optional[WorkflowPlannerResponse] = Field(default = None, description = "Planning steps of workflow creation.")
    adaptor : Optional[WorkflowAdaptorResponse] = Field(default = None, description = "Adapting step of workflow creation.")
    tester : Optional[TestedWorkflow] = Field(default = None, description = "Testing step of workflow creation.") 
    planner_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if planner needs reset during retry.")
    adaptor_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if adaptor needs reset during retry.")
    testing_errors : Optional[List[WorkflowError]] = Field(default = [], description = "Errors during testing workflow.")
    test_retries : int = Field(default = 0, description = "Retries completed during planning and testing loop.")

class WorfklowDescription(BaseModel):
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
    description : Optional[WorfklowDescription] = Field(default = WorfklowDescription(), description = "Workflow description.")


@attrsx.define(handler_specs = {
        "llm_handler" : LlmHandler,
        "check" : WorkflowCheck,
        "planner" : WorkflowPlanner,
        "adaptor" : WorkflowAdaptor,
        "runner" : WorkflowRunner,
        "input_collector" : InputCollector,
        "output_comparer" : OutputComparer
    },
    logger_chaining={'loggerLvl' : True})
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

    max_retry : int = attrs.field(default=5)

    def __attrs_post_init__(self):

        self._initialize_input_collector_h(uparams = {
            "loggerLvl" : logging.INFO
        })
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

        if wa_resp.planning.tester.error is None:
            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = False
            wa_resp.workflow_completed = True
            self.logger.debug(f"Workflow completed after {wa_resp.planning.test_retries + 1} planning loops!")

            return wa_resp
        
        self.logger.debug(f"Updating reset logic based on error: {wa_resp.planning.tester.error}")

        if wa_resp.planning.tester.error.error_type is WorkflowErrorType.RUNNER:
            wa_resp.planning.planner.errors.append(wa_resp.planning.tester.error)

            wa_resp.planning.planner_rerun_needed = True
            wa_resp.planning.adaptor_rerun_needed = True
            wa_resp.planning.adaptor = None

        if wa_resp.planning.tester.error.error_type is WorkflowErrorType.PLANNING_HF:
            wa_resp.planning.planner.errors.append(wa_resp.planning.tester.error)

            wa_resp.planning.planner_rerun_needed = True
            wa_resp.planning.adaptor_rerun_needed = True
            wa_resp.planning.adaptor = None

        if wa_resp.planning.tester.error.error_type is WorkflowErrorType.OUTPUTS_UNEXPECTED:
            wa_resp.planning.adaptor.all_errors.append(wa_resp.planning.tester.error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True

        if wa_resp.planning.tester.error.error_type is WorkflowErrorType.OUTPUTS_FAILURE:
            wa_resp.planning.adaptor.all_errors.append(wa_resp.planning.tester.error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True

        if wa_resp.planning.tester.error.error_type is WorkflowErrorType.ADAPTOR_JSON:
            wa_resp.planning.adaptor.all_errors.append(wa_resp.planning.tester.error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True


        wa_resp.planning.testing_errors.append(wa_resp.planning.tester.error)

        wa_resp.planning.tester.error = None

        return wa_resp


    async def plan_workflow(
        self,
        task_description : str, 
        test_params : List[Dict[str, Type[BaseModel]]] = None, 
        compare_params : dict = None,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        max_retry : Optional[int] = None):

        """
        Uses LLM to plans workflow based on provided tools and description.
        """

        if max_retry is None:
            max_retry = self.max_retry

        wa_resp = AssembledWorkflow(
            id = str(uuid.uuid4()),
            input_id = make_uid(d = {
                "task_description" : task_description,
                "input_model" : input_model.model_json_schema() if input_model else "",
                "output_model" : output_model.model_json_schema() if input_model else ""
                }),
            description = WorfklowDescription(
                task_description = task_description,
                input_model_json = input_model.model_json_schema(),
                output_model_json = output_model.model_json_schema()
            )
        )

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

                expected_inputs = None
                expected_outputs = None
                if test_params:
                    expected_inputs = test_params[0].get("inputs")
                    expected_outputs = test_params[0].get("outputs")

                wa_resp.planning.tester = self.runner_h.run_workflow(
                    workflow = wa_resp.planning.adaptor.workflow, 
                    inputs = expected_inputs,
                    expected_outputs = expected_outputs,
                    compare_params = compare_params,
                    input_model = input_model,
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

        if wa_resp.init_check.workflow_possible and wa_resp.planning.adaptor:  
            wa_resp.workflow = wa_resp.planning.adaptor.workflow

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
        max_retry : Optional[int] = None):

        """
        Uses LLM to plans workflow based on provided tools and description.
        """

        if max_retry is None:
            max_retry = self.max_retry

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
                    input_model = input_model,
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

            
        wa_resp.workflow = wa_resp.planning.adaptor.workflow

        return wa_resp.planning.tester.outputs[str(len(wa_resp.planning.tester.outputs)-1)]