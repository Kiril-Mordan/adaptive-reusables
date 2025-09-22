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