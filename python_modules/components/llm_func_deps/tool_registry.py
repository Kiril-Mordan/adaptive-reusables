"""
Runtime tool loading helpers for llm_function.
"""

import attrs
import attrsx
import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, Field, SkipValidation
from workflow_auto_assembler import LlmFunctionItem, make_uid

from llm_function_tools import (
    ToolSpec,
    load_tools_from_module,
    load_tools_from_python_file,
    tool_from_callable,
)


class ResolvedTool(BaseModel):
    """
    Runtime-ready tool definition with provenance metadata.
    """

    tool_spec: ToolSpec = Field(description="Normalized tool definition.")
    func: SkipValidation[Callable[..., Any]] = Field(description="Runtime callable for the tool.")
    source_type: str = Field(description="Source kind, for example file or module.")
    location_type: str = Field(description="Location kind, for example local or external.")
    package_name: Optional[str] = Field(default=None, description="Optional package name.")
    package_version: Optional[str] = Field(default=None, description="Optional resolved package version.")
    module_name: Optional[str] = Field(default=None, description="Python module that defined the tool.")
    file_path: Optional[str] = Field(default=None, description="Local file path when the tool was loaded from a file.")
    origin_ref: Optional[str] = Field(default=None, description="Original source reference used to load the tool.")
    metadata: dict = Field(default_factory=dict, description="Additional runtime metadata.")

    model_config = {
        "arbitrary_types_allowed": True,
    }


@attrsx.define
class InMemoryToolSource:
    """
    Resolve tools directly from callables, ToolSpec objects, or ResolvedTool objects.
    """

    tools: Sequence[Union[Callable[..., Any], ToolSpec, ResolvedTool]] = attrs.field()
    location_type: str = attrs.field(default="local")
    package_name: Optional[str] = attrs.field(default=None)
    package_version: Optional[str] = attrs.field(default=None)
    origin_ref: Optional[str] = attrs.field(default=None)

    def __attrs_post_init__(self):
        self.tools = list(self.tools)

    def load_tools(self) -> List[ResolvedTool]:
        """
        Resolve in-memory tools into runtime tool records.
        """

        resolved_tools: List[ResolvedTool] = []
        for item in self.tools:
            if isinstance(item, ResolvedTool):
                resolved_tools.append(item)
                continue

            tool_spec = item if isinstance(item, ToolSpec) else tool_from_callable(item)
            resolved_tools.append(
                ResolvedTool(
                    tool_spec=tool_spec,
                    func=tool_spec.func,
                    source_type="memory",
                    location_type=self.location_type,
                    package_name=self.package_name,
                    package_version=self.package_version,
                    module_name=getattr(tool_spec.func, "__module__", None),
                    origin_ref=self.origin_ref,
                )
            )

        return resolved_tools


@attrsx.define
class PythonModuleToolSource:
    """
    Resolve tools from an importable Python module.
    """

    module_name: str = attrs.field()
    include_plain_typed: bool = attrs.field(default=False)
    location_type: str = attrs.field(default="local")
    package_name: Optional[str] = attrs.field(default=None)
    package_version: Optional[str] = attrs.field(default=None)

    def load_tools(self) -> List[ResolvedTool]:
        """
        Import module and resolve tools declared inside it.
        """

        resolved_tools: List[ResolvedTool] = []
        for tool_spec in load_tools_from_module(
            self.module_name,
            include_plain_typed=self.include_plain_typed,
        ):
            resolved_tools.append(
                ResolvedTool(
                    tool_spec=tool_spec,
                    func=tool_spec.func,
                    source_type="module",
                    location_type=self.location_type,
                    package_name=self.package_name,
                    package_version=self.package_version,
                    module_name=self.module_name,
                    origin_ref=self.module_name,
                )
            )

        return resolved_tools


@attrsx.define
class PythonFileToolSource:
    """
    Resolve tools from a standalone Python file path.
    """

    file_path: str = attrs.field()
    include_plain_typed: bool = attrs.field(default=False)
    location_type: str = attrs.field(default="local")
    package_name: Optional[str] = attrs.field(default=None)
    package_version: Optional[str] = attrs.field(default=None)
    module_name: Optional[str] = attrs.field(default=None)

    def load_tools(self) -> List[ResolvedTool]:
        """
        Import file and resolve tools declared inside it.
        """

        resolved_path = str(Path(self.file_path).expanduser().resolve())
        resolved_tools: List[ResolvedTool] = []
        for tool_spec in load_tools_from_python_file(
            resolved_path,
            include_plain_typed=self.include_plain_typed,
            module_name=self.module_name,
        ):
            resolved_tools.append(
                ResolvedTool(
                    tool_spec=tool_spec,
                    func=tool_spec.func,
                    source_type="file",
                    location_type=self.location_type,
                    package_name=self.package_name,
                    package_version=self.package_version,
                    module_name=getattr(tool_spec.func, "__module__", self.module_name),
                    file_path=resolved_path,
                    origin_ref=resolved_path,
                )
            )

        return resolved_tools


@attrsx.define
class ToolRegistry:
    """
    Aggregate tools from one or more sources and expose WAA-compatible tool lists.
    """

    sources: Sequence[object] = attrs.field()
    _resolved_tools: Optional[List[ResolvedTool]] = attrs.field(default=None)

    def __attrs_post_init__(self):
        self.sources = list(self.sources)

    def load_tools(self, reload: bool = False) -> List[ResolvedTool]:
        """
        Resolve all configured sources into runtime tools.
        """

        if self._resolved_tools is not None and not reload:
            return list(self._resolved_tools)

        resolved_tools: List[ResolvedTool] = []
        seen_keys = set()

        for source in self.sources:
            for resolved_tool in source.load_tools():
                dedupe_key = (
                    resolved_tool.tool_spec.name,
                    resolved_tool.module_name,
                    resolved_tool.file_path,
                    resolved_tool.package_name,
                    resolved_tool.package_version,
                )
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                resolved_tools.append(resolved_tool)

        self._resolved_tools = resolved_tools
        return list(self._resolved_tools)

    @staticmethod
    def _safe_source_code(func: Callable[..., Any]) -> str:
        """
        Best-effort source capture for stable tool hashing.
        """

        try:
            return inspect.getsource(func)
        except (OSError, TypeError):
            return getattr(func, "__qualname__", getattr(func, "__name__", ""))

    def build_available_tools(self) -> Dict[str, Any]:
        """
        Convert resolved tools into WorkflowAutoAssembler-compatible structures.
        """

        available_functions: List[LlmFunctionItem] = []
        available_callables: Dict[str, Callable[..., Any]] = {}

        for resolved_tool in self.load_tools():
            llm_func_item = {
                "name": resolved_tool.tool_spec.name,
                "description": resolved_tool.tool_spec.description,
                "input_schema_json": resolved_tool.tool_spec.input_model.model_json_schema(),
                "output_schema_json": resolved_tool.tool_spec.output_model.model_json_schema(),
                "code": self._safe_source_code(resolved_tool.func),
            }
            func_id = make_uid(d=llm_func_item)

            available_functions.append(
                LlmFunctionItem(
                    func_id=func_id,
                    name=llm_func_item["name"],
                    description=llm_func_item["description"],
                    input_schema_json=llm_func_item["input_schema_json"],
                    output_schema_json=llm_func_item["output_schema_json"],
                )
            )
            available_callables[func_id] = resolved_tool.func

        return {
            "available_functions": available_functions,
            "available_callables": available_callables,
            "resolved_tools": self.load_tools(),
        }
