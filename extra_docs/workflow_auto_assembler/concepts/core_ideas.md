# Core Ideas

This page explains the core ideas behind Workflow Auto Assembler (WAA) and how to think about it when designing your tools and tasks.

![waa-flow](workflow_auto_assembler-flow.png)

## What WAA Builds

WAA builds an **executable workflow**: a list of ordered steps where each step calls one tool (function) with structured arguments. Each step writes its output, and later steps can reference those outputs.

At runtime, the workflow looks like:

- Step `0`: the input model (`0.output.*`)
- Step `1..N`: tool calls (`1.output.*`, `2.output.*`, ...)
- Final step: `output_model` (optional, but recommended for validation)

## How References Work

Arguments can be literals or **references** to earlier outputs.

Examples:

- Literal: `"city": "Berlin"`
- Reference: `"city": "0.output.city"` (from input model)
- Reference: `"content": "2.output.info"` (from step 2 output)

WAA resolves these references at execution time.

## The Three Core Components

WAA separates planning from execution:

- **Planner**: selects tools and drafts a workflow structure.
- **Adaptor**: rewires arguments to match schemas and converts literals vs references.
- **Runner**: executes the workflow and validates outputs.

This separation makes the plan stable, repeatable, and testable.

## Inputs, Outputs, and Tests

- `input_model`: defines the user inputs.
- `output_model`: defines expected outputs (recommended).
- `test_params`: optional list of input/output pairs used to validate the planned workflow.

If tests pass, the workflow is considered stable. If not, WAA attempts repairs.

## Error Types and Resets (High Level)

When a workflow fails, WAA uses error types to decide what to retry:

- **Planner reset** when the workflow structure is wrong.
- **Adaptor reset** when mappings are wrong.
- **Runner error** when execution fails.

This is a test‑driven repair loop rather than code generation.

## Practical Mental Model

Think of WAA as a **schema‑constrained planner** that composes your existing functions into a reproducible workflow and then keeps refining it until tests pass.

If you provide:

- deterministic functions
- clear input/output schemas
- simple test cases

you get predictable and reusable workflows.

