"""
`llm_function_tools` is an extension component for
[`llm_function`](https://pypi.org/project/llm-function/).

It provides small helpers for defining tools used by reusable LLM functions, including
tools stored in standalone `.py` files.
"""

import hashlib
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, List, Optional, Type, get_type_hints

from pydantic import BaseModel, Field, SkipValidation

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "Minimal metadata and discovery helpers for typed Python tools used by llm_function runtimes.",
    "url": "https://kiril-mordan.github.io/adaptive-reusables/llm_function_tools/",
}


class ToolSpec(BaseModel):
    """
    Canonical in-memory representation of a Python tool definition.
    """

    func: SkipValidation[Callable[..., Any]]
    name: str = Field(description="Public tool name.")
    description: str = Field(default="", description="Tool description used for planning.")
    input_model: SkipValidation[Type[BaseModel]] = Field(description="Tool input model.")
    output_model: SkipValidation[Type[BaseModel]] = Field(description="Tool output model.")
    metadata: dict = Field(default_factory=dict, description="Optional tool metadata.")
    tags: List[str] = Field(default_factory=list, description="Optional free-form tags.")

    model_config = {
        "arbitrary_types_allowed": True,
    }


def _normalize_description(func: Callable[..., Any], description: Optional[str] = None) -> str:
    """
    Return cleaned description override or function docstring.
    """

    if description is not None:
        return inspect.cleandoc(description).strip()

    return inspect.cleandoc(func.__doc__ or "").strip()


def _extract_io_models(
    func: Callable[..., Any],
    input_model: Optional[Type[BaseModel]] = None,
    output_model: Optional[Type[BaseModel]] = None,
) -> tuple[Type[BaseModel], Type[BaseModel]]:
    """
    Infer tool input/output models from a typed callable.
    """

    signature = inspect.signature(func)
    params = list(signature.parameters.values())
    if len(params) != 1:
        raise ValueError("Tool function must accept exactly one parameter annotated with a BaseModel subclass.")

    input_param = params[0]
    hints = get_type_hints(func)
    input_model = input_model or hints.get(input_param.name)
    output_model = output_model or hints.get("return")

    if not inspect.isclass(input_model) or not issubclass(input_model, BaseModel):
        raise TypeError("Tool function input annotation must be a Pydantic BaseModel subclass.")

    if not inspect.isclass(output_model) or not issubclass(output_model, BaseModel):
        raise TypeError("Tool function return annotation must be a Pydantic BaseModel subclass.")

    return input_model, output_model


def tool_from_callable(
    func: Callable[..., Any],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    input_model: Optional[Type[BaseModel]] = None,
    output_model: Optional[Type[BaseModel]] = None,
    metadata: Optional[dict] = None,
    tags: Optional[List[str]] = None,
) -> ToolSpec:
    """
    Build ToolSpec from a typed Python callable.
    """

    resolved_input_model, resolved_output_model = _extract_io_models(
        func=func,
        input_model=input_model,
        output_model=output_model,
    )

    return ToolSpec(
        func=func,
        name=name or func.__name__,
        description=_normalize_description(func, description=description),
        input_model=resolved_input_model,
        output_model=resolved_output_model,
        metadata=dict(metadata or {}),
        tags=list(tags or []),
    )


def llm_tool(
    func: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    input_model: Optional[Type[BaseModel]] = None,
    output_model: Optional[Type[BaseModel]] = None,
    metadata: Optional[dict] = None,
    tags: Optional[List[str]] = None,
):
    """
    Mark a typed Python function as discoverable by llm_function-style loaders.
    """

    def decorator(inner_func: Callable[..., Any]):
        tool_spec = tool_from_callable(
            inner_func,
            name=name,
            description=description,
            input_model=input_model,
            output_model=output_model,
            metadata=metadata,
            tags=tags,
        )
        setattr(inner_func, "__llm_tool__", tool_spec)
        return inner_func

    if func is not None:
        return decorator(func)

    return decorator


def get_tool_spec(func: Callable[..., Any]) -> Optional[ToolSpec]:
    """
    Return attached ToolSpec from a decorated function when present.
    """

    return getattr(func, "__llm_tool__", None)


def is_tool_callable(func: Callable[..., Any], include_plain_typed: bool = False) -> bool:
    """
    Return True when a function is an llm tool or a valid plain typed candidate.
    """

    if get_tool_spec(func) is not None:
        return True

    if not include_plain_typed:
        return False

    try:
        _extract_io_models(func=func)
    except (TypeError, ValueError, NameError):
        return False

    return True


def discover_tools_in_module(
    module: ModuleType,
    include_plain_typed: bool = False,
) -> List[ToolSpec]:
    """
    Discover llm tools defined directly in a loaded module.
    """

    tool_specs: List[ToolSpec] = []
    for _, func in inspect.getmembers(module, inspect.isfunction):
        if getattr(func, "__module__", None) != module.__name__:
            continue

        if get_tool_spec(func) is not None:
            tool_specs.append(get_tool_spec(func))
            continue

        if include_plain_typed and is_tool_callable(func, include_plain_typed=True):
            tool_specs.append(tool_from_callable(func))

    return tool_specs


def load_tools_from_module(
    module_name: str,
    include_plain_typed: bool = False,
) -> List[ToolSpec]:
    """
    Import a Python module and discover llm tools defined inside it.
    """

    module = importlib.import_module(module_name)
    return discover_tools_in_module(
        module=module,
        include_plain_typed=include_plain_typed,
    )


def _make_file_module_name(file_path: Path) -> str:
    """
    Build a stable import name for file-based loading.
    """

    digest = hashlib.sha1(str(file_path.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"_llm_function_tools_{file_path.stem}_{digest}"


def load_tools_from_python_file(
    file_path: str,
    include_plain_typed: bool = False,
    module_name: Optional[str] = None,
) -> List[ToolSpec]:
    """
    Load a Python file from disk and discover llm tools defined inside it.
    """

    resolved_path = Path(file_path).expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Tool file does not exist: {resolved_path}")

    if resolved_path.suffix != ".py":
        raise ValueError("Tool file loader expects a .py file.")

    import_name = module_name or _make_file_module_name(resolved_path)
    spec = importlib.util.spec_from_file_location(import_name, resolved_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module spec from file: {resolved_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module
    spec.loader.exec_module(module)

    return discover_tools_in_module(
        module=module,
        include_plain_typed=include_plain_typed,
    )
