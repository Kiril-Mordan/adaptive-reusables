# Workflow Auto Assembler (WAA) Positioning

Workflow Auto Assembler (WAA) is a schema‑first planner that **auto‑assembles executable workflows** from a natural‑language task description plus target input/output models. Unlike common tool‑calling or pipeline frameworks that rely on user‑authored graphs, WAA **selects and wires available tools** into a structured workflow, then validates it with runner‑based tests. When outputs deviate from expectations, WAA applies **test‑driven repair** (planner/adaptor resets) to revise the workflow rather than emit new code, and can promote successful workflows as reusable tools. This combination—**schema‑constrained composition + explicit test/diff‑guided repair + workflow‑as‑tool reuse**—distinguishes WAA from standard function‑calling loops or manual pipeline builders.


## WAA vs multi‑agent tool calling

Multi‑agent tool‑calling systems are typically reactive: they decide each next step based on the current prompt, which can drift when context is truncated or when intermediate data is too large or too sensitive to include. WAA separates planning from execution by persisting the workflow as a structured graph with explicit I/O mappings. That plan survives across LLM calls and relies on externalized state (tool outputs referenced by ID/path), so large or private data never needs to re‑enter the model context. This makes WAA better suited for long, multi‑step tasks where continuity, privacy, and predictable execution are required.


## Drift and schema‑strict planning

LLMs do not retain state across calls; each step reconstructs its “mind‑state” from the prompt. That reconstruction can drift when context is truncated, interpreted differently, or partially omitted—especially in multi‑step plans. For schema‑strict tool selection and wiring, even small drift can cause invalid mappings or wrong field selection. WAA mitigates this by externalizing the plan as a structured workflow and relying on explicit I/O schemas plus test‑driven feedback, reducing dependence on fragile in‑context memory.
