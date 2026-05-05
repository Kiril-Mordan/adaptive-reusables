from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _workflows_dir(storage_path: str | Path) -> Path:
    return Path(storage_path) / "workflows"


def _sort_candidate_paths(paths: list[Path]) -> list[Path]:
    def _sort_key(path: Path) -> tuple[str, str]:
        parts = path.stem.rsplit("_", 2)
        if len(parts) == 3:
            return parts[2], path.name
        return "", path.name

    return sorted(paths, key=_sort_key, reverse=True)


def _unwrap(value: Any) -> Any:
    if isinstance(value, dict):
        marker = value.get("__workflow_storage__")
        if marker == "pydantic_model":
            return _unwrap(value.get("data", {}))
        return {key: _unwrap(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_unwrap(item) for item in value]
    return value


def _candidate_paths(storage_path: str | Path, input_id: str) -> list[Path]:
    return _sort_candidate_paths(list(_workflows_dir(storage_path).glob(f"{input_id}_*.json")))


def discover_input_ids(storage_path: str | Path) -> list[str]:
    workflows_dir = _workflows_dir(storage_path)
    return sorted({
        parts[0]
        for filepath in workflows_dir.glob("*.json")
        for parts in [filepath.stem.rsplit("_", 2)]
        if len(parts) == 3
    })


def load_saved_workflows(
    storage_path: str | Path,
    input_ids: list[str] | None = None,
    completed_only: bool = False,
    latest_only: bool = False,
) -> list[dict[str, Any]]:
    target_input_ids = input_ids if input_ids is not None else discover_input_ids(storage_path=storage_path)

    workflows: list[dict[str, Any]] = []
    for input_id in target_input_ids:
        for candidate_path in _candidate_paths(storage_path=storage_path, input_id=input_id):
            try:
                payload = json.loads(candidate_path.read_text(encoding="utf-8"))
                workflow_object = _unwrap(payload)
            except Exception:
                continue

            if completed_only and not workflow_object.get("workflow_completed", False):
                continue

            workflows.append(workflow_object)
            if latest_only:
                break

    return workflows


def workflow_to_record(workflow_object: dict[str, Any]) -> dict[str, Any]:
    planning = workflow_object.get("planning") or {}
    init_check = workflow_object.get("init_check") or {}
    planner = planning.get("planner") or {}
    adaptor = planning.get("adaptor") or {}
    tester = planning.get("tester") or {}

    testing_errors = list(planning.get("testing_errors") or [])
    planner_errors = list(planner.get("errors") or [])
    adaptor_errors = list(adaptor.get("all_errors") or [])
    tester_error = tester.get("error")

    terminal_error = testing_errors[-1] if testing_errors else None
    if terminal_error is None:
        terminal_error = tester_error
    if terminal_error is None and adaptor_errors:
        terminal_error = adaptor_errors[-1]
    if terminal_error is None and planner_errors:
        terminal_error = planner_errors[-1]

    terminal_error_type = None
    terminal_error_message = None
    failing_paths: list[str] = []
    failing_step_ids: list[int] = []
    if isinstance(terminal_error, dict):
        terminal_error_type = terminal_error.get("error_type")
        terminal_error_message = terminal_error.get("error_message")
        additional_info = terminal_error.get("additional_info") or {}
        failing_paths = list(additional_info.get("failing_paths", []) or [])
        failing_step_ids = list(additional_info.get("failing_step_ids", []) or [])

    workflow_steps = workflow_object.get("workflow") or []
    case_results = list(tester.get("case_results") or [])

    return {
        "input_id": workflow_object.get("input_id"),
        "workflow_id": workflow_object.get("id"),
        "saved_at": workflow_object.get("saved_at"),
        "workflow_possible": workflow_object.get("workflow_possible"),
        "workflow_completed": workflow_object.get("workflow_completed"),
        "loops": workflow_object.get("loops"),
        "task_description": (workflow_object.get("description") or {}).get("task_description"),
        "workflow_step_count": len(workflow_steps),
        "tools_used": [
            step.get("name")
            for step in workflow_steps
            if step.get("name") and step.get("name") != "output_model"
        ],
        "init_check_possible": init_check.get("workflow_possible"),
        "init_check_retries": init_check.get("retries"),
        "planner_retries": planner.get("retries"),
        "planner_error_count": len(planner_errors),
        "planner_reset_count": len(list(planning.get("planner_iters") or [])),
        "adaptor_total_retries": adaptor.get("total_retries"),
        "adaptor_error_count": len(adaptor_errors),
        "adaptor_reset_count": len(list(planning.get("adaptor_iters") or [])),
        "test_retries": planning.get("test_retries"),
        "testing_error_count": len(testing_errors),
        "case_result_count": len(case_results),
        "terminal_error_type": terminal_error_type,
        "terminal_error_message": terminal_error_message,
        "failing_paths": failing_paths,
        "failing_step_ids": failing_step_ids,
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    total_runs = len(records)
    completed_runs = sum(1 for record in records if record.get("workflow_completed"))
    unique_input_ids = sorted({record["input_id"] for record in records if record.get("input_id")})
    solved_input_ids = sorted({
        record["input_id"]
        for record in records
        if record.get("input_id") and record.get("workflow_completed")
    })

    error_type_counts: dict[str, int] = {}
    failing_path_counts: dict[str, int] = {}
    tool_usage_counts: dict[str, int] = {}
    for record in records:
        error_type = record.get("terminal_error_type")
        if error_type:
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
        for failing_path in record.get("failing_paths", []) or []:
            failing_path_counts[failing_path] = failing_path_counts.get(failing_path, 0) + 1
        for tool_name in record.get("tools_used", []) or []:
            tool_usage_counts[tool_name] = tool_usage_counts.get(tool_name, 0) + 1

    per_input_id: dict[str, dict[str, Any]] = {}
    for input_id in unique_input_ids:
        input_records = [record for record in records if record.get("input_id") == input_id]
        latest_record = sorted(
            input_records,
            key=lambda record: ((record.get("saved_at") or ""), (record.get("workflow_id") or "")),
            reverse=True,
        )[0]
        per_input_id[input_id] = {
            "runs": len(input_records),
            "completed_runs": sum(1 for record in input_records if record.get("workflow_completed")),
            "completed_once": any(record.get("workflow_completed") for record in input_records),
            "latest_saved_at": latest_record.get("saved_at"),
            "latest_workflow_id": latest_record.get("workflow_id"),
            "latest_completed": latest_record.get("workflow_completed"),
            "latest_terminal_error_type": latest_record.get("terminal_error_type"),
        }

    summary = {
        "runs": total_runs,
        "completed_runs": completed_runs,
        "completion_rate": 0.0 if total_runs == 0 else completed_runs / total_runs,
        "unique_input_ids": len(unique_input_ids),
        "solved_input_ids": len(solved_input_ids),
        "solved_input_rate": 0.0 if not unique_input_ids else len(solved_input_ids) / len(unique_input_ids),
        "error_type_counts": error_type_counts,
        "failing_path_counts": failing_path_counts,
        "tool_usage_counts": tool_usage_counts,
    }

    return {
        "summary": summary,
        "per_input_id": per_input_id,
        "records": records,
    }


def analyze_saved_workflows(
    storage_path: str | Path,
    input_ids: list[str] | None = None,
    completed_only: bool = False,
    latest_only: bool = False,
) -> dict[str, Any]:
    workflows = load_saved_workflows(
        storage_path=storage_path,
        input_ids=input_ids,
        completed_only=completed_only,
        latest_only=latest_only,
    )
    records = [workflow_to_record(workflow_object) for workflow_object in workflows]
    return summarize_records(records)


def to_json(data: dict[str, Any], **kwargs) -> str:
    return json.dumps(data, indent=2, default=str, **kwargs)


def to_dataframes(data: dict[str, Any]):
    import pandas as pd

    records_df = pd.DataFrame(data.get("records", []))
    per_input_df = pd.DataFrame.from_dict(data.get("per_input_id", {}), orient="index")
    per_input_df.index.name = "input_id"
    summary_df = pd.DataFrame([data.get("summary", {})])
    return {
        "records": records_df,
        "per_input_id": per_input_df,
        "summary": summary_df,
    }
