import argparse
import asyncio
import json
import time
from pathlib import Path
from types import ModuleType
import importlib.util

from workflow_auto_assembler import (
    WorkflowAutoAssembler,
    create_avc_items,
    LlmFunctionItemInput,
)


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
RESULTS_DIR = HERE.parent / "test_results"
DEFAULT_RESULTS = RESULTS_DIR / "math_benchmark_results.json"
DEFAULT_SUMMARY = RESULTS_DIR / "math_benchmark_summary.json"
DEFAULT_STORAGE = PROJECT_ROOT / "temp" / "math_workflows"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _collect_tools(functions_module: ModuleType):
    funcs = []
    for value in functions_module.__dict__.values():
        if callable(value) and getattr(value, "__annotations__", None):
            ann = value.__annotations__
            if "inputs" in ann and "return" in ann:
                funcs.append(value)

    if not funcs:
        raise ValueError("No tool functions found with `inputs` and `return` annotations.")

    return create_avc_items([LlmFunctionItemInput(func=f) for f in funcs])


def _build_test_params(task_tests: dict, task_id: str):
    test_spec = task_tests.get(task_id)
    if not test_spec:
        return None
    inputs = test_spec.get("inputs") or []
    expected = test_spec.get("expected_outputs") or []
    return [
        {"inputs": inp, "outputs": out}
        for inp, out in zip(inputs, expected)
    ]


def _summarize_task(task_id: str, wf_obj, error: str | None, duration_s: float):
    summary = {
        "task_id": task_id,
        "workflow_possible": None,
        "workflow_completed": None,
        "error_type": None,
        "error_message": None,
        "test_cases_total": None,
        "test_cases_failed": None,
        "test_retries": None,
        "planner_resets": None,
        "adaptor_resets": None,
        "workflow_steps": None,
        "tools_used": None,
        "duration_s": round(duration_s, 4),
    }

    if error:
        summary["error_message"] = error
        return summary

    if wf_obj is None:
        summary["error_message"] = "No workflow object returned."
        return summary

    summary["workflow_possible"] = wf_obj.workflow_possible
    summary["workflow_completed"] = wf_obj.workflow_completed
    summary["test_retries"] = wf_obj.planning.test_retries
    summary["planner_resets"] = len(wf_obj.planning.planner_iters or [])
    summary["adaptor_resets"] = len(wf_obj.planning.adaptor_iters or [])

    if wf_obj.workflow:
        summary["workflow_steps"] = len(wf_obj.workflow)
        summary["tools_used"] = [
            step.get("name")
            for step in wf_obj.workflow
            if step.get("name") and step.get("name") != "output_model"
        ]

    tester = wf_obj.planning.tester
    if tester is not None:
        case_results = getattr(tester, "case_results", None)
        if case_results is not None:
            summary["test_cases_total"] = len(case_results)
            summary["test_cases_failed"] = len([c for c in case_results if c.error is not None])
        if getattr(tester, "error", None):
            summary["error_type"] = getattr(tester.error, "error_type", None)
            summary["error_message"] = tester.error.error_message

    return summary


def _aggregate(results: list[dict]):
    per_task = {}
    for r in results:
        tid = r.get("task_id")
        if not tid:
            continue
        bucket = per_task.setdefault(
            tid,
            {
                "runs": 0,
                "completed": 0,
                "possible": 0,
                "error_type_counts": {},
                "tool_usage_counts": {},
                "avg_test_retries": None,
                "avg_workflow_steps": None,
                "test_cases_total": 0,
                "test_cases_failed": 0,
            },
        )
        bucket["runs"] += 1
        if r.get("workflow_completed"):
            bucket["completed"] += 1
        if r.get("workflow_possible"):
            bucket["possible"] += 1
        et = r.get("error_type")
        if et is not None:
            et = getattr(et, "value", str(et))
            bucket["error_type_counts"][et] = bucket["error_type_counts"].get(et, 0) + 1
        if isinstance(r.get("test_cases_total"), int):
            bucket["test_cases_total"] += r.get("test_cases_total") or 0
            bucket["test_cases_failed"] += r.get("test_cases_failed") or 0
        for name in r.get("tools_used") or []:
            bucket["tool_usage_counts"][name] = bucket["tool_usage_counts"].get(name, 0) + 1

    for tid, bucket in per_task.items():
        task_retries = [r.get("test_retries") for r in results if r.get("task_id") == tid and isinstance(r.get("test_retries"), int)]
        task_steps = [r.get("workflow_steps") for r in results if r.get("task_id") == tid and isinstance(r.get("workflow_steps"), int)]
        bucket["avg_test_retries"] = round(sum(task_retries) / len(task_retries), 4) if task_retries else None
        bucket["avg_workflow_steps"] = round(sum(task_steps) / len(task_steps), 4) if task_steps else None
        bucket["success_rate"] = round(bucket["completed"] / bucket["runs"], 4) if bucket["runs"] else 0.0
        if bucket["test_cases_total"]:
            bucket["test_pass_rate"] = round(
                (bucket["test_cases_total"] - bucket["test_cases_failed"]) / bucket["test_cases_total"], 4
            )
        else:
            bucket["test_pass_rate"] = None

    overall = {
        "runs": len(results),
        "completed": len([r for r in results if r.get("workflow_completed")]),
        "possible": len([r for r in results if r.get("workflow_possible")]),
        "error_type_counts": {},
        "tool_usage_counts": {},
        "test_cases_total": 0,
        "test_cases_failed": 0,
    }
    retries = []
    steps = []
    for r in results:
        et = r.get("error_type")
        if et is not None:
            et = getattr(et, "value", str(et))
            overall["error_type_counts"][et] = overall["error_type_counts"].get(et, 0) + 1
        for name in r.get("tools_used") or []:
            overall["tool_usage_counts"][name] = overall["tool_usage_counts"].get(name, 0) + 1
        if isinstance(r.get("test_cases_total"), int):
            overall["test_cases_total"] += r.get("test_cases_total") or 0
            overall["test_cases_failed"] += r.get("test_cases_failed") or 0
        if isinstance(r.get("test_retries"), int):
            retries.append(r.get("test_retries"))
        if isinstance(r.get("workflow_steps"), int):
            steps.append(r.get("workflow_steps"))

    overall["avg_test_retries"] = round(sum(retries) / len(retries), 4) if retries else None
    overall["avg_workflow_steps"] = round(sum(steps) / len(steps), 4) if steps else None
    overall["success_rate"] = round(overall["completed"] / overall["runs"], 4) if overall["runs"] else 0.0
    if overall["test_cases_total"]:
        overall["test_pass_rate"] = round(
            (overall["test_cases_total"] - overall["test_cases_failed"]) / overall["test_cases_total"], 4
        )
    else:
        overall["test_pass_rate"] = None

    return {"per_task": {"overall": overall, **per_task}}


async def _run(args):
    functions_module = _load_module(HERE / "math_functions.py", "waa_math_functions")
    tests_module = _load_module(HERE / "math_test_examples.py", "waa_math_tests")

    available_tools = _collect_tools(functions_module)

    task_specs = tests_module.task_specs
    task_tests = tests_module.task_tests

    task_ids = sorted(task_specs.keys())
    if args.task:
        task_ids = [tid for tid in task_ids if tid in set(args.task)]
    if args.limit:
        task_ids = task_ids[: args.limit]

    semaphore = asyncio.Semaphore(args.concurrency)

    async def _run_single(task_id: str, repeat_idx: int):
        test_params = _build_test_params(task_tests, task_id)
        task_spec = task_specs[task_id]

        wa = WorkflowAutoAssembler(
            available_functions=available_tools["available_functions"],
            available_callables=available_tools["available_callables"],
            storage_path=str(args.storage_path),
            llm_handler_params={
                "llm_h_type": "ollama",
                "llm_h_params": {
                    "connection_string": args.connection_string,
                    "model_name": args.model_name,
                },
            },
        )

        async with semaphore:
            started = time.perf_counter()
            wf_obj = None
            error = None
            try:
                await wa.actualize_workflow(
                    task_description=task_spec["description"],
                    run_inputs=(task_tests.get(task_id) or {}).get("inputs", [None])[0],
                    input_model=task_spec["input_model"],
                    output_model=task_spec["output_model"],
                    test_params=test_params,
                    compare_params={"max_decimals": 6},
                    available_functions=available_tools["available_functions"],
                    available_callables=available_tools["available_callables"],
                    force_replan=True,
                    storage_path=str(args.storage_path),
                )
                input_id = wa.get_input_id(
                    task_description=task_spec["description"],
                    input_model=task_spec["input_model"],
                    output_model=task_spec["output_model"],
                )
                wf_obj = wa.load_latest_workflow(
                    input_id=input_id,
                    completed=False,
                    storage_path=str(args.storage_path),
                )
            except Exception as exc:
                error = str(exc)
            duration_s = time.perf_counter() - started

        summary = _summarize_task(task_id=task_id, wf_obj=wf_obj, error=error, duration_s=duration_s)
        summary["repeat_idx"] = repeat_idx
        summary["description"] = task_spec["description"]
        return summary

    jobs = [
        _run_single(task_id=task_id, repeat_idx=repeat_idx)
        for repeat_idx in range(args.repeats)
        for task_id in task_ids
    ]
    results = await asyncio.gather(*jobs)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    args.results_path.write_text(json.dumps(results, indent=2, default=str))
    args.summary_path.write_text(json.dumps(_aggregate(results), indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Run the WAA math benchmark.")
    parser.add_argument("--task", action="append", help="Specific task id(s) to run, e.g. task_12")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks.")
    parser.add_argument("--repeats", type=int, default=3, help="How many repeats per task.")
    parser.add_argument("--model-name", default="gpt-oss:20b")
    parser.add_argument("--connection-string", default="http://localhost:11434")
    parser.add_argument("--results-path", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--storage-path", type=Path, default=DEFAULT_STORAGE)
    parser.add_argument("--concurrency", type=int, default=1, help="How many benchmark jobs to run concurrently.")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
