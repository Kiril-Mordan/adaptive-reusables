# `@llm_function`

`@llm_function` turns a typed Python function into a reusable LLM-backed function.

The decorator does not use the function body. Instead, it uses:

- the function input annotation as the workflow input model
- the return annotation as the workflow output model
- the function docstring as the task description

At call time, it delegates to [`workflow_auto_assembler`](https://pypi.org/project/workflow-auto-assembler/) to assemble or reuse a workflow that satisfies that contract.

## What The Decorator Expects

The decorated function should:

- accept exactly one argument annotated with a Pydantic `BaseModel`
- return a Pydantic `BaseModel`
- include a docstring describing the task

Example:

```python
from pydantic import BaseModel, Field

from llm_function import llm_function


class WfInputs(BaseModel):
    city: str = Field(..., description="City name.")


class WfOutputs(BaseModel):
    summary: str = Field(..., description="Weather summary.")


@llm_function(
    available_functions=available_tools["available_functions"],
    available_callables=available_tools["available_callables"],
    llm_handler_params={...},
)
def get_city_weather(input: WfInputs) -> WfOutputs:
    """
    Get weather for the provided city and prepare a short summary.
    """
```

## Configuration Styles

`@llm_function` currently supports three configuration styles:

### 1. Direct Arguments

Pass tool lists and runtime settings directly to the decorator.

Use this for small scripts or one-off examples.

### 2. `config=...`

Pass `LlmFunctionConfig`, which bundles:

- `LlmRuntimeConfig`
- tool sources or a prebuilt tool registry

Use this when multiple decorated functions should share the same configuration.

### 3. `runtime=...`

Pass `LlmFunctionRuntime` when you want a shared initialized runtime.

Use this when:

- multiple decorated functions should reuse the same initialized runtime
- you want to reuse the same in-memory workflow cache
- you do not want to initialize `WorkflowAutoAssembler` on every call

Runtime details are described in [Concepts](../concepts/concepts.md).

## Errors

If workflow assembly or execution fails, the decorator raises `LlmFunctionError`.

This keeps the function contract consistent: successful calls return the declared output model, and failures raise.

## Notes

- Dict inputs are coerced into the declared input model.
- The decorated function body is ignored.
- The returned callable exposes `input_model`, `output_model`, and `task_description` attributes.
