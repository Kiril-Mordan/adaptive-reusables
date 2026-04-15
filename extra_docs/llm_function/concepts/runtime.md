# Runtime

`LlmFunctionRuntime` is the reusable runtime object for `llm_function`.

It exists so multiple decorated functions or repeated calls can reuse the same initialized runtime state.

## What Runtime Reuses

In the current implementation, runtime is responsible for:

- resolving tools once
- initializing a shared [`workflow_auto_assembler`](https://pypi.org/project/workflow-auto-assembler/) instance once
- reusing that initialized instance across calls

## Why Runtime Exists

Without a shared runtime, each decorated call has to build runtime state again.

With `LlmFunctionRuntime`, repeated calls can reuse:

- the same resolved toolset
- the same in-memory workflow cache held by WAA

This is especially useful when:

- multiple LLM-backed functions share the same tools
- one process makes repeated calls for similar tasks

## Relationship To Config

`LlmRuntimeConfig` is configuration data.

`LlmFunctionRuntime` is the initialized execution object built from configuration and tool sources.

That means:

- config describes runtime settings
- runtime holds shared initialized state

## Example

```python
from llm_function import (
    InMemoryToolSource,
    LlmFunctionConfig,
    LlmFunctionRuntime,
    LlmRuntimeConfig,
    llm_function,
)

tool_sources = [
    InMemoryToolSource([get_weather, send_report_email]),
]

runtime_config = LlmRuntimeConfig(
    llm_handler_params={
        "llm_h_type": "ollama",
        "llm_h_params": {
            "connection_string": "http://localhost:11434",
            "model_name": "gpt-oss:20b",
        },
    },
    storage_path="/tmp",
)

llm_config = LlmFunctionConfig(
    runtime=runtime_config,
    tool_sources=tool_sources,
)

llm_runtime = LlmFunctionRuntime(config=llm_config)


@llm_function(runtime=llm_runtime)
def get_city_weather(input: WfInputs) -> WfOutputs:
    """
    Get weather for the provided city and prepare a short summary.
    """
```

In this setup, repeated calls reuse the same initialized runtime instead of constructing a new `WorkflowAutoAssembler` for every function call.
