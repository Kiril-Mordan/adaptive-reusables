# Tools

`llm_function` works from tool definitions that are converted into:

- `available_functions`
- `available_callables`

These are the structures passed into [`workflow_auto_assembler`](https://pypi.org/project/workflow-auto-assembler/) for planning and execution.

## Where Tools Can Come From

Current tool-loading paths include:

- in-memory callables
- standalone `.py` files
- Python modules

The lower-level tool definition helpers live in [`llm_function_tools`](https://pypi.org/project/llm-function-tools/).

## Why Tools Matter

The workflow planner can only assemble workflows from the tools it is given.

That means tool descriptions and schemas affect:

- whether a task is considered possible
- which workflow steps are chosen
- whether a saved workflow is still reusable later

## Tool Sources

The current `llm_function` runtime supports tool-loading through source objects such as:

- `InMemoryToolSource`
- `PythonFileToolSource`
- `PythonModuleToolSource`

These let you keep tool definitions close to the use case that needs them, or organize them into reusable modules.
