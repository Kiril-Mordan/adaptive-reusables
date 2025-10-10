"""
The module contains tools to generate a functional workflow with a use of llm given tool 
in a form of annotated functions.
"""

import json
from typing import Type
from pydantic import BaseModel, Field

from .components.wa_general_models import LlmFunctionItem, WorkflowErrorType, WorkflowError, create_function_item
from .components.llm_function.llm_handler import LlmHandler
from .components.workflow_planner import WorkflowPlanner, WorkflowPlannerResponse
from .components.workflow_adaptor import WorkflowAdaptor, WorkflowAdaptorResponse
from .components.input_collector import InputCollector
from .components.workflow_runner import WorkflowRunner, TestedWorkflow

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "LLM-based planner and orchestrator that turns existing code into complex functions.",
}

class WorkflowAssemblerResponse(BaseModel):

    planner_response : Optional[WorkflowPlannerResponse] = Field(default = None, description = "Planning steps of workflow creation.")
    adaptor_response : Optional[WorkflowAdaptorResponse] = Field(default = None, description = "Adapting step of workflow creation.")
    tester_response : Optional[TestedWorkflow] = Field(default = None, description = "Testing step of workflow creation.")
    testing_errors : Optional[List[WorkflowError]] = Field(default = [], description = "Errors during testing workflow.")
    planner_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if planner needs reset during retry.")
    adaptor_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if adaptor needs reset during retry.")
    workflow_completed : Optional[bool] = Field(default = False, description = "Indicates if workflow was completed in the preset amount of retries.")
    test_retries : int = Field(default = 0, description = "Retries completed during planning and testing loop.")
    test_output : Optional[BaseModel] = Field(default = None, description = "Errors during testing workflow.")
    workflow : Optional[dict] = Field(default = None, description = "Planned and tested workflow.")



@attrsx.define(handler_specs = {
        "llm_handler" : LlmHandler,
        "planner" : WorkflowPlanner,
        "adaptor" : WorkflowAdaptor,
        "runner" : WorkflowRunner,
        "input_collector" : InputCollector
    },
    logger_chaining={'loggerLvl' : True})
class WorkflowAutoAssembler:

    workflow_error_types = attrs.field(default=WorkflowErrorType)
    workflow_error = attrs.field(default=WorkflowError)

    available_functions : List[LlmFunctionItem] = attrs.field(default=None)
    available_callables : Dict[str, callable] = attrs.field(default=None)

    max_retry : int = attrs.field(default=5)

    def __attrs_post_init__(self):

        self._initialize_input_collector_h()
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
            "available_functions" : self.available_functions,
            "available_callables" : self.available_callables,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
        })

    def _update_reset_logic(self, wa_resp : WorkflowAssemblerResponse):

        if wa_resp.tester_response.error is None:
            wa_resp.planner_rerun_needed = False
            wa_resp.adaptor_rerun_needed = False
            wa_resp.workflow_completed = True
            return wa_resp
        
        if wa_resp.tester_response.error.error_type is WorkflowErrorType.RUNNER:
            wa_resp.planner_response.errors.append(wa_resp.tester_response.error)

            wa_resp.planner_rerun_needed = True
            wa_resp.adaptor_rerun_needed = True
            wa_resp.adaptor_response = None

        if wa_resp.tester_response.error.error_type is WorkflowErrorType.PLANNING_HF:
            wa_resp.planner_response.errors.append(wa_resp.tester_response.error)

            wa_resp.planner_rerun_needed = True
            wa_resp.adaptor_rerun_needed = True
            wa_resp.adaptor_response = None

        if wa_resp.tester_response.error.error_type is WorkflowErrorType.ADAPTOR_JSON:
            wa_resp.adaptor_response.all_errors.append(wa_resp.tester_response.error)

            wa_resp.planner_rerun_needed = False
            wa_resp.adaptor_rerun_needed = True


        wa_resp.testing_errors.append(wa_resp.tester_response.error)

        wa_resp.tester_response.error = None

        return wa_resp


    async def plan_workflow(
        self,
        task_description : str, 
        test_inputs : Type[BaseModel] = None, 
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

        wa_resp = WorkflowAssemblerResponse()

        while wa_resp.test_retries in range(max_retry):

            if wa_resp.planner_rerun_needed:

                wa_resp.planner_response = await self.planner_h.generate_workflow(
                    task_description=task_description,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    planned_workflow = wa_resp.planner_response
                )

            if wa_resp.adaptor_rerun_needed:

                wa_resp.adaptor_response = await self.adaptor_h.adapt_workflow(
                    workflow=wa_resp.planner_response.workflow, 
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    adapted_workflow = wa_resp.adaptor_response
                )

            if test_inputs:

                wa_resp.tester_response = self.runner_h.run_workflow(
                    workflow = wa_resp.adaptor_response.workflow, 
                    inputs = test_inputs,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    available_callables = available_callables
                    )
                if task_description:
                    wa_resp.tester_response.task_description = task_description
                
            wa_resp = self._update_reset_logic(
                wa_resp = wa_resp
            )

            if wa_resp.workflow_completed:
                break

            wa_resp.test_retries += 1
            self.logger.warning(f"Error : {wa_resp.tester_response.error.error_type} happened during testing. Attempts left {max_retry - wa_resp.test_retries} !")

            
        wa_resp.workflow = wa_resp.adaptor_response.workflow
        wa_resp.test_output = wa_resp.tester_response.outputs

        return wa_resp

    async def run_workflow(
        self,
        workflow_object : WorkflowAssemblerResponse,
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
            input_model = workflow_object.tester_response.input_model
        if output_model is None:
            output_model = workflow_object.tester_response.output_model

        while wa_resp.test_retries in range(max_retry):

            if wa_resp.planner_rerun_needed:

                wa_resp.planner_response = await self.planner_h.generate_workflow(
                    task_description=task_description,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    planned_workflow = wa_resp.planner_response
                )

            if wa_resp.adaptor_rerun_needed:

                wa_resp.adaptor_response = await self.adaptor_h.adapt_workflow(
                    workflow=wa_resp.planner_response.workflow, 
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    adapted_workflow = wa_resp.adaptor_response
                )

            if run_inputs:

                    
                wa_resp.tester_response = self.runner_h.run_workflow(
                    workflow = wa_resp.adaptor_response.workflow, 
                    inputs = run_inputs,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    available_callables = available_callables
                    )
                if task_description:
                    wa_resp.tester_response.task_description = task_description
                else:
                    task_description = wa_resp.tester_response.task_description
                

            wa_resp = self._update_reset_logic(
                wa_resp = wa_resp
            )

            if wa_resp.workflow_completed:
                break

            wa_resp.test_retries += 1

            self.logger.warning(f"Error : {wa_resp.tester_response.error.error_type} happened during testing. Attempts left {max_retry - wa_resp.test_retries} !")

            
        wa_resp.workflow = wa_resp.adaptor_response.workflow

        return wa_resp.tester_response.outputs[str(len(wa_resp.test_output)-1)]