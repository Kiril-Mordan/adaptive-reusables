"""
`llm_function` helps you build reusable LLM functions with normal Python signatures.

You define a function with Pydantic input and output models, describe what it should do
in the docstring, and provide a set of available tools. At runtime, `llm_function`
uses [`workflow_auto_assembler`](https://pypi.org/project/workflow-auto-assembler/) to
assemble and execute a workflow that satisfies that typed function contract.

The result is an LLM-backed function that can be reused like any other Python function,
while still being grounded in explicit tools, schemas, and config.

Tool definition and discovery live in
[`llm_function_tools`](https://pypi.org/project/llm-function-tools/).
"""

import asyncio
import attrs
import attrsx
import inspect
import threading
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, get_type_hints

from pydantic import BaseModel
from workflow_auto_assembler import WorkflowAutoAssembler
from .components.llm_func_deps.llm_function_config import LlmFunctionConfig, LlmRuntimeConfig
from .components.llm_func_deps.tool_registry import InMemoryToolSource, ToolRegistry

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "Llm function is a decorator that uses llm to assemble reusable workflows from available tools to match input and output models.",
    "url" : 'https://kiril-mordan.github.io/adaptive-reusables/llm-function/',
}


@attrsx.define
class LlmFunction:
    available_functions: Optional[List[Any]] = attrs.field(default=None)
    available_callables: Optional[Dict[str, Callable[..., Any]]] = attrs.field(default=None)
    tool_registry: Optional[ToolRegistry] = attrs.field(default=None)
    tool_sources: Optional[List[object]] = attrs.field(default=None)
    config: Optional[LlmFunctionConfig] = attrs.field(default=None)
    llm_handler_params: Optional[dict] = attrs.field(default=None)
    storage_path: Optional[str] = attrs.field(default=None)
    force_replan: bool = attrs.field(default=False)
    max_retry: Optional[int] = attrs.field(default=None)
    reset_loops: Optional[int] = attrs.field(default=None)
    compare_params: Optional[dict] = attrs.field(default=None)
    test_params: Optional[list] = attrs.field(default=None)
    resolved_tools: Optional[Dict[str, Any]] = attrs.field(default=None, init=False)

    def __attrs_post_init__(self):
        self._apply_config_defaults()

        if self.llm_handler_params is None:
            raise ValueError("llm_handler_params is required either directly or via config.")

        self.resolved_tools = self._resolve_available_tools()

    def _apply_config_defaults(self):
        if self.config is None:
            return

        if self.llm_handler_params is None:
            self.llm_handler_params = self.config.runtime.llm_handler_params
        if self.storage_path is None:
            self.storage_path = self.config.runtime.storage_path
        if self.force_replan is False:
            self.force_replan = self.config.runtime.force_replan
        if self.max_retry is None:
            self.max_retry = self.config.runtime.max_retry
        if self.reset_loops is None:
            self.reset_loops = self.config.runtime.reset_loops
        if self.compare_params is None:
            self.compare_params = self.config.runtime.compare_params
        if self.test_params is None:
            self.test_params = self.config.runtime.test_params
        if self.tool_registry is None:
            self.tool_registry = self.config.tool_registry
        if self.tool_sources is None and self.config.tool_sources is not None:
            self.tool_sources = list(self.config.tool_sources)

    def _normalize_task_description(self, func: Callable[..., Any]) -> str:
        task_description = inspect.cleandoc(func.__doc__ or "").strip()
        if not task_description:
            raise ValueError("Decorated function must define a docstring to use as task_description.")

        return task_description

    def _extract_io_models(self, func: Callable[..., Any]) -> tuple[Type[BaseModel], Type[BaseModel], str]:
        signature = inspect.signature(func)
        params = list(signature.parameters.values())
        if len(params) != 1:
            raise ValueError("Decorated function must accept exactly one parameter annotated with a BaseModel subclass.")

        input_param = params[0]
        hints = get_type_hints(func)
        input_model = hints.get(input_param.name)
        output_model = hints.get("return")

        if not inspect.isclass(input_model) or not issubclass(input_model, BaseModel):
            raise TypeError("Decorated function input annotation must be a Pydantic BaseModel subclass.")

        if not inspect.isclass(output_model) or not issubclass(output_model, BaseModel):
            raise TypeError("Decorated function return annotation must be a Pydantic BaseModel subclass.")

        return input_model, output_model, input_param.name

    def _coerce_run_inputs(self, input_model: Type[BaseModel], run_inputs: Any) -> BaseModel:
        if isinstance(run_inputs, input_model):
            return run_inputs

        if hasattr(input_model, "model_validate"):
            return input_model.model_validate(run_inputs)

        return input_model.parse_obj(run_inputs)

    def _run_coro_blocking(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result: Dict[str, Any] = {}
        error: Dict[str, BaseException] = {}

        def _thread_main():
            try:
                result["value"] = asyncio.run(coro)
            except BaseException as exc:  # pragma: no cover
                error["value"] = exc

        thread = threading.Thread(target=_thread_main, daemon=True)
        thread.start()
        thread.join()

        if "value" in error:
            raise error["value"]

        return result["value"]

    def _resolve_available_tools(self) -> Dict[str, Any]:
        if self.tool_registry is not None and self.tool_sources is not None:
            raise ValueError("Use either tool_registry or tool_sources, not both.")

        if self.tool_registry is not None:
            return self.tool_registry.build_available_tools()

        if self.tool_sources is not None:
            return ToolRegistry(sources=self.tool_sources).build_available_tools()

        if self.available_functions is None or self.available_callables is None:
            raise ValueError(
                "Provide either available_functions and available_callables, or tool_registry/tool_sources."
            )

        return {
            "available_functions": self.available_functions,
            "available_callables": self.available_callables,
            "resolved_tools": None,
        }

    def as_decorator(self):
        def decorator(func: Callable[..., Any]):
            signature = inspect.signature(func)
            task_description = self._normalize_task_description(func)
            input_model, output_model, input_name = self._extract_io_models(func)

            async def _invoke_async(run_inputs: Any):
                wa = WorkflowAutoAssembler(
                    available_functions=self.resolved_tools["available_functions"],
                    available_callables=self.resolved_tools["available_callables"],
                    storage_path=self.storage_path,
                    llm_handler_params=self.llm_handler_params,
                )

                return await wa.actualize_workflow(
                    task_description=task_description,
                    force_replan=self.force_replan,
                    run_inputs=self._coerce_run_inputs(input_model=input_model, run_inputs=run_inputs),
                    test_params=self.test_params,
                    compare_params=self.compare_params,
                    input_model=input_model,
                    output_model=output_model,
                    max_retry=self.max_retry,
                    reset_loops=self.reset_loops,
                )

            if inspect.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    bound = signature.bind(*args, **kwargs)
                    return await _invoke_async(bound.arguments[input_name])

                async_wrapper.input_model = input_model
                async_wrapper.output_model = output_model
                async_wrapper.task_description = task_description
                async_wrapper.ainvoke = _invoke_async
                async_wrapper.resolved_tools = self.resolved_tools["resolved_tools"]
                return async_wrapper

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                bound = signature.bind(*args, **kwargs)
                return self._run_coro_blocking(_invoke_async(bound.arguments[input_name]))

            sync_wrapper.input_model = input_model
            sync_wrapper.output_model = output_model
            sync_wrapper.task_description = task_description
            sync_wrapper.ainvoke = _invoke_async
            sync_wrapper.resolved_tools = self.resolved_tools["resolved_tools"]
            return sync_wrapper

        return decorator


def llm_function(
    *,
    available_functions: Optional[List[Any]] = None,
    available_callables: Optional[Dict[str, Callable[..., Any]]] = None,
    tool_registry: Optional[ToolRegistry] = None,
    tool_sources: Optional[List[object]] = None,
    config: Optional[LlmFunctionConfig] = None,
    llm_handler_params: Optional[dict] = None,
    storage_path: Optional[str] = None,
    force_replan: bool = False,
    max_retry: Optional[int] = None,
    reset_loops: Optional[int] = None,
    compare_params: Optional[dict] = None,
    test_params: Optional[list] = None,
):
    """
    Decorate a typed function and route its calls through WorkflowAutoAssembler.
    """
    return LlmFunction(
        available_functions=available_functions,
        available_callables=available_callables,
        tool_registry=tool_registry,
        tool_sources=tool_sources,
        config=config,
        llm_handler_params=llm_handler_params,
        storage_path=storage_path,
        force_replan=force_replan,
        max_retry=max_retry,
        reset_loops=reset_loops,
        compare_params=compare_params,
        test_params=test_params,
    ).as_decorator()
