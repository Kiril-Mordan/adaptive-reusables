"""
This module contains a set of tools to check if llm-generated 
workflow for described task based on provided tools is possible.
"""

import attrs
import attrsx

import yaml
import os

import importlib
import importlib.metadata
import importlib.resources as pkg_resources

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel, Field


class WorkflowCheckResponse(BaseModel):

    retries : int = Field(description = "Number of attempt it took to generate workflow.")
    init_messages : List[dict] = Field(default = None, description = "Initial messages for planning workflow.")
    errors : List[BaseModel] = Field(description = "Errors during planning.")
    include_input : bool = Field(description = "If input model is expected.")
    include_output : bool = Field(description = "If output model is expected.")
    workflow_possible : bool = Field(description = "If workflow is possible for a provided task and set of tools.")
    justification : str = Field(description = "Why it was determined that workflow is possible or not.")

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
class WorkflowCheck:

    workflow_error_types = attrs.field()
    workflow_error = attrs.field()

    system_message : str = attrs.field(default=None)
    system_message_items : Dict[str, str] = attrs.field(default=None)
    debug_prompts : Dict[str, str] = attrs.field(default=None)
    check_prompt : str = attrs.field(default=None)
    check_prompt_items : Dict[str, str] = attrs.field(default=None)
    
    prompts_filepath : str = attrs.field(default=None)
    available_functions : list = attrs.field(default=None)

    n_checks : int = attrs.field(default=5)
    max_retry : int = attrs.field(default=5)

    """
    Checks if workflows are possible based on provided task and description
    """

    def __attrs_post_init__(self):

        self._assign_prompts()

    def _assign_prompts(self, 
        prompts_filepath : str = None,
        system_message : str = None, 
        system_message_items : Dict[str,str] = None,
        check_prompt_items : Dict[str, str] = None,
        debug_prompts : Dict[str, str] = None,
        check_prompt : str = None
        ):

        if prompts_filepath is None: 
            prompts_filepath = self.prompts_filepath

        wa_path = pkg_resources.files('workflow_auto_assembler')

        if 'artifacts' in os.listdir(wa_path):

            if prompts_filepath is None:

                with pkg_resources.path('workflow_auto_assembler.artifacts.prompts',
                'workflow_check.yml') as path:
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

        if check_prompt_items: 
            self.check_prompt_items = check_prompt_items
        else:
            self.check_prompt_items = wp_prompts.get("check_prompt_items", {})

        if debug_prompts: 
            self.debug_prompts = debug_prompts
        else:
            self.debug_prompts = wp_prompts['debug_prompts']

        if check_prompt: 
            self.check_prompt = check_prompt
        else:
            self.check_prompt = wp_prompts['check_prompt']


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

        if input_model is not None and self.check_prompt_items.get("input_schema") is not None:
            user_message_items["input_schema"] = self.check_prompt_items["input_schema"].format(
                input_model_schema = input_model.model_json_schema())

        if output_model is not None and self.check_prompt_items.get("output_schema") is not None:
            user_message_items["output_schema"] = self.check_prompt_items["output_schema"].format(
                output_model_schema = output_model.model_json_schema())

        messages = [
        {"role": "system", "content": self.system_message.format(
            **system_message_items)},
        {"role": "user", "content": self.check_prompt.format(
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
            return self.workflow_error(error_type = self.workflow_error_types.CHECK_JSON,
                additional_info = {"llm_response" : llm_response})

        
        return None

    async def _get_llm_response(self, messages, n_checks):

        requests = [self.llm_h.chat(messages) for i in range(n_checks)]

        responses = await asyncio.gather(*requests)
        llm_responses = [response.message.content for response in responses] 

        checked_workflow_items_v = [self._read_json_output(output=llm_response) for llm_response in llm_responses] 
        decisions = [checked_workflow_items["decision"] for checked_workflow_items in checked_workflow_items_v if checked_workflow_items is not None]
        llm_response_p = [llm_response for llm_response, decision in zip(llm_responses, decisions) if decision]
        if llm_response_p:
            llm_response = llm_response_p[0]
        else:
            llm_response = llm_responses[0]

        return llm_response

    async def check_workflow(
        self,
        task_description : str = None, 
        available_functions : list = None, 
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        max_retry : Optional[int] = None,
        n_checks : Optional[int] = None,
        checked_workflow : Optional[WorkflowCheckResponse] = None) -> WorkflowCheckResponse:

        """
        Check viability of workflow from available functions given task description.

        Args:

            task_description (str): llm prompt that describes a task, achievable with available functions.
            available_functions (list): list of function items for llm to pick from with their input and output models.
            max_retry (Optional[int]): optional maximum number of allowed retries.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if n_checks is None:
            n_checks = self.n_checks

        if available_functions is None:
            available_functions = self.available_functions

        if available_functions is None:
            raise ValueError("Input available_functions : list cannot be None!")

        if checked_workflow is None:
        
            init_messages = self._prep_init_messages(
                available_functions = available_functions, 
                task_description = task_description, 
                input_model = input_model, 
                output_model = output_model
            )

            llm_response = await self._get_llm_response(messages = init_messages, n_checks = n_checks)

            retry_i = 0
            errors = []
            init_error = None
            include_input = input_model is not None
            include_output = output_model is not None
        
        else:
            init_messages = checked_workflow.init_messages
            llm_response = json.dumps({"justification" :  checked_workflow.justification,
                                       "decision" : checked_workflow.workflow_possible})
            retry_i = checked_workflow.retries
            errors = checked_workflow.errors
            init_error = errors[-1]
            include_input = checked_workflow.include_input
            include_output = checked_workflow.include_output
        
        retry_messages = init_messages

        while retry_i < max_retry:

            error = self._check_llm_response(
                init_error = init_error,
                llm_response = llm_response,
                include_output = include_output,
                available_functions = available_functions)

            if error is None:
                checked_workflow_items = self._read_json_output(output=llm_response)
                return WorkflowCheckResponse(
                    errors = errors,
                    retries = retry_i,
                    include_input = include_input,
                    include_output = include_output,
                    init_messages = init_messages,
                    workflow_possible = checked_workflow_items["decision"],
                    justification = checked_workflow_items["justification"],
                )

            retry_i += 1
            if init_error:
                init_error = None
            else:
                errors.append(error)

            self.logger.debug(f"Attempt: {retry_i}")

            if error.error_type is self.workflow_error_types.CHECK_JSON:
                debug_response = await self._get_llm_response(messages = retry_messages, n_checks = n_checks)
                llm_response = debug_response['message']['content']
                continue

            if error.error_type is self.workflow_error_types.CHECK_INIT:
                break

            
        if retry_i == max_retry:
            return WorkflowCheckResponse(
                errors = errors,
                retries = retry_i,
                init_messages = init_messages,
                include_input = include_input,
                include_output = include_output,
                workflow_possible = None,
                justification = None
            )
