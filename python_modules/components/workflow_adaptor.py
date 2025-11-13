"""
This module contains a set of tools to corrent initial llm-generated 
workflow for described task based on provided tools and adapt input and output models.
"""

import attrs
import attrsx

import asyncio

import yaml
import os
import re
import json

import importlib
import importlib.metadata
import importlib.resources as pkg_resources

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, get_args, get_origin, Type
from pydantic import BaseModel, Field, create_model


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

class WorkflowAdaptorStep(BaseModel):

    step_id : int = Field(description = "Step id.")
    func_name : str = Field(description = "Function name used in the step.")
    retries : int = Field(description = "Number of attempt it took to generate workflow.")
    init_messages : List[dict] = Field(default = None, description = "Initial messages for adapting workflow.")
    errors : List[BaseModel] = Field(description = "Errors during planning.")
    adapted_schema : Optional[dict] = Field(default = None, description = "Planned workflow.")
    state_schema: Optional[dict] = Field(default = None, description = "Schema of steps before this one in the workflow.")
    target_schema : Optional[dict] = Field(default = None,description = "Target schema from available functions.")

    model_config = {
        "arbitrary_types_allowed": True
    }

class WorkflowAdaptorResponse(BaseModel):

    total_retries : int = Field(description = "Number of attempt it took to adapt workflow.")
    planned_workflow : Optional[List[dict]] = Field(default = None, description = "Planned workflow.")
    workflow : Optional[List[dict]] = Field(default = None, description = "Adapted workflow.")
    all_errors : List[BaseModel] = Field(description = "Errors during planning.")
    steps : List[WorkflowAdaptorStep] = Field(description = "Steps it took to adapt workflow.")
    include_input : bool = Field(description = "If input model is expected.")
    include_output : bool = Field(description = "If output model is expected.")

    model_config = {
        "arbitrary_types_allowed": True
    }

@attrsx.define(handler_specs = {"llm" : LlmHandlerMock, "input_collector" : InputCollectorMock})
class WorkflowAdaptor:

    workflow_error_types = attrs.field()
    workflow_error = attrs.field()

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

        wa_path = pkg_resources.files('workflow_auto_assembler')

        if 'artifacts' in os.listdir(wa_path):

            if prompts_filepath is None:

                with pkg_resources.path('workflow_auto_assembler.artifacts.prompts',
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
            self.logger.error(f"Problem with JSON: {e}")
            return None

        return function_calls

    def _make_current_state_schema(self, 
        workflow : list, 
        available_functions : List[LlmFunctionItem], 
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        func_name : str = None):

        base_state_schema = {}

        if input_model:
            base_state_schema['input_model'] = input_model.model_json_schema()

        if func_name is None:

            current_state_schema = {wd['name'] : [ad.output_schema_json \
                for ad in available_functions \
                    if ad.name == wd['name']][0] for wd in workflow}

            base_state_schema.update(current_state_schema)

            if output_model:
                base_state_schema['output_model']: output_model.model_json_schema()

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

            if output_model:
                base_state_schema['output_model']: output_model.model_json_schema()

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


    def _prep_init_messages(self,
        func_name : str, 
        workflow : dict,
        workflow_current_state_schema : dict,
        available_functions : list,
        id_func_mapping : Dict[str,str],):

        selected_function_input_schema, selected_function_input_schema_pyd = [
                (af.input_schema_json, self.json_schema_to_base_model(af.input_schema_json)) for af in available_functions if af.name == func_name][0]

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

        return messages, selected_function_input_schema

    def _check_llm_response(self,
        llm_response : str, 
        step_id : str,
        target_schema : dict, 
        state : dict, 
        id_func_mapping : Dict[str,str],
        current_function : str,
        init_error : Optional[Type[BaseModel]] = None):

        if init_error:
            return init_error

        function_calls = self._read_json_output(output=llm_response)

        if function_calls is None:
            return self.workflow_error(
                error_type = self.workflow_error_types.ADAPTOR_JSON,
                additional_info = {
                    "step_id" : step_id,
                    "error_messages" : ['Provided output is not json!']})

        try:
            mapping_errors = self._check_complex_mapping(
                mapping = function_calls, 
                target_schema = target_schema, 
                state = state, 
                id_func_mapping = id_func_mapping,
                current_function=current_function)

            if mapping_errors:
                return self.workflow_error(
                    error_type = self.workflow_error_types.ADAPTOR_JSON,
                    additional_info = {
                        "step_id" : step_id,
                        "error_messages" : [erm for erm in mapping_errors]})

        except Exception as e:
            return self.workflow_error(
                error_type = self.workflow_error_types.ADAPTOR_JSON,
                additional_info = {
                    "step_id" : step_id,
                    "error_messages" : [str(e)]})

        return None

    async def _adapt_func(self,
        func_name : str = None, 
        step_id : str = None,
        workflow : dict = None,
        workflow_current_state_schema : dict = None,
        available_functions : list = None,
        id_func_mapping : Dict[str,str] = None,
        adapted_step = None,
        max_retry : int = 5):
        
        if workflow_current_state_schema != {}:
                
            if adapted_step is None :

                workflow = workflow.copy()

                init_messages, target_schema = self._prep_init_messages(
                    func_name = func_name, 
                    workflow = workflow,
                    workflow_current_state_schema = workflow_current_state_schema,
                    available_functions = available_functions,
                    id_func_mapping = id_func_mapping
                )
                
                retry_i = 0
                not_json_output = True
                errors = []
                init_error = None

                response = await self.llm_h.chat(init_messages)
                llm_response = response.message.content
            else:
                step_id = adapted_step.step_id
                init_messages = adapted_step.init_messages
                llm_response = json.dumps(adapted_step.workflow)
                retry_i = adapted_step.retries
                errors = adapted_step.errors
                init_error = errors[-1]
                target_schema = adapted_step.target_schema
                func_name = adapted_step.func_name

            retry_messages = init_messages

            while retry_i < max_retry:

                error = self._check_llm_response(
                    llm_response=llm_response,
                    step_id=step_id, 
                    target_schema = target_schema,
                    state=workflow_current_state_schema,
                    id_func_mapping=id_func_mapping,
                    current_function=func_name)

                if error is None:
                    adapted_schema = self._read_json_output(output=llm_response)
                    return WorkflowAdaptorStep(
                        step_id = step_id,
                        func_name = func_name,
                        errors = errors,
                        adapted_schema = adapted_schema,
                        state_schema = workflow_current_state_schema,
                        target_schema = target_schema,
                        retries = retry_i,
                        init_messages = init_messages
                    )

                retry_i += 1
                if init_error:
                    init_error = None
                else:
                    errors.append(error)

                self.logger.debug(f"Attempt for {func_name}: {retry_i}")

                if error.error_type is self.workflow_error_types.ADAPTOR_JSON:

                    mapping_errors = "\n ".join(iter(error.additional_info["error_messages"]))
                    retry_messages += [
                        {"role": "assistant", "content": llm_response},
                        {"role": "user", "content": self.debug_prompt.format(
                    mapping_errors = mapping_errors)}
                    ]

                    debug_response = await self.llm_h.chat(retry_messages)
                    llm_response = debug_response.message.content
                    continue
            
        else:
            return WorkflowAdaptorStep(
                step_id = step_id,
                func_name = func_name,
                errors = [],
                adapted_schema = workflow[0]['args'],
                state_schema = workflow_current_state_schema,
                retries = 0,
                target_schema = {},
                init_messages = []
            )


        if retry_i == max_retry:
            return WorkflowAdaptorStep(
                step_id = step_id,
                func_name = func_name,
                errors = errors,
                adapted_schema = None,
                state_schema = None,
                retries = retry_i,
                target_schema = target_schema,
                init_messages = init_messages
            )

    def _hash_string_sha256(self, input_string: str) -> str:
        return hashlib.sha256(input_string.encode()).hexdigest()

    def _make_uid(self, d: dict) -> str:

        input_string = json.dumps(d)

        return self._hash_string_sha256(input_string)
    
    def _mod_inputs_for_output_model(self, 
        workflow : List[dict],
        output_model : Type[BaseModel],
        available_functions : List[LlmFunctionItem],
        ):

        workflow_s = workflow
        available_functions_t = available_functions
        if output_model:
            workflow_s += [{'id': len(workflow) + 1 , 'name': 'output_model'}]
            output_item = {
                "name" : "output_model", 
                "description" : "Schema to which relevant workflow outputs should be connected to.",
                "input_schema_json" : output_model.model_json_schema(),
                "output_schema_json" : output_model.model_json_schema(),
            }
            available_functions_t += [LlmFunctionItem(
                func_id = self._make_uid(d = output_item),
                **output_item
                )]

        return workflow_s, available_functions_t


    def _add_fcall_ids(self, 
            workflow: dict,
            input_model : Type[BaseModel] = None,
            output_model : Type[BaseModel] = None) -> dict:

        wf_base = []
        id_func_mapping_base = {"0" : "input_model"}

        if input_model:
            wf_base.append({"id" : 0, "name" : "input_model"})

        wf = wf_base + [{"id" : idx + 1, **d} for idx, d in enumerate(workflow)]
        id_func_mapping_u = {str(idx + 1) : d['name'] for idx, d in enumerate(workflow)}
        id_func_mapping_base.update(id_func_mapping_u)

        # if output_model:
        #     id_func_mapping_base.update({str(len(wf)) : "output_model"})
        #     wf.append({"id" : len(wf), "name" : "output_model"})

        return wf, id_func_mapping_base

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

    async def adapt_workflow(
        self,
        workflow : List[dict] = None,
        available_functions : List[LlmFunctionItem] = None,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        max_retry : Optional[int] = None,
        adapted_workflow : Optional[WorkflowAdaptorResponse] = None):

        """
        Adapts input and output models of planned workflow.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if available_functions is None:
            available_functions = self.available_functions

        if available_functions is None:
            raise ValueError("Input available_functions : List[LlmFunctionItem] cannot be None!")

        include_input = False
        include_output = False
        if input_model:
            include_input = True
        if output_model:
            include_output = True

        if adapted_workflow is None:

            workflow = workflow.copy()

            id_workflow, id_func_mapping = self._add_fcall_ids(
                workflow=workflow,
                input_model=input_model,
                output_model=output_model)

            workflow_s, available_functions_t = self._mod_inputs_for_output_model(
                workflow=workflow,
                available_functions=available_functions,
                output_model=output_model
            )
                
            workflow_current_state_schema = {step['name'] : self._make_current_state_schema(
                workflow = id_workflow, 
                available_functions = available_functions, 
                input_model = input_model,
                output_model=output_model,
                func_name = step['name']
            ) for step in workflow_s}

            # Create a list of tasks for each workflow step using adapt_func.
            adapt_tasks = [asyncio.create_task(self._adapt_func(
                step_id = step["id"],
                func_name = step['name'],
                workflow = id_workflow,
                workflow_current_state_schema = workflow_current_state_schema[step['name']],
                available_functions = available_functions_t,
                id_func_mapping = id_func_mapping,
                max_retry = max_retry)) \
                for step in id_workflow if step["name"] != "input_model"]
            
            # Wait for all tasks to complete and gather their results.
            adapted_steps = await asyncio.gather(*adapt_tasks)


            adapted_workflow = [{
                "id" : adapted_step.step_id, 
                "func_id" : [av.func_id for av in available_functions_t if av.name == adapted_step.func_name][0],
                'name' : adapted_step.func_name, 
                'args': adapted_step.adapted_schema} \
            for adapted_step in adapted_steps]

            adapted_fixed_workflow = self.input_collector_h.fix_literal_values(workflow, adapted_workflow)

            return WorkflowAdaptorResponse(
                total_retries = sum([adapted_step.retries for adapted_step in adapted_steps]),
                planned_workflow = id_workflow,
                workflow = adapted_fixed_workflow,
                all_errors = [err for adapted_step in adapted_steps for err in adapted_step.errors],
                steps = adapted_steps,
                include_input = include_input,
                include_output = include_output
            )

        else:
            retried_step_id = adapted_workflow.all_errors[-1].additional_info["step_id"]
            retried_step = [step for step in adapted_workflow.workflow if step["id"] == retried_step_id][0]
            retried_step_obj = [step_obj for step_obj in adapted_workflow.steps if step_obj.step_id == retried_step_id][0]

            id_func_mapping = {}

            if adapted_workflow.include_input:
                id_func_mapping["0"] = "input_model"
            
            id_func_mapping_u = {str(step_obj.step_id) : step_obj.func_name for step_obj in adapted_workflow.steps}
            id_func_mapping.update(id_func_mapping_u)

            reset_step = await self._adapt_func(
                step_id = retried_step_id,
                func_name = retried_step['name'],
                workflow = adapted_workflow.planned_workflow,
                workflow_current_state_schema = retried_step_obj.state_schema,
                available_functions = available_functions,
                id_func_mapping = id_func_mapping,
                max_retry = max_retry)

            adapted_workflow.total_retries += reset_step.retries
            adapted_workflow.all_errors += reset_step.errors

            reset_step.errors = retried_step_obj.errors + reset_step.errors
            reset_step.retries += retried_step_obj.retries
            
            adapted_workflow.steps = [reset_step \
                if step.step_id == retried_step_id else step \
                for step in adapted_workflow.steps]

            adapted_workflow.workflow = [{
                'id': wstep['id'], 
                'func_id' : wstep['func_id'],
                'name' : wstep['name'], 
                'args' : reset_step.adapted_schema} if wstep['id'] == retried_step_id else wstep \
                for wstep in adapted_workflow.workflow]

            return adapted_workflow
            

        