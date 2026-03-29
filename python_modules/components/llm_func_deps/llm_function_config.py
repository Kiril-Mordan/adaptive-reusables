"""
Config models for llm_function runtime wiring.
"""

from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field


class LlmRuntimeConfig(BaseModel):
    """
    Reusable runtime settings for llm_function execution.
    """

    llm_handler_params: dict = Field(description="Parameters passed to WorkflowAutoAssembler LLM handler.")
    storage_path: Optional[str] = Field(default=None, description="Optional storage path for workflow persistence.")
    force_replan: bool = Field(default=False, description="Force workflow replanning instead of reusing cached workflows.")
    max_retry: Optional[int] = Field(default=None, description="Optional max retry override for planning loops.")
    reset_loops: Optional[int] = Field(default=None, description="Optional reset loop override for planning loops.")
    compare_params: Optional[dict] = Field(default=None, description="Optional compare parameters for workflow validation.")
    test_params: Optional[list] = Field(default=None, description="Optional test cases for planning/validation.")


class LlmFunctionConfig(BaseModel):
    """
    Bundled llm_function configuration for future config-driven decorator usage.
    """

    runtime: LlmRuntimeConfig = Field(description="Runtime settings for workflow execution.")
    tool_sources: Optional[Sequence[Any]] = Field(default=None, description="Configured tool sources for runtime loading.")
    tool_registry: Optional[Any] = Field(default=None, description="Optional prebuilt tool registry.")

    model_config = {
        "arbitrary_types_allowed": True,
    }
