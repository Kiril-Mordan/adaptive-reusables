"""
This module contains a set of tools to get initial llm-generated 
workflow for described task based on provided tools.
"""

import attrs
import attrsx

from copy import deepcopy
import yaml
import os

import importlib
import importlib.metadata
import importlib.resources as pkg_resources

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel, Field


class WorkflowPlannerResponse(BaseModel):

    retries : int = Field(description = "Number of attempt it took to generate workflow.")
    workflow : Optional[List[dict]] = Field(default = None, description = "Planned workflow.")
    init_messages : List[dict] = Field(default = None, description = "Initial messages for planning workflow.")
    errors : List[BaseModel] = Field(description = "Errors during planning.")
    include_input : bool = Field(description = "If input model is expected.")
    include_output : bool = Field(description = "If output model is expected.")

    model_config = {
        "arbitrary_types_allowed": True
    }

@attrs.define(kw_only=True)
class LlmHandlerMock(ABC):

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]],  *args, **kwargs):

        """
        Abstract chat method for async chat method that passes messages to llm.
        """

        pass


@attrsx.define(handler_specs = {"llm" : LlmHandlerMock})
class WorkflowPlanner:

    workflow_error_types = attrs.field()
    workflow_error = attrs.field()

    system_message : str = attrs.field(default=None)
    system_message_items : Dict[str, str] = attrs.field(default=None)
    debug_prompts : Dict[str, str] = attrs.field(default=None)
    plan_prompt : str = attrs.field(default=None)
    plan_prompt_items : Dict[str, str] = attrs.field(default=None)
    
    prompts_filepath : str = attrs.field(default=None)
    available_functions: List[LlmFunctionItem] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else deepcopy(v),
    )

    max_retry : int = attrs.field(default=5)

    """
    Plans workflows
    """

    def __attrs_post_init__(self):

        self._assign_prompts()

    def _assign_prompts(self, 
        prompts_filepath : str = None,
        system_message : str = None, 
        system_message_items : Dict[str,str] = None,
        plan_prompt_items : Dict[str, str] = None,
        debug_prompts : Dict[str, str] = None,
        plan_prompt : str = None
        ):

        if prompts_filepath is None: 
            prompts_filepath = self.prompts_filepath

        wa_path = pkg_resources.files('workflow_auto_assembler')

        if 'artifacts' in os.listdir(wa_path):

            if prompts_filepath is None:

                with pkg_resources.path('workflow_auto_assembler.artifacts.prompts',
                'workflow_planner.yml') as path:
                    prompts_filepath = path

            with open(prompts_filepath, 'r') as f:
                wp_prompts = yaml.safe_load(f)

        if system_message: 
            self.system_message = system_message
        else:
            self.system_message = wp_prompts['system_message']

        if system_message_items: 
            self.system_message_items = system_message_items
        else:
            self.system_message_items = wp_prompts.get("system_message_items", {})

        if plan_prompt_items: 
            self.plan_prompt_items = plan_prompt_items
        else:
            self.plan_prompt_items = wp_prompts.get("plan_prompt_items", {})

        if debug_prompts: 
            self.debug_prompts = debug_prompts
        else:
            self.debug_prompts = wp_prompts['debug_prompts']

        if plan_prompt: 
            self.plan_prompt = plan_prompt
        else:
            self.plan_prompt = wp_prompts['plan_prompt']


    def _read_json_output(self, output : str) -> list | dict | None:

        try:

            if "```json" in output:
                output = output.replace("```json", "").replace("```", "")

            function_calls = json.loads(output)
        except Exception as e:
            self.logger.error(f"Failed to extract json from {output}")
            return None

        return function_calls

    def _get_hafunctions(self, 
        function_calls : list, 
        available_functions : list,
        include_output : bool) -> tuple:

        hfunctions, afunctions = None, None

        if function_calls:

            afunctions = [afd.name for afd in available_functions]

            hfunctions = [fc['name'] for fc in function_calls if fc['name'] not in afunctions]

            if include_output:
                hfunctions = [hf for hf in hfunctions if hf != "output_model"]

        return hfunctions, afunctions 

    def _prep_init_messages(self,
        task_description : str, 
        available_functions : list, 
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,):


        available_functions_json = json.dumps([
            {key:value for key,value in av.model_dump().items() \
                if key in ["name", "description", "input_schema_json", "output_schema_json"]} \
                    for av in available_functions])

        system_message_items = {
            "purpose_description" : "",
            "expected_output_schema" : "",
            "function_call_description" : ""
        }

        if self.system_message_items.get("purpose_description"):
            system_message_items["purpose_description"] = self.system_message_items.get("purpose_description")

        if self.system_message_items.get("expected_output_schema"):
            system_message_items["expected_output_schema"] = self.system_message_items.get("expected_output_schema")

        if self.system_message_items.get("function_call_description"):
            system_message_items["function_call_description"] = self.system_message_items.get("function_call_description").format(
                available_functions = available_functions_json)

        user_message_items = {
            "task_description" : task_description,
            "input_schema" : "",
            "output_schema" : ""}

        if input_model is not None and self.plan_prompt_items.get("input_schema") is not None:
            user_message_items["input_schema"] = self.plan_prompt_items["input_schema"].format(
                input_model_schema = input_model.model_json_schema())

        if output_model is not None and self.plan_prompt_items.get("output_schema") is not None:
            user_message_items["output_schema"] = self.plan_prompt_items["output_schema"].format(
                output_model_schema = output_model.model_json_schema())

        messages = [
        {"role": "system", "content": self.system_message.format(
            **system_message_items)},
        {"role": "user", "content": self.plan_prompt.format(
            **user_message_items
        )}
        ]

        return messages

    def _check_llm_response(self, 
        llm_response : str, 
        available_functions : list,
        include_output : bool = False,
        init_error : Optional[Type[BaseModel]] = None):

        if init_error:
            return init_error

        function_calls = self._read_json_output(output=llm_response)

        if function_calls is None:
            return self.workflow_error(error_type = self.workflow_error_types.PLANNING_JSON,
                additional_info = {"llm_response" : llm_response})

        hfunctions, afunctions = self._get_hafunctions(
                function_calls = function_calls, 
                available_functions = available_functions,
                include_output = include_output)

        if hfunctions is None:
            return self.workflow_error(error_type = self.workflow_error_types.PLANNING_JSON,
                additional_info = {"llm_response" : llm_response})

        if not ((function_calls is not None) and ((hfunctions is None) or (hfunctions == []))):
            return self.workflow_error(error_type = self.workflow_error_types.PLANNING_HF,
                additional_info = {"llm_response" : llm_response})

        if include_output:
            if "output_model" not in [fc["name"] for fc in function_calls]:
                return self.workflow_error(error_type = self.workflow_error_types.PLANNING_MISSOUTPUT,
                additional_info = {"llm_response" : llm_response})

        return None


    async def generate_workflow(
        self,
        task_description : str = None, 
        available_functions : list = None, 
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        max_retry : Optional[int] = None,
        planned_workflow : Optional[WorkflowPlannerResponse] = None) -> WorkflowPlannerResponse:

        """
        Generates initial workflow from available functions given task description.

        Args:

            task_description (str): llm prompt that describes a task, achievable with available functions.
            available_functions (list): list of function items for llm to pick from with their input and output models.
            max_retry (Optional[int]): optional maximum number of allowed retries.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if available_functions is None:
            available_functions = self.available_functions

        if available_functions is None:
            raise ValueError("Input available_functions : list cannot be None!")

        if planned_workflow is None:
        
            init_messages = self._prep_init_messages(
                available_functions = available_functions, 
                task_description = task_description, 
                input_model = input_model, 
                output_model = output_model
            )

            response = await self.llm_h.chat(init_messages)
            llm_response = response.message.content

            retry_i = 0
            errors = []
            init_error = None
            include_input = input_model is not None
            include_output = output_model is not None
        
        else:
            init_messages = planned_workflow.init_messages
            llm_response = json.dumps(planned_workflow.workflow)
            retry_i = planned_workflow.retries
            errors = planned_workflow.errors
            if len(errors) == 0:
                self.logger.error("Planner recieved `planned_workflow` input for retry that doesn not contain any errors!")
                return planned_workflow
            init_error = errors[-1]
            include_input = planned_workflow.include_input
            include_output = planned_workflow.include_output
        
        retry_messages = init_messages

        while retry_i < max_retry:

            error = self._check_llm_response(
                init_error = init_error,
                llm_response = llm_response,
                include_output = include_output,
                available_functions = available_functions)

            if error is None:
                planned_workflow = self._read_json_output(output=llm_response)
                return WorkflowPlannerResponse(
                    errors = errors,
                    workflow = planned_workflow,
                    retries = retry_i,
                    include_input = include_input,
                    include_output = include_output,
                    init_messages = init_messages
                )

            retry_i += 1
            if init_error:
                init_error = None
            else:
                errors.append(error)

            self.logger.debug(f"Attempt: {retry_i}")

            if error.error_type is self.workflow_error_types.PLANNING_JSON:
                debug_response = await self.llm_h.chat(retry_messages)
                llm_response = debug_response.message.content
                continue

            if error.error_type is self.workflow_error_types.PLANNING_MISSOUTPUT:

                retry_messages = init_messages + [
                    {'role' : 'assistant', "content" : llm_response},
                    {"role": "user", "content": self.debug_prompts["mo"]}
                ]

                debug_response = await self.llm_h.chat(retry_messages)
                llm_response = debug_response.message.content
                continue

            if error.error_type is self.workflow_error_types.PLANNING_HF:

                function_calls = self._read_json_output(output=llm_response)

                hfunctions, afunctions = self._get_hafunctions(
                        function_calls = function_calls, 
                        available_functions = available_functions,
                        include_output = include_output)

                retry_messages = init_messages + [
                    {'role' : 'assistant', "content" : llm_response},
                    {"role": "user", "content": self.debug_prompts["hf"].format(
                        hfunctions = "\n -".join([h for h in hfunctions]),
                        afunctions = "\n -".join([a for a in afunctions]))}
                ]

                debug_response = await self.llm_h.chat(retry_messages)
                llm_response = debug_response.message.content
                continue

            if error.error_type is self.workflow_error_types.RUNNER:

                function_calls = self._read_json_output(output=llm_response)

                _, afunctions = self._get_hafunctions(
                        function_calls = function_calls, 
                        available_functions = available_functions,
                        include_output = include_output)

                ffunction = error.additional_info.get("ffunction")

                retry_messages = init_messages + [
                    {'role' : 'assistant', "content" : llm_response},
                    {"role": "user", "content": self.debug_prompts["alt"].format(
                        ffunction = ffunction,
                        afunctions = "\n -".join([a for a in afunctions if a != ffunction]))}
                ]

                debug_response = await self.llm_h.chat(retry_messages)
                llm_response = debug_response.message.content
                continue

        if retry_i == max_retry:
            return WorkflowPlannerResponse(
                errors = errors,
                workflow = None,
                retries = retry_i,
                init_messages = init_messages,
                include_input = include_input,
                include_output = include_output,
            )
