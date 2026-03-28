# Workflow Cache

This page explains how Workflow Auto Assembler reuses previously planned workflows through in-memory cache and filesystem storage.

## Why Cache Workflows

Planning a workflow can involve:

- initial feasibility checking
- planner calls
- adaptor calls
- optional test-driven repair loops

If the same task and I/O schemas are used again, WAA can often reuse an already assembled workflow instead of planning from scratch.

## Workflow Identity

WAA computes a stable `input_id` from:

- `task_description`
- `input_model`
- `output_model`

This hash is used as the lookup key for workflow reuse.

## Two Reuse Layers

WAA uses two reuse layers:

- **In-memory cache**: `storage_h.workflow_cache`
- **Filesystem storage**: saved workflow JSON files under `workflows/`

The in-memory cache is the fastest path inside a running process. Filesystem storage makes workflows reusable across sessions.

## Storage Layout

Workflows are saved under:

- `<storage_path>/workflows/`

Each saved workflow uses the filename pattern:

- `<input_id>_<workflow_id>_<timestamp>.json`

This keeps workflow history append-only and allows WAA to search for the newest reusable workflow for a given `input_id`.

## Latest vs Latest Complete

When loading workflows by `input_id`, WAA can:

- load the newest workflow of any status
- load the newest **completed** workflow

For completed lookup, WAA checks saved candidates from newest to oldest and returns the first one where `workflow_completed == True`.

This matters because newer workflow attempts may exist but still be incomplete or failed.

## `actualize_workflow`

`actualize_workflow` is the high-level reuse entrypoint.

Its normal behavior is:

1. Compute `input_id`
2. Check in-memory cache
3. If missing, check storage for the latest completed workflow
4. If still missing, plan a new workflow
5. Save the new workflow to storage
6. Cache it
7. Run it
8. Return outputs

So the same function handles both:

- first-time planning
- later workflow reuse

## Force Replanning

If you want to ignore existing cache and storage reuse, call:

- `actualize_workflow(..., force_replan=True)`

This skips the reuse lookup path and creates a fresh workflow plan.

## Incomplete Workflows

If a workflow object has `workflow_completed == False`, WAA does not try to execute it through `run_workflow`.

Instead, it returns the latest known workflow error from the stored planning state. This makes incomplete workflow reuse safer and easier to debug.

## Practical Use

Workflow cache is useful when:

- the task description is stable
- input/output schemas are stable
- planning is relatively expensive
- you want repeatable execution across sessions

This lets WAA act more like a reusable workflow runtime and less like a planner that starts from scratch every time.
