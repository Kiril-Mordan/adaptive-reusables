from pydantic import BaseModel

from python_modules.components.input_collector import InputCollector
from python_modules.components.output_comparer import OutputComparer
from python_modules.components.workflow_runner import WorkflowRunner
from python_modules.components.wa_general_models import LlmFunctionItemInput, create_avc_items, WorkflowErrorType, WorkflowError


class AddInput(BaseModel):
    x: int


class AddOutput(BaseModel):
    y: int


class DoubleInput(BaseModel):
    y: int


class DoubleOutput(BaseModel):
    z: int


class FinalOutput(BaseModel):
    result: int


def add_one(inputs: AddInput) -> AddOutput:
    return AddOutput(y=inputs.x + 1)


def double(inputs: DoubleInput) -> DoubleOutput:
    return DoubleOutput(z=inputs.y * 2)


def test_workflow_runner_smoke():
    avc = create_avc_items([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput),
        LlmFunctionItemInput(func=double, input_model=DoubleInput, output_model=DoubleOutput),
    ])
    available_functions = avc["available_functions"]
    available_callables = avc["available_callables"]

    func_id_by_name = {f.name: f.func_id for f in available_functions}

    workflow = [
        {"id": 1, "name": "add_one", "func_id": func_id_by_name["add_one"], "args": {"x": "0.output.x"}},
        {"id": 2, "name": "double", "func_id": func_id_by_name["double"], "args": {"y": "1.output.y"}},
        {"id": 3, "name": "output_model", "args": {"result": "2.output.z"}},
    ]

    runner = WorkflowRunner(
        workflow_error_types=WorkflowErrorType,
        workflow_error=WorkflowError,
        available_functions=available_functions,
        available_callables=available_callables,
        output_comparer_class=OutputComparer,
    )

    result = runner.run_workflow(
        workflow=workflow,
        inputs=AddInput(x=3),
        output_model=FinalOutput,
    )

    assert result.error is None
    assert result.outputs["3"] == FinalOutput(result=8)


def test_input_collector_fix_literal_values():
    planned = [
        {"id": 1, "name": "step", "args": {"x": "literal", "y": "source: 1.output.y"}}
    ]
    adapted = [
        {"id": 1, "name": "step", "args": {"x": "source: 9.output.z", "y": "source: 1.output.y"}}
    ]

    collector = InputCollector()
    fixed = collector.fix_literal_values(planned_workflow=planned, adapted_workflow=adapted)

    assert fixed[0]["args"]["x"] == "literal"
    assert fixed[0]["args"]["y"] == "source: 1.output.y"


def test_output_comparer_diff():
    class A(BaseModel):
        val: int

    expected = A(val=1)
    actual = A(val=2)

    comparer = OutputComparer()
    diffs = comparer.compare_models(expected=expected, actual=actual)

    assert len(diffs) == 1
    assert diffs[0]["path"] == "val"
    assert diffs[0]["diff_type"] == "value_mismatch"
