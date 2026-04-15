import pytest
import sys
import types
from pydantic import BaseModel, Field

workflow_auto_assembler_stub = types.ModuleType("workflow_auto_assembler")


class StubWorkflowError(BaseModel):
    error_message: str | None = None


class StubWorkflowAutoAssembler:
    def __init__(self, **kwargs):
        pass

    async def actualize_workflow(self, **kwargs):
        return kwargs


class StubLlmFunctionItem(BaseModel):
    func_id: str
    name: str
    description: str
    input_schema_json: dict
    output_schema_json: dict


def stub_make_uid(d):
    return "stub-func-id"


workflow_auto_assembler_stub.WorkflowAutoAssembler = StubWorkflowAutoAssembler
workflow_auto_assembler_stub.WorkflowError = StubWorkflowError
workflow_auto_assembler_stub.LlmFunctionItem = StubLlmFunctionItem
workflow_auto_assembler_stub.make_uid = stub_make_uid
sys.modules.setdefault("workflow_auto_assembler", workflow_auto_assembler_stub)

import python_modules.llm_function_tools as llm_function_tools_module

sys.modules.setdefault("llm_function_tools", llm_function_tools_module)

import python_modules.llm_function as llm_function_module
from python_modules.llm_function import LlmFunctionRuntime, llm_function


class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city.")


class WfOutputs(BaseModel):
    city: str
    message: str


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_llm_function_sync_wrapper_uses_actualize_workflow(monkeypatch):
    calls = {}
    tool_callable = object()

    class FakeWorkflowAutoAssembler:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        async def actualize_workflow(self, **kwargs):
            calls["actualize"] = kwargs
            return WfOutputs(city=kwargs["run_inputs"].city, message="sent")

    monkeypatch.setattr(llm_function_module, "WorkflowAutoAssembler", FakeWorkflowAutoAssembler)

    @llm_function(
        available_functions=["func"],
        available_callables={"func": tool_callable},
        llm_handler_params={"llm_h_type": "ollama", "llm_h_params": {"model_name": "gpt-oss:20b"}},
        storage_path="/tmp/llm-function-test",
        force_replan=True,
    )
    def get_and_send_birds_info(input: WfInputs) -> WfOutputs:
        """
        Query database to find information on birds and get latest weather for the city, then send an email there.
        """

    output = get_and_send_birds_info(WfInputs(city="London"))

    assert output == WfOutputs(city="London", message="sent")
    assert calls["init"]["available_functions"] == ["func"]
    assert calls["init"]["available_callables"] == {"func": tool_callable}
    assert calls["init"]["storage_path"] == "/tmp/llm-function-test"
    assert calls["init"]["llm_handler_params"] == {
        "llm_h_type": "ollama",
        "llm_h_params": {"model_name": "gpt-oss:20b"},
    }
    assert calls["actualize"]["task_description"] == (
        "Query database to find information on birds and get latest weather for the city, then send an email there."
    )
    assert calls["actualize"]["force_replan"] is True
    assert calls["actualize"]["run_inputs"] == WfInputs(city="London")
    assert calls["actualize"]["input_model"] is WfInputs
    assert calls["actualize"]["output_model"] is WfOutputs


@pytest.mark.anyio
async def test_llm_function_async_wrapper_supports_dict_inputs(monkeypatch):
    calls = {}

    class FakeWorkflowAutoAssembler:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        async def actualize_workflow(self, **kwargs):
            calls["actualize"] = kwargs
            return WfOutputs(city=kwargs["run_inputs"].city, message="ok")

    monkeypatch.setattr(llm_function_module, "WorkflowAutoAssembler", FakeWorkflowAutoAssembler)

    @llm_function(
        available_functions=[],
        available_callables={},
        llm_handler_params={"llm_h_type": "ollama", "llm_h_params": {"model_name": "gpt-oss:20b"}},
    )
    async def get_birds_info(input: WfInputs) -> WfOutputs:
        """
        Fetch birds information and weather for a city.
        """

    output = await get_birds_info({"city": "Berlin"})

    assert output == WfOutputs(city="Berlin", message="ok")
    assert calls["actualize"]["run_inputs"] == WfInputs(city="Berlin")
    assert get_birds_info.input_model is WfInputs
    assert get_birds_info.output_model is WfOutputs
    assert get_birds_info.task_description == "Fetch birds information and weather for a city."


def test_llm_function_requires_docstring():
    with pytest.raises(ValueError, match="docstring"):

        @llm_function(
            available_functions=[],
            available_callables={},
            llm_handler_params={"llm_h_type": "ollama", "llm_h_params": {"model_name": "gpt-oss:20b"}},
        )
        def undocumented(input: WfInputs) -> WfOutputs:
            pass


def test_llm_function_runtime_reuses_waa_instance(monkeypatch):
    calls = {"init": 0, "actualize": 0}

    class FakeWaa:
        def __init__(self, **kwargs):
            calls["init"] += 1
            self.init_kwargs = kwargs

        async def actualize_workflow(self, **kwargs):
            calls["actualize"] += 1
            return WfOutputs(city=kwargs["run_inputs"].city, message="runtime")

    def fake_initialize_waa_h(self, uparams=None):
        self.waa_h = FakeWaa(**(uparams or {}))

    monkeypatch.setattr(llm_function_module.LlmFunctionRuntime, "_initialize_waa_h", fake_initialize_waa_h)

    runtime = LlmFunctionRuntime(
        available_functions=["func"],
        available_callables={"func": object()},
        llm_handler_params={"llm_h_type": "ollama", "llm_h_params": {"model_name": "gpt-oss:20b"}},
        storage_path="/tmp/llm-function-runtime-test",
    )

    @llm_function(runtime=runtime)
    def first_func(input: WfInputs) -> WfOutputs:
        """
        First runtime-backed function.
        """

    @llm_function(runtime=runtime)
    def second_func(input: WfInputs) -> WfOutputs:
        """
        Second runtime-backed function.
        """

    first = first_func(WfInputs(city="London"))
    second = second_func(WfInputs(city="Berlin"))

    assert first == WfOutputs(city="London", message="runtime")
    assert second == WfOutputs(city="Berlin", message="runtime")
    assert calls["init"] == 1
    assert calls["actualize"] == 2


def test_llm_function_runtime_conflicts_with_direct_tool_inputs(monkeypatch):
    def fake_initialize_waa_h(self, uparams=None):
        self.waa_h = object()

    monkeypatch.setattr(llm_function_module.LlmFunctionRuntime, "_initialize_waa_h", fake_initialize_waa_h)

    runtime = LlmFunctionRuntime(
        available_functions=["func"],
        available_callables={"func": object()},
        llm_handler_params={"llm_h_type": "ollama", "llm_h_params": {"model_name": "gpt-oss:20b"}},
    )

    with pytest.raises(ValueError, match="runtime"):

        @llm_function(runtime=runtime, available_functions=["other"], available_callables={"other": object()})
        def conflicting(input: WfInputs) -> WfOutputs:
            """
            Conflicting runtime-backed function.
            """
