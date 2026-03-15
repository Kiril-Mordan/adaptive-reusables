import argparse
import asyncio
import json
import time
from pathlib import Path
from types import ModuleType
import importlib.util

import logging
try:
    from shouterlog import Shouter
    _SHOUTER_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    Shouter = None
    _SHOUTER_AVAILABLE = False

from workflow_auto_assembler import (
    WorkflowAutoAssembler,
    create_avc_items,
    LlmFunctionItemInput,
    LlmHandler,
    WorkflowCheck,
    WorkflowPlanner,
    WorkflowAdaptor,
    WorkflowRunner,
    InputCollector,
    OutputComparer,
)


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE.parent / "test_results"
DEFAULT_RESULTS = RESULTS_DIR / "benchmark_results.json"
DEFAULT_SUMMARY = RESULTS_DIR / "benchmark_summary.json"


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
    params = []
    for inp, out in zip(inputs, expected):
        params.append({"inputs": inp, "outputs": out})
    return params


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

    per_task = {"overall": overall, **per_task}

    summary = {
        "per_task": per_task,
    }
    return summary


def _serialize_model(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def _serialize_test_params(test_params):
    if not test_params:
        return []
    out = []
    for item in test_params:
        out.append(
            {
                "inputs": _serialize_model(item.get("inputs")),
                "outputs": _serialize_model(item.get("outputs")),
            }
        )
    return out


async def _run(args):
    functions_module = _load_module(HERE / "functions.py", "waa_examples_functions")
    tests_module = _load_module(HERE / "test_examples.py", "waa_examples_tests")

    available_tools = _collect_tools(functions_module)

    task_specs = tests_module.task_specs
    task_tests = tests_module.task_tests

    task_ids = sorted(task_specs.keys())
    if args.task:
        task_ids = [tid for tid in task_ids if tid in set(args.task)]
    if args.limit:
        task_ids = task_ids[: args.limit]

    results = []
    if args.append and args.results_path.exists():
        try:
            existing = json.loads(args.results_path.read_text())
            if isinstance(existing, list):
                results.extend(existing)
        except Exception:
            pass

    async def _run_task(task_id: str, rep: int):
        spec = task_specs[task_id]
        test_params = _build_test_params(task_tests, task_id)
        start = time.time()
        ts = time.strftime("%Y%m%d_%H%M%S")
        try:
            logger = None
            if args.use_shouter:
                if not _SHOUTER_AVAILABLE:
                    raise RuntimeError("shouterlog is required for --use-shouter")
                logger = Shouter(
                    supported_classes=(
                        WorkflowAutoAssembler,
                        LlmHandler,
                        WorkflowCheck,
                        WorkflowPlanner,
                        WorkflowAdaptor,
                        WorkflowRunner,
                        InputCollector,
                        OutputComparer,
                    ),
                    logger_name="WorkflowAutoAssembler",
                    loggerLvl=args.shouter_level,
                )
            wa = WorkflowAutoAssembler(
                logger=logger,
                available_functions=available_tools["available_functions"],
                available_callables=available_tools["available_callables"],
                llm_handler_params={
                    "llm_h_type": args.llm_type,
                    "llm_h_params": {
                        "connection_string": args.connection_string,
                        "model_name": args.model_name,
                    },
                },
            )

            wf_obj = await wa.plan_workflow(
                task_description=spec["description"],
                input_model=spec["input_model"],
                output_model=spec["output_model"],
                test_params=test_params,
            )
            error = None
        except Exception as e:
            wf_obj = None
            error = str(e)
            wa = None
        duration = time.time() - start

        result = _summarize_task(task_id, wf_obj, error, duration)
        result["repeat_index"] = rep
        log_records = None
        if wa is not None and getattr(wa, "logger", None) is not None:
            log_records = getattr(wa.logger, "log_records", None)

        reset_counts = {}
        if wf_obj is not None:
            testing_errors = getattr(wf_obj.planning, "testing_errors", []) if getattr(wf_obj, "planning", None) else []
            for err in testing_errors or []:
                et = getattr(err, "error_type", None)
                if et is None:
                    continue
                et_key = getattr(et, "value", str(et))
                reset_counts[et_key] = reset_counts.get(et_key, 0) + 1

        json_payload = {
            "task_id": task_id,
            "repeat_index": rep,
            "workflow_completed": getattr(wf_obj, "workflow_completed", None) if wf_obj is not None else None,
            "error": error,
            "workflow": getattr(wf_obj, "workflow", None) if wf_obj is not None else None,
            "init_check": _serialize_model(getattr(wf_obj, "init_check", None)) if wf_obj is not None else None,
            "test_params": _serialize_test_params(test_params),
            "reset_counts": reset_counts,
            "log_records": log_records,
            "timestamp": ts,
        }
        return result, json_payload

    coros = [
        _run_task(task_id, rep)
        for task_id in task_ids
        for rep in range(args.repeats)
    ]

    run_payloads = []
    if coros:
        gathered = await asyncio.gather(*coros)
        for result, payload in gathered:
            results.append(result)
            run_payloads.append(payload)

    summary = _aggregate(results)

    args.results_path.parent.mkdir(parents=True, exist_ok=True)
    args.results_path.write_text(json.dumps(results, indent=2, default=str) + "\n")
    args.summary_path.write_text(json.dumps(summary, indent=2, default=str) + "\n")

    if args.save_runs_dir:
        args.save_runs_dir.mkdir(parents=True, exist_ok=True)
        for payload in run_payloads:
            task_id = payload.get("task_id", "task")
            ts = payload.get("timestamp", time.strftime("%Y%m%d_%H%M%S"))
            rep = payload.get("repeat_index", 0)
            json_name = f"{task_id}_{ts}_r{rep}.json"
            (args.save_runs_dir / json_name).write_text(
                json.dumps(payload, indent=2, default=str) + "\n"
            )

    print(f"Wrote {args.results_path}")
    print(f"Wrote {args.summary_path}")


def main():
    parser = argparse.ArgumentParser(description="Run WAA benchmark tasks and save compact metrics.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tasks (0 = all).")
    parser.add_argument("--task", action="append", help="Run only a specific task id (can be repeated).")
    parser.add_argument("--repeats", type=int, default=1, help="Number of repeats per task.")
    parser.add_argument("--append", action="store_true", help="Append results to existing output file.")
    parser.add_argument(
        "--save-runs-dir",
        type=Path,
        default=None,
        help="Optional directory to save per-run JSON (workflow, test cases, log records).",
    )
    parser.add_argument(
        "--use-shouter",
        action="store_true",
        help="Enable Shouter logger for debugging (requires shouterlog).",
    )
    parser.add_argument(
        "--shouter-level",
        type=int,
        default=logging.INFO,
        help="Shouter logger level (numeric, e.g. 10=DEBUG, 20=INFO).",
    )
    parser.add_argument("--results-path", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--llm-type", default="ollama")
    parser.add_argument("--connection-string", default="http://localhost:11434")
    parser.add_argument("--model-name", default="gpt-oss:20b")
    args = parser.parse_args()

    if args.limit == 0:
        args.limit = None

    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
