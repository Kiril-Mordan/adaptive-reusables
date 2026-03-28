import pytest
from pydantic import BaseModel

from python_modules.components.output_comparer import OutputComparer
from python_modules.components.workflow_runner import WorkflowRunner
from python_modules.components.wa_general_models import (
    LlmFunctionItemInput,
    create_avc_items,
    WorkflowErrorType,
    WorkflowError,
)


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


def _make_runner(functions):
    avc = create_avc_items(functions)
    return (
        WorkflowRunner(
            workflow_error_types=WorkflowErrorType,
            workflow_error=WorkflowError,
            available_functions=avc["available_functions"],
            available_callables=avc["available_callables"],
            output_comparer_class=OutputComparer,
        ),
        avc,
    )


def _make_add_double_workflow(available_functions):
    func_id_by_name = {f.name: f.func_id for f in available_functions}
    return [
        {"id": 1, "name": "add_one", "func_id": func_id_by_name["add_one"], "args": {"x": "0.output.x"}},
        {"id": 2, "name": "double", "func_id": func_id_by_name["double"], "args": {"y": "1.output.y"}},
        {"id": 3, "name": "output_model", "args": {"result": "2.output.z"}},
    ]


def test_resolve_func_args_nested():
    runner, _ = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput)
    ])

    outputs = {
        "1": AddOutput(y=2),
        "2": DoubleOutput(z=4),
    }
    args = {
        "x": "1.output.y",
        "nested": {"z": "2.output.z", "list": ["1.output.y", 5]},
        "literal": "hi",
    }

    resolved = runner._resolve_func_args(outputs, args)

    assert resolved["x"] == 2
    assert resolved["nested"]["z"] == 4
    assert resolved["nested"]["list"] == [2, 5]
    assert resolved["literal"] == "hi"


def test_resolve_func_args_missing_path():
    runner, _ = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput)
    ])
    outputs = {"1": AddOutput(y=2)}

    with pytest.raises(ValueError):
        runner._resolve_func_args(outputs, {"x": "9.output.nope"})


def test_output_comparer_optional_and_rounding():
    class M(BaseModel):
        opt: int | None
        val: float

    expected = M(opt=None, val=1.2345)
    actual = M(opt=None, val=1.2344)

    comparer = OutputComparer(max_decimals=3)
    diffs = comparer.compare_models(expected=expected, actual=actual)

    assert diffs == []


def test_output_comparer_ignore_fields_and_types():
    class Inner(BaseModel):
        c: int

    class Token:
        pass

    class M(BaseModel):
        a: int
        b: int
        inner: Inner
        token: Token

        model_config = {"arbitrary_types_allowed": True}

    expected = M(a=1, b=2, inner=Inner(c=3), token=Token())
    actual = M(a=1, b=999, inner=Inner(c=999), token=Token())

    comparer = OutputComparer(ignore_fields={"b", "inner.c"}, ignore_types={Token})
    diffs = comparer.compare_models(expected=expected, actual=actual)

    assert diffs == []


def test_output_comparer_missing_output_mapping_does_not_crash():
    class Expected(BaseModel):
        city: str
        message: str

    class Actual(BaseModel):
        city: str

    comparer = OutputComparer()
    workflow = [
        {"id": 1, "name": "output_model", "args": {"city": "0.output.city"}},
    ]

    diffs = comparer.compare_models(
        expected=Expected(city="London", message="Email sent to London!"),
        actual=Actual(city="London"),
        workflow=workflow,
    )

    assert len(diffs) == 1
    assert diffs[0]["path"] == "message"
    assert diffs[0]["output"] is None
    assert diffs[0]["source_step_id"] == -1


def test_workflow_runner_error_surface():
    class BoomInput(BaseModel):
        x: int

    class BoomOutput(BaseModel):
        y: int

    def boom(inputs: BoomInput) -> BoomOutput:
        raise RuntimeError("boom")

    runner, avc = _make_runner([
        LlmFunctionItemInput(func=boom, input_model=BoomInput, output_model=BoomOutput)
    ])

    workflow = [
        {"id": 1, "name": "boom", "func_id": avc["available_functions"][0].func_id, "args": {"x": "0.output.x"}},
        {"id": 2, "name": "output_model", "args": {"result": "1.output.y"}},
    ]

    result = runner.run_workflow(workflow=workflow, inputs=BoomInput(x=1), output_model=FinalOutput)

    assert result.error is not None
    assert result.error.error_type == WorkflowErrorType.RUNNER
    assert result.error.additional_info.get("ffunction") == "boom"


def test_runner_missing_function_in_available_functions():
    runner, avc = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput),
    ])

    workflow = [
        {"id": 1, "name": "unknown", "func_id": "missing-func-id", "args": {"x": "0.output.x"}},
        {"id": 2, "name": "output_model", "args": {"result": "1.output.y"}},
    ]

    result = runner.run_workflow(
        workflow=workflow,
        inputs=AddInput(x=1),
        output_model=FinalOutput,
    )

    assert result.error is not None
    assert result.error.error_type == WorkflowErrorType.PLANNING_HF


def test_runner_output_model_failure():
    class BadOutput(BaseModel):
        result: int

    runner, _ = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput),
    ])

    workflow = [
        {"id": 1, "name": "output_model", "args": {"result": "not_an_int"}},
    ]

    result = runner.run_workflow(
        workflow=workflow,
        inputs=AddInput(x=1),
        output_model=BadOutput,
    )

    assert result.error is not None
    assert result.error.error_type == WorkflowErrorType.OUTPUTS_FAILURE


def test_run_workflow_batch_returns_aggregate_error():
    runner, avc = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput),
        LlmFunctionItemInput(func=double, input_model=DoubleInput, output_model=DoubleOutput),
    ])

    workflow = _make_add_double_workflow(avc["available_functions"])

    test_params = [
        {"inputs": AddInput(x=1), "outputs": FinalOutput(result=4)},
        {"inputs": AddInput(x=2), "outputs": FinalOutput(result=999)},
    ]

    result = runner.run_workflow(
        workflow=workflow,
        test_params=test_params,
        output_model=FinalOutput,
    )

    assert result.error is not None
    assert result.error.additional_info.get("failed_cases") == [1]
    assert len(result.case_results) == 2


def test_run_workflow_batch_all_pass():
    runner, avc = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput),
        LlmFunctionItemInput(func=double, input_model=DoubleInput, output_model=DoubleOutput),
    ])

    workflow = _make_add_double_workflow(avc["available_functions"])

    test_params = [
        {"inputs": AddInput(x=1), "outputs": FinalOutput(result=4)},
        {"inputs": AddInput(x=2), "outputs": FinalOutput(result=6)},
    ]

    result = runner.run_workflow(
        workflow=workflow,
        test_params=test_params,
        output_model=FinalOutput,
    )

    assert result.error is None
    assert len(result.case_results) == 2


def test_json_schema_to_base_model_roundtrip():
    runner, _ = _make_runner([
        LlmFunctionItemInput(func=add_one, input_model=AddInput, output_model=AddOutput)
    ])

    schema = {
        "title": "Top",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "items": {
                "type": "array",
                "items": {"$ref": "#/$defs/Item"},
            },
        },
        "required": ["name", "items"],
        "$defs": {
            "Item": {
                "title": "Item",
                "type": "object",
                "properties": {
                    "value": {"type": "integer"},
                    "note": {"type": "string"},
                },
                "required": ["value"],
            }
        },
    }

    Model = runner.json_schema_to_base_model(schema)
    model = Model(name="x", items=[{"value": 3, "note": "n"}])

    assert model.name == "x"
    assert model.items[0].value == 3
    assert model.items[0].note == "n"


def test_runner_notebook_style_nested_outputs():
    class GetWeatherInput(BaseModel):
        city: str

    class GetWeatherOutput(BaseModel):
        condition: str
        temperature: float

    def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
        return GetWeatherOutput(condition="Sunny", temperature=20.0)

    class QueryDatabaseInput(BaseModel):
        topic: str
        location: str | None = None

    class QueryDatabaseOutput(BaseModel):
        info: str

    def query_database(inputs: QueryDatabaseInput) -> QueryDatabaseOutput:
        return QueryDatabaseOutput(info="Content extracted from the database for your query is ...")

    class EmailInformationPoint(BaseModel):
        title: str
        content: str

    class WfInputs(BaseModel):
        city: str

    class WfOutputs(BaseModel):
        city: str
        information: list[EmailInformationPoint]

    runner, avc = _make_runner([
        LlmFunctionItemInput(func=get_weather, input_model=GetWeatherInput, output_model=GetWeatherOutput),
        LlmFunctionItemInput(func=query_database, input_model=QueryDatabaseInput, output_model=QueryDatabaseOutput),
    ])

    func_id_by_name = {f.name: f.func_id for f in avc["available_functions"]}
    workflow = [
        {"id": 1, "name": "query_database", "func_id": func_id_by_name["query_database"], "args": {"topic": "birds", "location": "0.output.city"}},
        {"id": 2, "name": "get_weather", "func_id": func_id_by_name["get_weather"], "args": {"city": "0.output.city"}},
        {"id": 3, "name": "output_model", "args": {
            "city": "0.output.city",
            "information": [
                {"title": "Birds Info", "content": "1.output.info"},
                {"title": "Weather", "content": "2.output.condition"},
            ],
        }},
    ]

    expected = WfOutputs(
        city="Berlin",
        information=[
            EmailInformationPoint(title="Birds Info", content="Content extracted from the database for your query is ..."),
            EmailInformationPoint(title="Weather", content="Sunny"),
        ],
    )

    result = runner.run_workflow(
        workflow=workflow,
        inputs=WfInputs(city="Berlin"),
        expected_outputs=expected,
        output_model=WfOutputs,
    )

    assert result.error is None
    assert result.outputs["3"] == expected
