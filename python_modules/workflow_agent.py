"""
The module contains tools to generate a functional workflow with a use of llm given tool 
in a form of annotated functions.
"""

import json
from typing import Type
from pydantic import BaseModel, Field

from .components.wa_general_models import LlmFunctionItem, WorkflowErrorType, WorkflowError
from .components.llm_function.llm_handler import LlmHandler
from .components.workflow_planner import WorkflowPlanner, WorkflowPlannerResponse, create_function_item
from .components.workflow_adaptor import WorkflowAdaptor, WorkflowAdaptorResponse
from .components.input_collector import InputCollector
from .components.workflow_runner import WorkflowRunner, TestedWorkflow

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "LLM-based planner and orchestrator that turns existing code into complex functions.",
}


@attrsx.define(handler_specs = {
        "llm_handler" : LlmHandler,
        "planner" : WorkflowPlanner,
        "adaptor" : WorkflowAdaptor,
        "runner" : WorkflowRunner,
        "input_collector" : InputCollector
    },
    logger_chaining={'loggerLvl' : True})
class WorkflowAgent:

    available_functions : List[LlmFunctionItem] = attrs.field(default=None)
    available_callables : Dict[str, callable] = attrs.field(default=None)

    max_retry : int = attrs.field(default=5)

    def __attrs_post_init__(self):

        self._initialize_input_collector_h()
        self._initialize_llm_handler_h()
        self._initialize_planner_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "available_functions" : self.available_functions,
            "max_retry" : self.max_retry
        })
        self._initialize_adaptor_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "input_collector_h" : self.input_collector_h,
            "available_functions" : self.available_functions,
            "max_retry" : self.max_retry
        })
        self._initialize_runner_h(uparams = {
            "available_functions" : self.available_functions,
            "available_callables" : self.available_callables,
        })

    def _update_reset_logic(self,
        planned_wf_obj : WorkflowPlannerResponse, 
        adapted_wf_obj : WorkflowAdaptorResponse, 
        tested_wf_obj : TestedWorkflow,
        rerun_planner : bool, 
        rerun_adaptor : bool,
        stop_retry : bool):

        if tested_wf_obj.error is None:
            stop_retry = True
            return planned_wf_obj, adapted_wf_obj, tested_wf_obj, rerun_planner, rerun_adaptor, stop_retry
        
        if tested_wf_obj.error.error_type is WorkflowErrorType.RUNNER:
            planned_wf_obj.errors.append(tested_wf_obj.error)

            rerun_planner = True
            rerun_adaptor = True
            adapted_wf_obj = None

        if tested_wf_obj.error.error_type is WorkflowErrorType.PLANNING_HF:
            planned_wf_obj.errors.append(tested_wf_obj.error)

            rerun_planner = True
            rerun_adaptor = True
            adapted_wf_obj = None

        if tested_wf_obj.error.error_type is WorkflowErrorType.ADAPTOR_JSON:
            adapted_wf_obj.all_errors.append(tested_wf_obj.error)

            rerun_planner = False
            rerun_adaptor = True


        tested_wf_obj.error = None

        return planned_wf_obj, adapted_wf_obj, tested_wf_obj, rerun_planner, rerun_adaptor, stop_retry


    async def plan_workflow(
        self,
        task_description : str = None, 
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

        planned_wf_obj = None
        adapted_wf_obj = None
        tested_wf_obj = None

        rerun_planner = True
        rerun_adaptor = True
        stop_retry = False

        retry = 0

        while retry in range(max_retry):

            if rerun_planner:

                planned_wf_obj = await self.planner_h.generate_workflow(
                    task_description=task_description,
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    planned_workflow = planned_wf_obj
                )

            if rerun_adaptor:

                adapted_wf_obj = await self.adaptor_h.adapt_workflow(
                    workflow=planned_wf_obj.workflow, 
                    input_model = input_model,
                    output_model = output_model,
                    available_functions = available_functions,
                    max_retry = max_retry,
                    adapted_workflow = adapted_wf_obj
                )

            if test_inputs:

                tested_wf_obj = self.runner_h.run_workflow(
                    workflow = adapted_wf_obj.workflow, 
                    inputs = test_inputs,
                    output_model = output_model,
                    available_functions = available_functions,
                    available_callables = available_callables
                    )

            (planned_wf_obj, 
            adapted_wf_obj, 
            tested_wf_obj,
            rerun_planner, 
            rerun_adaptor,
            stop_retry) = self._update_reset_logic(
                planned_wf_obj = planned_wf_obj, 
                adapted_wf_obj = adapted_wf_obj, 
                tested_wf_obj = tested_wf_obj,
                rerun_planner = rerun_planner, 
                rerun_adaptor = rerun_adaptor,
                stop_retry = stop_retry,
            )

            if stop_retry:
                break

            retry += 1
            self.logger.warning(f"Error : {tested_wf_obj.error.error_type} happened during testing. Attempts left {max_retry - retry} !")

            
        return {
            "planned_wf_obj" : planned_wf_obj,
            "adapted_wf_obj" : adapted_wf_obj,
            "tested_wf_obj" : tested_wf_obj,
        }