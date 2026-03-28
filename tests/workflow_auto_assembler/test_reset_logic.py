import pytest
from pydantic import BaseModel

from python_modules.components.workflow_adaptor import WorkflowAdaptorResponse
from python_modules.components.workflow_planner import WorkflowPlannerResponse
from python_modules.components.workflow_runner import TestedWorkflow
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
