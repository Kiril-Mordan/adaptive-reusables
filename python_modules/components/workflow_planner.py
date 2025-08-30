"""
This module contains a set of tools to get initial llm-generated 
workflow for described task based on provided tools.
"""

import attrs
import attrsx

import yaml
import os

import importlib
import importlib.metadata
import importlib.resources as pkg_resources

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LlmFunctionItem(BaseModel):

    """
    Function suitable for llm use. 
    """

    name : str
    description : str
    input_schema_json : dict
    output_schema_json : dict
    input_model : Type[BaseModel]
    output_model : Type[BaseModel]

@attrs.define(kw_only=True)
class LlmHandlerMock(ABC):

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]],  *args, **kwargs):

        """
        Abstract chat method for async chat method that passes messages to llm.
        """

        pass


def create_function_item(
    func: callable, 
    input_model: Type[BaseModel], 
    output_model: Type[BaseModel]) -> dict:
    """
    Constructs a structured function item that includes:
      - function name (extracted from the actual function's __name__)
      - function description (extracted from the function's __doc__)
      - JSON schema for the input model
      - JSON schema for the output model

    Parameters:
      func: The actual function (callable) object.
      input_model: The Pydantic model class representing the function's input schema.
      output_model: The Pydantic model class representing the function's output schema.

    Returns:
      LlmFunctionItem with:
        - "name": the function's name.
        - "description": the function's description (docstring).
        - "input_schema_json": the JSON schema (as a dict) for the input model.
        - "output_schema_json": the JSON schema (as a dict) for the output model.
        - "input_model": The Pydantic model class representing the function's input schema.
        - "output_model": The Pydantic model class representing the function's output schema.
    """
    return LlmFunctionItem(
        name = func.__name__,
        description = func.__doc__.strip() if func.__doc__ else "",
        input_schema_json = input_model.model_json_schema(),
        output_schema_json = output_model.model_json_schema(),
        input_model = input_model,
        output_model = output_model
    )

@attrsx.define(handler_specs = {"llm" : LlmHandlerMock})
class WorkflowPlanner:


    system_message : str = attrs.field(default=None)
    system_message_items : Dict[str, str] = attrs.field(default=None)
    debug_prompt : str = attrs.field(default=None)
    plan_prompt : str = attrs.field(default=None)
    plan_prompt_items : Dict[str, str] = attrs.field(default=None)
    
    prompts_filepath : str = attrs.field(default=None)
    available_functions : List[LlmFunctionItem] = attrs.field(default=None)

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
        debug_prompt : str = None,
        plan_prompt : str = None
        ):

        if prompts_filepath is None: 
            prompts_filepath = self.prompts_filepath

        wa_path = pkg_resources.files('workflow_agent')

        if 'artifacts' in os.listdir(wa_path):

            if prompts_filepath is None:

                with pkg_resources.path('workflow_agent.artifacts.prompts',
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

        if debug_prompt: 
            self.debug_prompt = debug_prompt
        else:
            self.debug_prompt = wp_prompts['debug_prompt']

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

    def _get_hafunctions(self, function_calls : list, available_functions : List[LlmFunctionItem]) -> tuple:

        hfunctions, afunctions = None, None

        if function_calls:

            afunctions = [afd.name for afd in available_functions]

            hfunctions = [fc['name'] for fc in function_calls if fc['name'] not in afunctions]

        return hfunctions, afunctions 

    async def generate_workflow(
        self,
        task_description : str, 
        available_functions : List[LlmFunctionItem] = None, 
        input_model : type(BaseModel) = None,
        max_retry : Optional[int] = None):

        """
        Generates initial workflow from available functions given task description.

        Args:

            task_description (str): llm prompt that describes a task, achievable with available functions.
            available_functions (List[LlmFunctionItem]): list of function items for llm to pick from with their input and output models.
            max_retry (Optional[int]): optional maximum number of allowed retries.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if available_functions is None:
            available_functions = self.available_functions

        if available_functions is None:
            raise ValueError("Input available_functions : List[LlmFunctionItem] cannot be None!")

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

        messages = [
        {"role": "system", "content": self.system_message.format(
            **system_message_items)},
        {"role": "user", "content": self.plan_prompt.format(
            **user_message_items
        )}
        ]

        response = await self.llm_h.chat(messages)
        llm_response = response['message']['content']


        failed_to_extract = True
        retry_i = 0
        debug_messages = messages
        while failed_to_extract and (retry_i < max_retry):

            retry_i += 1
            self.logger.debug(f"Attempt: {retry_i}")

            function_calls = self._read_json_output(output=llm_response)

            if function_calls is None:
                debug_response = await self.llm_h.chat(debug_messages)
                llm_response = debug_response['message']['content']
                function_calls = read_json_output(output=llm_response)

            hfunctions, afunctions = self._get_hafunctions(
                function_calls = function_calls, 
                available_functions = available_functions)

            if hfunctions is None:
                continue

            if (function_calls is not None) and ((hfunctions is None) or (hfunctions == [])):
                return function_calls


            debug_messages = messages + [
                {'role' : 'assistant', "content" : llm_response},
                {"role": "user", "content": self.debug_prompt.format(
                    hfunctions = "\n -".join([h for h in hfunctions]),
                    afunctions = "\n -".join([a for a in afunctions]))}
            ]

            debug_response = await self.llm_h.chat(debug_messages)
            llm_response = debug_response['message']['content']


        if retry_i == max_retry:
            return None
