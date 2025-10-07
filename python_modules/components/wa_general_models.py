"""
The module contains general pydantic models used within workflow-agent components
"""

import json
from typing import Type
from pydantic import BaseModel, Field
from enum import Enum

class LlmFunctionItem(BaseModel):

    """
    Function suitable for llm use.
    """

    name : str
    description : str
    input_schema_json : dict
    output_schema_json : dict

class WorkflowErrorType(Enum):
    PLANNING_JSON = "planning_json"
    PLANNING_MISSOUTPUT = "planning_missoutput"
    PLANNING_HF = "planning_hf"
    ADAPTOR_JSON = "adaptor_json"
    RUNNER = "runner"
    INPUTS = "inputs"
    OUTPUTS = "outputs"

class WorkflowError(BaseModel):

    error_message: Optional[str] = Field(default=None, description = "Error message if function call fails.")
    error_type: Optional[WorkflowErrorType] = Field(default=None, description = "Error type of failed call.")
    additional_info: Optional[dict] = Field(default={}, description = "Optional additional info for the error.")

    model_config = {
        "arbitrary_types_allowed": True
    }

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
        output_schema_json = output_model.model_json_schema()
    )