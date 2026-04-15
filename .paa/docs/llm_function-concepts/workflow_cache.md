# Workflow Cache

`llm_function` inherits workflow reuse behavior from [`workflow_auto_assembler`](https://pypi.org/project/workflow-auto-assembler/).

That means workflow reuse can involve:

- in-memory cache
- filesystem storage
- workflow replanning when stale saved workflows no longer match the current toolset

## Runtime Interaction

When you use `LlmFunctionRuntime`, repeated decorated calls reuse the same initialized WAA instance.

That also means they reuse the same in-memory workflow cache held by WAA.

## More Detail

For deeper cache behavior, see the WAA docs:

- [Workflow Cache](https://kiril-mordan.github.io/adaptive-reusables/workflow_auto_assembler/workflow_cache/)
- [Core Ideas](https://kiril-mordan.github.io/adaptive-reusables/workflow_auto_assembler/core_ideas/)
