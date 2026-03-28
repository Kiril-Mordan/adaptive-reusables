from pydantic import BaseModel
import json
import pytest

from python_modules.workflow_auto_assembler import (
    AssembledWorkflow,
    PlanningStepsResp,
    WorkflowAutoAssembler,
    WorkflowDescription,
)
from python_modules.components.workflow_runner import TestedWorkflow, WorkflowItem
from python_modules.components.workflow_storage import WorkflowStorage
from python_modules.components.wa_general_models import WorkflowError, WorkflowErrorType


class InputModel(BaseModel):
    x: int


class OutputModel(BaseModel):
    y: int


class EmailInformationPoint(BaseModel):
    title: str
    content: str


class NestedOutputModel(BaseModel):
    information: list[EmailInformationPoint]


class DummyLogger:
    def debug(self, *args, **kwargs):
        return None


def _make_storage_wa() -> WorkflowAutoAssembler:
    wa = WorkflowAutoAssembler.__new__(WorkflowAutoAssembler)
    wa.workflow_error_types = WorkflowErrorType
    wa.workflow_error = WorkflowError
    wa.storage_path = ""
    wa.logger = DummyLogger()
    wa.storage_h = WorkflowStorage(
        workflow_error_types=WorkflowErrorType,
        workflow_error=WorkflowError,
        model_class=AssembledWorkflow,
    )
    return wa


def test_workflow_storage_round_trip_preserves_dynamic_models_and_errors():
    wa = _make_storage_wa()

    workflow_object = AssembledWorkflow(
        id="workflow-id",
        input_id="input-id",
        planning=PlanningStepsResp(
            tester=TestedWorkflow(
                workflow=[WorkflowItem(name="step", args={"value": "1.output.y"})],
                inputs=InputModel(x=1),
                outputs={"1": OutputModel(y=2)},
                error=WorkflowError(
                    error_message="boom",
                    error_type=WorkflowErrorType.RUNNER,
                    additional_info={"step_id": 1},
                ),
            )
        ),
        description=WorkflowDescription(
            task_description="test",
            input_model_json=InputModel.model_json_schema(),
            output_model_json=OutputModel.model_json_schema(),
        ),
    )

    payload = wa.storage_h.serialize(workflow_object)
    restored = wa.storage_h.deserialize(payload)

    assert isinstance(restored.planning.tester, TestedWorkflow)
    assert isinstance(restored.planning.tester.inputs, InputModel)
    assert restored.planning.tester.inputs.x == 1
    assert isinstance(restored.planning.tester.outputs["1"], OutputModel)
    assert restored.planning.tester.outputs["1"].y == 2
    assert isinstance(restored.planning.tester.error, WorkflowError)
    assert restored.planning.tester.error.error_type == WorkflowErrorType.RUNNER
    assert restored.planning.tester.error.additional_info == {"step_id": 1}


def test_workflow_storage_round_trip_preserves_nested_dynamic_model_lists():
    wa = _make_storage_wa()

    workflow_object = AssembledWorkflow(
        id="workflow-id",
        input_id="input-id",
        planning=PlanningStepsResp(
            tester=TestedWorkflow(
                workflow=[WorkflowItem(name="step", args={"value": "1.output.information"})],
                inputs=InputModel(x=1),
                outputs={
                    "1": NestedOutputModel(
                        information=[
                            EmailInformationPoint(title="first", content="alpha"),
                            EmailInformationPoint(title="second", content="beta"),
                        ]
                    )
                },
                error=None,
            )
        ),
        description=WorkflowDescription(
            task_description="test",
            input_model_json=InputModel.model_json_schema(),
            output_model_json=NestedOutputModel.model_json_schema(),
        ),
    )

    payload = wa.storage_h.serialize(workflow_object)
    restored = wa.storage_h.deserialize(payload)

    output_model = restored.planning.tester.outputs["1"]
    assert isinstance(output_model, NestedOutputModel)
    assert len(output_model.information) == 2
    assert output_model.information[0].title == "first"
    assert output_model.information[0].content == "alpha"
    assert output_model.information[1].title == "second"
    assert output_model.information[1].content == "beta"


def test_workflow_storage_save_and_load_latest_complete(tmp_path):
    wa = _make_storage_wa()

    older_complete = AssembledWorkflow(
        id="workflow-1",
        input_id="shared-input",
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="older complete"),
    )
    latest_incomplete = AssembledWorkflow(
        id="workflow-2",
        input_id="shared-input",
        workflow_completed=False,
        workflow=[{"id": 2, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="latest incomplete"),
    )

    first_path = wa.save_workflow_to_storage(older_complete, str(tmp_path))
    second_path = wa.save_workflow_to_storage(latest_incomplete, str(tmp_path))

    assert first_path.exists()
    assert second_path.exists()
    assert first_path.parent.name == "workflows"
    assert older_complete.saved_at is None

    latest_workflow = wa.load_latest_workflow("shared-input", str(tmp_path), completed=False)
    assert latest_workflow.id == "workflow-2"
    assert latest_workflow.workflow_completed is False

    latest_complete = wa.load_latest_workflow("shared-input", str(tmp_path), completed=True)
    assert latest_complete.id == "workflow-1"
    assert latest_complete.workflow_completed is True
    assert latest_complete.saved_at is not None
    assert wa.storage_h.workflow_cache["shared-input"].id == "workflow-1"


def test_workflow_storage_load_workflows_to_cache_and_add_to_cache(tmp_path):
    wa = _make_storage_wa()

    complete_workflow = AssembledWorkflow(
        id="workflow-a",
        input_id="input-a",
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="complete"),
    )
    incomplete_workflow = AssembledWorkflow(
        id="workflow-b",
        input_id="input-b",
        workflow_completed=False,
        workflow=[{"id": 2, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="incomplete"),
    )

    wa.save_workflow_to_storage(complete_workflow, str(tmp_path))
    wa.save_workflow_to_storage(incomplete_workflow, str(tmp_path))
    wa.storage_h.workflow_cache.clear()

    loaded = wa.load_workflows_to_cache(
        storage_path=str(tmp_path),
        input_ids=["input-a", "input-b"],
        latest_complete=True,
    )
    assert list(loaded.keys()) == ["input-a"]
    assert wa.storage_h.workflow_cache["input-a"].id == "workflow-a"
    assert "input-b" not in wa.storage_h.workflow_cache

    manual_workflow = AssembledWorkflow(
        id="workflow-c",
        input_id="input-c",
        workflow_completed=False,
        workflow=[{"id": 3, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="manual"),
    )
    wa.add_workflow_to_cache(manual_workflow)
    assert wa.storage_h.workflow_cache["input-c"].id == "workflow-c"


def test_workflow_storage_saved_file_contains_timestamp_in_name(tmp_path):
    wa = _make_storage_wa()
    workflow_object = AssembledWorkflow(
        id="workflow-id",
        input_id="input-id",
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="stored"),
    )

    filepath = wa.save_workflow_to_storage(workflow_object, str(tmp_path))
    assert filepath.name.startswith("input-id_workflow-id_")
    assert filepath.suffix == ".json"

    payload = json.loads(filepath.read_text(encoding="utf-8"))
    assert payload["data"]["saved_at"] is not None


def test_workflow_storage_load_workflows_to_cache_without_input_ids_loads_all_complete(tmp_path):
    wa = _make_storage_wa()

    workflow_a = AssembledWorkflow(
        id="workflow-a",
        input_id="input-a",
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="a"),
    )
    workflow_b = AssembledWorkflow(
        id="workflow-b",
        input_id="input-b",
        workflow_completed=True,
        workflow=[{"id": 2, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="b"),
    )

    wa.save_workflow_to_storage(workflow_a, str(tmp_path))
    wa.save_workflow_to_storage(workflow_b, str(tmp_path))
    wa.storage_h.workflow_cache.clear()

    loaded = wa.load_workflows_to_cache(
        storage_path=str(tmp_path),
        input_ids=None,
        latest_complete=True,
    )

    assert set(loaded.keys()) == {"input-a", "input-b"}
    assert set(wa.storage_h.workflow_cache.keys()) == {"input-a", "input-b"}


def test_workflow_storage_uses_default_storage_path_when_omitted(tmp_path):
    wa = _make_storage_wa()
    wa.storage_path = str(tmp_path)

    workflow_object = AssembledWorkflow(
        id="workflow-default",
        input_id="input-default",
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="default"),
    )

    filepath = wa.save_workflow_to_storage(workflow_object)
    restored = wa.load_latest_workflow("input-default", completed=True)

    assert filepath.parent == tmp_path / "workflows"
    assert restored is not None
    assert restored.id == "workflow-default"


def test_get_input_id_is_stable_for_same_inputs():
    wa = _make_storage_wa()

    input_id_1 = wa.get_input_id(
        task_description="same task",
        input_model=InputModel,
        output_model=OutputModel,
    )
    input_id_2 = wa.get_input_id(
        task_description="same task",
        input_model=InputModel,
        output_model=OutputModel,
    )
    input_id_3 = wa.get_input_id(
        task_description="different task",
        input_model=InputModel,
        output_model=OutputModel,
    )

    assert input_id_1 == input_id_2
    assert input_id_1 != input_id_3


@pytest.mark.anyio
async def test_actualize_workflow_uses_cache_before_planning(tmp_path, monkeypatch):
    wa = _make_storage_wa()
    wa.storage_path = str(tmp_path)

    workflow_object = AssembledWorkflow(
        id="workflow-cached",
        input_id=wa.get_input_id("cached task", InputModel, OutputModel),
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="cached task"),
    )
    wa.storage_h.workflow_cache[workflow_object.input_id] = workflow_object

    calls = {"plan": 0, "run": 0}

    async def fake_plan_workflow(*args, **kwargs):
        calls["plan"] += 1
        return workflow_object

    async def fake_run_workflow(*args, **kwargs):
        calls["run"] += 1
        return OutputModel(y=7)

    monkeypatch.setattr(WorkflowAutoAssembler, "plan_workflow", fake_plan_workflow)
    monkeypatch.setattr(WorkflowAutoAssembler, "run_workflow", fake_run_workflow)

    result = await wa.actualize_workflow(
        task_description="cached task",
        run_inputs=InputModel(x=1),
        input_model=InputModel,
        output_model=OutputModel,
    )

    assert result.y == 7
    assert calls["plan"] == 0
    assert calls["run"] == 1


@pytest.mark.anyio
async def test_actualize_workflow_plans_saves_and_caches_when_missing(tmp_path, monkeypatch):
    wa = _make_storage_wa()
    wa.storage_path = str(tmp_path)

    planned_workflow = AssembledWorkflow(
        id="workflow-planned",
        input_id=wa.get_input_id("new task", InputModel, OutputModel),
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="new task"),
    )

    calls = {"plan": 0, "run": 0}

    async def fake_plan_workflow(*args, **kwargs):
        calls["plan"] += 1
        return planned_workflow

    async def fake_run_workflow(*args, **kwargs):
        calls["run"] += 1
        return OutputModel(y=9)

    monkeypatch.setattr(WorkflowAutoAssembler, "plan_workflow", fake_plan_workflow)
    monkeypatch.setattr(WorkflowAutoAssembler, "run_workflow", fake_run_workflow)

    result = await wa.actualize_workflow(
        task_description="new task",
        run_inputs=InputModel(x=1),
        input_model=InputModel,
        output_model=OutputModel,
    )

    assert result.y == 9
    assert calls["plan"] == 1
    assert calls["run"] == 1
    assert planned_workflow.input_id in wa.storage_h.workflow_cache
    assert list((tmp_path / "workflows").glob(f"{planned_workflow.input_id}_*.json"))


@pytest.mark.anyio
async def test_actualize_workflow_returns_last_error_when_planned_workflow_is_incomplete(tmp_path, monkeypatch):
    wa = _make_storage_wa()
    wa.storage_path = str(tmp_path)

    planned_workflow = AssembledWorkflow(
        id="workflow-incomplete",
        input_id=wa.get_input_id("broken task", InputModel, OutputModel),
        workflow_completed=False,
        workflow=[{"id": 1, "name": "step", "args": {}}],
        description=WorkflowDescription(task_description="broken task"),
    )
    planned_workflow.planning.testing_errors.append(
        WorkflowError(
            error_message="broken",
            error_type=WorkflowErrorType.RUNNER,
            additional_info={"step_id": 1},
        )
    )

    calls = {"run": 0}

    async def fake_plan_workflow(*args, **kwargs):
        return planned_workflow

    async def fake_run_workflow(*args, **kwargs):
        calls["run"] += 1
        return OutputModel(y=999)

    monkeypatch.setattr(WorkflowAutoAssembler, "plan_workflow", fake_plan_workflow)
    monkeypatch.setattr(WorkflowAutoAssembler, "run_workflow", fake_run_workflow)

    result = await wa.actualize_workflow(
        task_description="broken task",
        run_inputs=InputModel(x=1),
        input_model=InputModel,
        output_model=OutputModel,
    )

    assert isinstance(result, WorkflowError)
    assert result.error_type == WorkflowErrorType.RUNNER
    assert calls["run"] == 0
