"""
The module contains general pydantic models used within workflow-agent components
"""

import inspect
import hashlib
import json
from typing import Type, get_type_hints
from collections.abc import Callable
from pydantic import BaseModel, Field, SkipValidation
from enum import Enum

class LlmFunctionItemInput(BaseModel):

    """
    Function suitable for llm use.
    """

    func: SkipValidation[Callable[..., Any]]
    input_model: Optional[Type[BaseModel]] = Field(default=None, description = "Optional input model for function, if cannot be derived from func definition.")
    output_model: Optional[Type[BaseModel]] = Field(default=None, description = "Optional output model for function, if cannot be derived from func definition.")

    model_config = {
        "arbitrary_types_allowed": True
    }

class LlmFunctionItem(BaseModel):

    """
    Function suitable for llm use.
    """

    func_id : str
    name : str
    description : str
    input_schema_json : dict
    output_schema_json : dict

class WorkflowErrorType(Enum):
    CHECK_JSON = "check_json"
    PLANNING_JSON = "planning_json"
    PLANNING_MISSOUTPUT = "planning_missoutput"
    PLANNING_HF = "planning_hf"
    ADAPTOR_JSON = "adaptor_json"
    RUNNER = "runner"
    INPUTS = "inputs"
    OUTPUTS_FAILURE = "outputs_failure"
    OUTPUTS_UNEXPECTED = "outputs_unexpected"

class WorkflowError(BaseModel):

    error_message: Optional[str] = Field(default=None, description = "Error message if function call fails.")
    error_type: Optional[WorkflowErrorType] = Field(default=None, description = "Error type of failed call.")
    additional_info: Optional[dict] = Field(default={}, description = "Optional additional info for the error.")

    model_config = {
        "arbitrary_types_allowed": True
    }

def _hash_string_sha256(input_string: str) -> str:
        return hashlib.sha256(input_string.encode()).hexdigest()

def make_uid(d: dict) -> str:

    input_string = json.dumps(d)

    return _hash_string_sha256(input_string)

def create_function_item(
  func: callable, 
  input_model: Type[BaseModel] = None, 
  output_model: Type[BaseModel] = None) -> dict:
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
      - "func_id" : unique id of the function
      - "name": the function's name.
      - "description": the function's description (docstring).
      - "input_schema_json": the JSON schema (as a dict) for the input model.
      - "output_schema_json": the JSON schema (as a dict) for the output model.

  """

  if input_model is None or output_model is None:
    hints = get_type_hints(func)

  if input_model is None:
    input_model = hints.get("inputs")

  if output_model is None:
    output_model = hints.get("return")

  llm_func_item = {
    "name" : func.__name__,
    "description" : func.__doc__.strip() if func.__doc__ else "",
    "input_schema_json" : input_model.model_json_schema(),
    "output_schema_json" : output_model.model_json_schema()
  }

  return LlmFunctionItem(
      func_id = make_uid(d = {**llm_func_item, "code" : inspect.getsource(func)}),
      **llm_func_item
  )

def _fill_hints(fi):
    hints = get_type_hints(fi.func)
    fi.input_model = fi.input_model or hints.get("inputs")
    fi.output_model = fi.output_model or hints.get("return")
    return fi

def create_avc_items(functions : List[LlmFunctionItemInput]):

  """
  Creates available functions and callables for Workflow Auto Assembler
  """

  hints_for_functions = [get_type_hints(fi.func) for fi in functions]
  functions_after_hints = [_fill_hints(fi) for fi in functions]

  llm_func_items = [{
    "name" : fi.func.__name__,
    "description" : fi.func.__doc__.strip() if fi.func.__doc__ else "",
    "input_schema_json" : fi.input_model.model_json_schema(),
    "output_schema_json" : fi.output_model.model_json_schema(),
    "code" : inspect.getsource(fi.func)
  } for fi in functions_after_hints]

  
  available_functions = [
    LlmFunctionItem(
        func_id = make_uid(d = llm_func_item),
        **{k : v for k,v in llm_func_item.items() if k != "code"}
    ) for llm_func_item in llm_func_items
  ]

  available_callables = {
    make_uid(d = llm_func_item) : fi.func \
      for llm_func_item, fi in zip(llm_func_items,functions)
  }

  return {
    "available_functions" : available_functions,
    "available_callables" : available_callables
  }