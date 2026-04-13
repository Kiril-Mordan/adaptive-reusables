import pytest
from pydantic import BaseModel

from python_modules.components.workflow_adaptor import WorkflowAdaptorResponse
from python_modules.components.workflow_planner import WorkflowPlannerResponse
from python_modules.components.workflow_runner import TestedWorkflow, WorkflowRunner
from python_modules.components.workflow_check import WorkflowCheckResponse
from python_modules.components.workflow_check import WorkflowCheck
from python_modules.components.wa_general_models import WorkflowErrorType, WorkflowError
from python_modules.workflow_auto_assembler import AssembledWorkflow, WorkflowAutoAssembler


class DummyLogger:
    def debug(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Input(BaseModel):
    x: int


class DummyFunctionItem:
    def __init__(self, func_id: str, input_schema_json: dict):
        self.func_id = func_id
        self.input_schema_json = input_schema_json


def _make_bare_wa(max_output_unexpected: int = 3) -> WorkflowAutoAssembler:
    wa = WorkflowAutoAssembler.__new__(WorkflowAutoAssembler)
    wa.max_output_unexpected = max_output_unexpected
    wa.max_retry = 10
    wa.reset_loops = 2
    wa.workflow_error_types = WorkflowErrorType
    wa.workflow_error = WorkflowError
    wa.logger = DummyLogger()
    return wa


def _make_base_assembled(error: WorkflowError) -> AssembledWorkflow:
    planner = WorkflowPlannerResponse(
        retries=0,
        workflow=[],
        init_messages=[],
        additional_messages=[],
        errors=[],
        include_input=True,
        include_output=True,
    )
    adaptor = WorkflowAdaptorResponse(
        total_retries=0,
        planned_workflow=[],
        workflow=[{"id": 1, "name": "step", "args": {}}],
        all_errors=[],
        steps=[],
        include_input=True,
        include_output=True,
    )
    tester = TestedWorkflow(
        workflow=[],
        inputs=Input(x=1),
        outputs={},
        error=error,
    )

    wa_resp = AssembledWorkflow(id="1", input_id="1")
    wa_resp.workflow_possible = True
    wa_resp.planning.planner = planner
    wa_resp.planning.adaptor = adaptor
    wa_resp.planning.tester = tester
    return wa_resp


def test_reset_logic_outputs_unexpected_adaptor_rerun():
    wa = _make_bare_wa()
    error = WorkflowError(
        error_message="bad",
        error_type=WorkflowErrorType.OUTPUTS_UNEXPECTED,
        additional_info={"differences": [{"path": "result"}]},
    )
    wa_resp = _make_base_assembled(error)

    updated = wa._update_reset_logic(wa_resp)

    assert updated.planning.planner_rerun_needed is False
    assert updated.planning.adaptor_rerun_needed is True
    assert updated.planning.tester.error is None
    assert updated.planning.testing_errors[-1].error_type == WorkflowErrorType.OUTPUTS_UNEXPECTED


def test_reset_logic_repeated_paths_trigger_planning_reset():
    wa = _make_bare_wa()
    prev_error = WorkflowError(
        error_message="prev",
        error_type=WorkflowErrorType.OUTPUTS_UNEXPECTED,
        additional_info={"failing_paths": ["result"]},
    )
    error = WorkflowError(
        error_message="bad",
        error_type=WorkflowErrorType.OUTPUTS_UNEXPECTED,
        additional_info={"differences": [{"path": "result"}]},
    )
    wa_resp = _make_base_assembled(error)
    wa_resp.planning.testing_errors.append(prev_error)

    updated = wa._update_reset_logic(wa_resp)

    assert updated.planning.planner_rerun_needed is True
    assert updated.planning.adaptor_rerun_needed is True
    assert updated.planning.adaptor is None
    assert updated.planning.planner.errors[-1].error_type == WorkflowErrorType.PLANNING_RESET


def test_reset_logic_runner_error_resets_planner_and_adaptor():
    wa = _make_bare_wa()
    error = WorkflowError(
        error_message="boom",
        error_type=WorkflowErrorType.RUNNER,
        additional_info={"step_id": 1},
    )
    wa_resp = _make_base_assembled(error)

    updated = wa._update_reset_logic(wa_resp)

    assert updated.planning.planner_rerun_needed is True
    assert updated.planning.adaptor_rerun_needed is True
    assert updated.planning.adaptor is None
    assert updated.planning.planner.errors[-1].error_type == WorkflowErrorType.RUNNER


def test_reset_logic_missing_tester_with_expected_execution_resets_planner_and_adaptor():
    wa = _make_bare_wa()
    wa_resp = AssembledWorkflow(id="1", input_id="1")
    wa_resp.workflow_possible = True
    wa_resp.planning.planner = WorkflowPlannerResponse(
        retries=0,
        workflow=[],
        init_messages=[],
        additional_messages=[],
        errors=[],
        include_input=True,
        include_output=True,
    )
    wa_resp.planning.adaptor = WorkflowAdaptorResponse(
        total_retries=0,
        planned_workflow=[],
        workflow=[{"id": 1, "name": "step", "args": {}}],
        all_errors=[],
        steps=[],
        include_input=True,
        include_output=True,
    )
    wa_resp.planning.tester = None

    updated = wa._update_reset_logic(wa_resp, expect_tester_result=True)

    assert updated.workflow_completed is False
    assert updated.planning.planner_rerun_needed is True
    assert updated.planning.adaptor_rerun_needed is True
    assert updated.planning.adaptor is None
    assert updated.planning.planner.errors[-1].error_type == WorkflowErrorType.RUNNER


def test_reset_logic_marks_workflow_incomplete_when_cached_execution_error_occurs():
    wa = _make_bare_wa()
    error = WorkflowError(
        error_message="cached workflow references missing function ids",
        error_type=WorkflowErrorType.PLANNING_HF,
        additional_info={"step_id": 1, "func_id": "missing_func_id"},
    )
    wa_resp = _make_base_assembled(error)
    wa_resp.workflow_completed = True

    updated = wa._update_reset_logic(wa_resp)

    assert updated.workflow_completed is False
    assert updated.planning.planner_rerun_needed is True
    assert updated.planning.adaptor_rerun_needed is True


class DummyCheck:
    async def check_workflow(self, *args, **kwargs):
        return WorkflowCheckResponse(
            retries=0,
            init_messages=[],
            errors=[],
            include_input=True,
            include_output=True,
            workflow_possible=False,
            justification="Not possible with provided tools.",
        )


@pytest.mark.anyio
async def test_plan_workflow_stops_when_not_possible():
    wa = _make_bare_wa()
    wa.check_h = DummyCheck()
    wa.max_retry = 1

    class Inp(BaseModel):
        x: int

    class Out(BaseModel):
        y: int

    wa_resp = await wa.plan_workflow(
        task_description="do something impossible",
        input_model=Inp,
        output_model=Out,
    )

    assert wa_resp.workflow_possible is False
    assert wa_resp.workflow_completed is False
    assert wa_resp.planning.planner_rerun_needed is False
    assert wa_resp.planning.adaptor_rerun_needed is False
    assert wa._get_last_workflow_error(wa_resp) is not None
    assert wa._get_last_workflow_error(wa_resp).error_message == "Not possible with provided tools."


@pytest.mark.anyio
async def test_workflow_check_resume_with_empty_errors_does_not_crash():
    check = WorkflowCheck.__new__(WorkflowCheck)
    check.workflow_error_types = WorkflowErrorType
    check.workflow_error = WorkflowError
    check.max_retry = 1
    check.n_checks = 1
    check.available_functions = []
    check.logger = DummyLogger()

    checked_workflow = WorkflowCheckResponse(
        retries=0,
        init_messages=[],
        errors=[],
        include_input=True,
        include_output=True,
        workflow_possible=False,
        justification="Not possible with provided tools.",
    )

    result = await check.check_workflow(
        task_description="do something impossible",
        available_functions=[],
        checked_workflow=checked_workflow,
    )

    assert result.workflow_possible is False
    assert result.justification == "Not possible with provided tools."


def test_runner_returns_planning_hf_when_workflow_func_id_is_missing():
    runner = WorkflowRunner.__new__(WorkflowRunner)
    runner.workflow_error_types = WorkflowErrorType
    runner.workflow_error = WorkflowError
    runner.available_functions = None
    runner.available_callables = None

    workflow = [
        {"id": 1, "name": "step_a", "func_id": "missing_func_id", "args": {"x": "0.output.x"}},
        {"id": 2, "name": "output_model", "args": {"y": 1}},
    ]

    available_functions = [
        DummyFunctionItem(
            func_id="other_func_id",
            input_schema_json={
                "title": "OtherInput",
                "type": "object",
                "properties": {
                    "x": {"title": "X", "type": "integer"},
                },
                "required": ["x"],
            },
        )
    ]

    result = runner._run_single_case(
        workflow=workflow,
        inputs=Input(x=1),
        available_functions=available_functions,
        available_callables={"other_func_id": lambda inputs: inputs},
    )

    assert result.error is not None
    assert result.error.error_type == WorkflowErrorType.PLANNING_HF
    assert result.error.additional_info["step_id"] == 1
    assert result.error.additional_info["func_id"] == "missing_func_id"
    assert result.error.additional_info["func_name"] == "step_a"


@pytest.mark.anyio
async def test_run_workflow_returns_last_recorded_error_after_failed_execution_loop(monkeypatch):
    wa = _make_bare_wa()
    recorded_error = WorkflowError(
        error_message="cached workflow references missing function ids",
        error_type=WorkflowErrorType.PLANNING_HF,
        additional_info={"step_id": 1, "func_id": "missing_func_id"},
    )

    async def _fake_execute_workflow_loop(self, **kwargs):
        wa_resp = kwargs["wa_resp"]
        wa_resp.workflow_completed = False
        wa_resp.planning.testing_errors.append(recorded_error)
        if wa_resp.planning.tester is not None:
            wa_resp.planning.tester.error = None
        return wa_resp

    class DummyRunner:
        @staticmethod
        def json_schema_to_base_model(schema):
            return Input

    monkeypatch.setattr(WorkflowAutoAssembler, "_execute_workflow_loop", _fake_execute_workflow_loop)
    wa.runner_h = DummyRunner()

    workflow_object = AssembledWorkflow(
        id="1",
        input_id="1",
        workflow_completed=True,
        workflow=[{"id": 1, "name": "step_a", "func_id": "missing_func_id", "args": {}}],
    )
    workflow_object.description.input_model_json = Input.model_json_schema()
    workflow_object.description.output_model_json = Input.model_json_schema()
    workflow_object.planning.tester = TestedWorkflow(
        workflow=[],
        inputs=Input(x=1),
        outputs={"0": Input(x=1)},
        error=None,
    )

    result = await wa.run_workflow(
        workflow_object=workflow_object,
        run_inputs=Input(x=1),
        input_model=Input,
        output_model=Input,
    )

    assert result is recorded_error
