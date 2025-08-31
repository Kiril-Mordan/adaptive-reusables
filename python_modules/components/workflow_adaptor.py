"""
This module contains a set of tools to corrent initial llm-generated 
workflow for described task based on provided tools and adapt input and output models.
"""

import attrs
import attrsx

import asyncio

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

@attrs.define(kw_only=True)
class InputCollectorMock(ABC):

    @abstractmethod
    def fix_literal_values(self, planned_workflow : dict, adapted_workflow : dict,  *args, **kwargs):

        """
        Abstract method for fixing literal values in adapted workflow if necessary.
        """

        pass


@attrsx.define(handler_specs = {"llm" : LlmHandlerMock, "input_collector" : InputCollectorMock})
class WorkflowAdaptor:


    system_message : str = attrs.field(default=None)
    system_message_items : Dict[str, str] = attrs.field(default=None)
    debug_prompt : str = attrs.field(default=None)
    adapt_prompt : str = attrs.field(default=None)
    
    prompts_filepath : str = attrs.field(default=None)
    available_functions : List[LlmFunctionItem] = attrs.field(default=None)

    max_retry : int = attrs.field(default=5)

    """
    Adapts initially planned workflows
    """

    def __attrs_post_init__(self):

        self._assign_prompts()
        self._initialize_input_collector_h()

    def _assign_prompts(self, 
        prompts_filepath : str = None,
        system_message : str = None, 
        system_message_items : Dict[str,str] = None,
        debug_prompt : str = None,
        adapt_prompt : str = None
        ):

        if prompts_filepath is None: 
            prompts_filepath = self.prompts_filepath

        wa_path = pkg_resources.files('workflow_agent')

        if 'artifacts' in os.listdir(wa_path):

            if prompts_filepath is None:

                with pkg_resources.path('workflow_agent.artifacts.prompts',
                'workflow_adaptor.yml') as path:
                    prompts_filepath = path

            with open(prompts_filepath, 'r') as f:
                wa_prompts = yaml.safe_load(f)


        if system_message: 
            self.system_message = system_message
        else:
            self.system_message = wa_prompts['system_message']

        if system_message_items:
            self.system_message_items = system_message_items
        else:
            self.system_message_items = wa_prompts.get("system_message_items", {})

        if debug_prompt: 
            self.debug_prompt = debug_prompt
        else:
            self.debug_prompt = wa_prompts['debug_prompt']

        if adapt_prompt: 
            self.adapt_prompt = adapt_prompt
        else:
            self.adapt_prompt = wa_prompts['adapt_prompt']

    def _read_json_output(self, output : str) -> list | dict | None:

        try:

            if "```json" in output:
                output = output.replace("```json", "").replace("```", "")

            function_calls = json.loads(output)
        except Exception as e:
            self.logger.error(f"Failed to extract json from {output}")
            return None

        return function_calls

    def _make_current_state_schema(self, 
        workflow : list, 
        available_functions : List[LlmFunctionItem], 
        input_model : type(BaseModel) = None,
        func_name : str = None):

        base_state_schema = {}

        if input_model:
            base_state_schema['input_model'] = input_model.model_json_schema()

        if func_name is None:

            current_state_schema = {wd['name'] : [ad.output_schema_json \
                for ad in available_functions \
                    if ad.name == wd['name']][0] for wd in workflow}

            base_state_schema.update(current_state_schema)

            return base_state_schema
        else:
            current_state_schema = {}

            for step in workflow:

                if step['name'] == "input_model":
                    continue

                if step['name'] != func_name:
                    current_state_schema[step['name']] = [ad.output_schema_json \
                        for ad in available_functions \
                            if ad.name == step['name']][0]
                else:
                    break

            base_state_schema.update(current_state_schema)

            return base_state_schema

    def _resolve_ref(self, schema: Dict[str, Any], defs: Dict[str, Any]) -> Dict[str, Any]:
        """
        If the schema contains a $ref, resolve it using the provided defs dictionary.
        This function assumes that $ref is of the form "#/$defs/SomeDefinition".
        """
        if "$ref" in schema:
            ref = schema["$ref"]
            parts = ref.split("/")
            if len(parts) >= 3 and parts[1] == "$defs":
                ref_key = parts[2]
                if ref_key in defs:
                    # Recursively resolve in case the referenced definition has further $ref
                    return self._resolve_ref(defs[ref_key], defs)
        return schema

    def _check_reference(self, 
        reference: str, 
        target_field_schema: Dict[str, Any], 
        state: Dict[str, Dict[str, Any]], 
        id_func_mapping : Dict[str, str],
        current_function: str) -> List[str]:
        """
        Validate that a reference string is valid.
        
        A valid reference must have the exact format:
        <function_name>.output.<field_name>
        
        Additionally, the reference should not point to the output of the same function (self-reference).
        
        This function resolves the target_field_schema if it contains a $ref.
        
        Returns a list of error messages. If the list is empty, the reference is valid.
        """
        reference_errors = []
        
        # Extra check: disallow prefixes like "source:" or "string:".
        if reference.startswith("source:") or reference.startswith("string:"):
            reference_errors.append(f"Reference '{reference}' should not include a prefix like 'source:' or 'string:'.")
            return reference_errors

        pattern = r"^(?P<func_id>[^.]+)\.output\.(?P<field_name>[^.]+)$"
        match = re.fullmatch(pattern, reference)
        
        if not match:
            reference_errors.append(f"Invalid reference format: {reference}")
            return reference_errors
        
        func_name = id_func_mapping.get(match.group("func_id"), "")
        field_name = match.group("field_name")
        
        if func_name == current_function:
            reference_errors.append(f"Invalid self-reference: Function '{current_function}' should not reference its own output.")
            return reference_errors
        
        if func_name not in state:
            reference_errors.append(f"Function '{func_name}' not found in state for reference {reference}.")
            return reference_errors
        
        output_schema = state[func_name]
        properties = output_schema.get("properties", {})
        if field_name not in properties:
            reference_errors.append(f"Field '{field_name}' not found in output schema of '{func_name}' for reference {reference}.")
            return reference_errors
        
        source_type = properties[field_name].get("type")
        # Resolve any $ref in the target field schema
        target_field_schema = self._resolve_ref(target_field_schema, target_field_schema.get("$defs", {}))
        target_type = target_field_schema.get("type")
        if source_type != target_type:
            reference_errors.append(f"Type mismatch in reference '{reference}': expected target type '{target_type}', got source type '{source_type}'.")
            return reference_errors
        
        return reference_errors

    def _check_complex_mapping(self, 
        mapping: Any, 
        target_schema: Dict[str, Any],
        state: Dict[str, Dict[str, Any]], 
        id_func_mapping : Dict[str,str],
        current_function: str) -> List[str]:
        """
        Recursively validate a mapping object against the target JSON schema (which may include $ref)
        and available state.
        
        Parameters:
        mapping: The mapping object (literal, reference string, dict, or list).
        target_schema: The JSON schema (as produced by .model_json_schema()).
        state: A dictionary mapping function names to their output JSON schemas.
        current_function: The name of the current function (to check for self-references).
        
        Returns:
        A list of error messages. An empty list indicates the mapping is valid.
        """
        defs = target_schema.get("$defs", {})
        # Resolve $ref in the current schema node, if any.
        schema = self._resolve_ref(target_schema, defs)

        def _check(mapping: Any, schema: Dict[str, Any]) -> List[str]:
            # Resolve references in this schema node
            schema = self._resolve_ref(schema, defs)
            errors: List[str] = []
            
            if isinstance(mapping, str):
                # If the string contains '.output.', it is expected to be a reference.
                if ".output." in mapping:
                    errors.extend(self._check_reference(
                        reference = mapping, 
                        target_field_schema = schema, 
                        state = state,
                        id_func_mapping = id_func_mapping,
                        current_function = current_function))
                    return errors
                else:
                    # For a literal value, we can (optionally) enforce that the schema type is string.
                    if schema.get("type") == "string":
                        return []
                    # Otherwise, if literal value is provided where an object is expected, it's an error.
                    errors.append(f"Expected an object mapping (or valid reference), but got literal '{mapping}'.")
                    return errors

            if isinstance(mapping, dict):
                # If the schema expects a literal string but we got a dict, that's an error.
                if schema.get("type") == "string":
                    errors.append(f"Expected a literal string, but got an object: {mapping}")
                    return errors
                if schema.get("type") != "object":
                    errors.append("Expected an object mapping, but target schema is not an object.")
                    return errors
                target_properties = schema.get("properties", {})
                # Check required keys
                required_keys = schema.get("required", [])
                for req_key in required_keys:
                    if req_key not in mapping:
                        errors.append(f"Missing required key '{req_key}' in mapping.")
                for key, value in mapping.items():
                    if key not in target_properties:
                        errors.append(f"Key '{key}' not found in target schema properties.")
                        continue
                    child_errors = _check(value, target_properties[key])
                    if child_errors:
                        errors.extend(child_errors)
                        errors.append(f"Mapping for key '{key}' is invalid.")
                return errors

            if isinstance(mapping, list):
                if schema.get("type") != "array":
                    errors.append("Expected an array mapping, but target schema is not an array.")
                    return errors
                item_schema = schema.get("items")
                for idx, item in enumerate(mapping):
                    child_errors = _check(item, item_schema)
                    if child_errors:
                        errors.extend(child_errors)
                        errors.append(f"Mapping for array item at index {idx} is invalid.")
                return errors

            errors.append(f"Unexpected mapping type: {type(mapping)}")
            return errors

        return _check(mapping, schema)



    def _check_adapt_schema(self,
        llm_response : str, 
        target_schema : dict, 
        state : dict, 
        id_func_mapping : Dict[str,str],
        current_function : str):

        json_output = self._read_json_output(output=llm_response)
        mapping_errors = ['Provided output is not json!']

        if json_output:
            try:
                mapping_errors = self._check_complex_mapping(
                    mapping = json_output, 
                    target_schema = target_schema, 
                    state = state, 
                    id_func_mapping = id_func_mapping,
                    current_function=current_function)

            except Exception as e:
                self.logger.debug(f"error: {e}")

        return json_output, mapping_errors


    async def _adapt_func(self,
        func_name : str, 
        workflow : dict,
        workflow_current_state_schema : dict,
        available_functions : list,
        id_func_mapping : Dict[str,str],
        max_retry : int = 5):


        selected_function_input_schema, selected_function_input_schema_pyd = [
                (af.input_schema_json, af.input_model) for af in available_functions if af.name == func_name][0]

        if workflow_current_state_schema != {}:

            system_message_items = {
                "purpose_description" : "",
                "generated_workflow" : "",
                "workflow_current_state" : "",
                "expected_output_schema" : ""
            }

            if self.system_message_items.get("purpose_description"):
                system_message_items["purpose_description"] = self.system_message_items.get("purpose_description")

            if self.system_message_items.get("generated_workflow"):
                system_message_items["generated_workflow"] = self.system_message_items.get("generated_workflow").format(
                    raw_workflow = json.dumps(workflow))

            if self.system_message_items.get("workflow_current_state"):
                system_message_items["workflow_current_state"] = self.system_message_items.get("workflow_current_state").format(
                    workflow_current_state = json.dumps(workflow_current_state_schema))

            if self.system_message_items.get("expected_output_schema"):
                system_message_items["expected_output_schema"] = self.system_message_items.get("expected_output_schema")

            adapt_message_items = {
                "selected_function_name" : func_name,
                "selected_function_input_schema" : json.dumps(selected_function_input_schema)
            }

            messages = [
                {"role": "system", "content": self.system_message.format(
                    **system_message_items)},
                {"role": "user", "content": self.adapt_prompt.format(
                    **adapt_message_items)}
            ]

            retry = 0
            not_json_output = True
            mapping_errors = []
            while (not_json_output) and (retry < max_retry):
                retry += 1

                if mapping_errors:
                    errors = "\n ".join(iter(mapping_errors))
                    messages += [
                        {"role": "assistant", "content": llm_response},
                        {"role": "user", "content": self.debug_prompt.format(
                    mapping_errors = errors)}
                    ]
                    mapping_errors = []

                    self.logger.warning(f"Mapping errors: {errors}")

                
                response = await self.llm_h.chat(messages)
                llm_response = response['message']['content']
                
                json_output, mapping_errors = self._check_adapt_schema(
                    llm_response=llm_response, 
                    target_schema = selected_function_input_schema,
                    state=workflow_current_state_schema,
                    id_func_mapping=id_func_mapping,
                    current_function=func_name)

                not_json_output = mapping_errors != []

                if not not_json_output:
                    self.logger.debug(f"step: {func_name} adapted successfully on step {retry}! -------------------------------")
                else:
                    self.logger.debug(llm_response)
        else:
            #self.logger.warning("No input models was provided, llm planner inputs initialize workflow!")
            json_output = workflow[0]['args']


        return json_output

    def _add_fcall_ids(self, 
            workflow: dict,
            input_model : type(BaseModel) = None) -> dict:

        wf_base = []
        id_func_mapping_base = {"0" : "input_model"}

        if input_model:
            wf_base.append({"id" : 0, "name" : "input_model"})

        wf = wf_base + [{"id" : idx + 1, **d} for idx, d in enumerate(workflow)]
        id_func_mapping_u = {str(idx + 1) : d['name'] for idx, d in enumerate(workflow)}
        id_func_mapping_base.update(id_func_mapping_u)
        return wf, id_func_mapping_base

    async def adapt_workflow(
        self,
        workflow : dict,
        available_functions : List[LlmFunctionItem] = None,
        input_model : type(BaseModel) = None,
        max_retry : Optional[int] = None):

        """
        Adapts input and output models of planned workflow.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if available_functions is None:
            available_functions = self.available_functions

        if available_functions is None:
            raise ValueError("Input available_functions : List[LlmFunctionItem] cannot be None!")

        id_workflow, id_func_mapping = self._add_fcall_ids(
            workflow=workflow,
            input_model=input_model)

        workflow_current_state_schema = {step['name'] : self._make_current_state_schema(
            workflow = id_workflow, 
            available_functions = available_functions, 
            input_model = input_model,
            func_name = step['name']
        ) for step in workflow}

        # Create a list of tasks for each workflow step using adapt_func.
        adapt_tasks = [asyncio.create_task(self._adapt_func(
            func_name = step['name'],
            workflow = id_workflow,
            workflow_current_state_schema = workflow_current_state_schema[step['name']],
            available_functions = available_functions,
            id_func_mapping = id_func_mapping,
            max_retry = max_retry)) \
            for step in id_workflow if step["name"] != "input_model"]
        
        # Wait for all tasks to complete and gather their results.
        adapted_inputs = await asyncio.gather(*adapt_tasks)

        if input_model:
            adapted_inputs = [{}] + adapted_inputs

        adapted_workflow = [{"id" : step['id'], 'name' : step['name'], 'args': adapted_input} \
            for step, adapted_input in zip(id_workflow, adapted_inputs) \
                if step["name"] != "input_model"]

        new_workflow = self.input_collector_h.fix_literal_values(workflow, adapted_workflow)

        return adapted_workflow