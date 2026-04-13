"""
Workflow Auto Assembler (WAA) is an experimental schema-first workflow synthesis tool.
It uses an LLM to assemble simple executable workflows from a task description, target
input/output models, and a catalog of available typed tools.

WAA is built around a narrow idea: instead of asking the model to solve a task
directly, expose tools through explicit schemas and let the model construct a linear
workflow whose intermediate states can be validated and tested. The resulting workflow
is persisted as an explicit artifact with I/O mappings, which makes it inspectable,
re-runnable, and easier to validate than a transient agent trace.

### Why Workflow-Auto-Assembler?

WAA treats tool selection and wiring as a schema-matching problem. When the required
capabilities exist in the available tool catalog, the assembled workflow can behave
like a larger typed function composed from smaller typed functions.

This package should be read as experimental adaptive tooling rather than a claim of
general autonomous planning. Its strongest use case is simple linear workflow assembly
under explicit schema constraints, with runner-based validation used to check that the
assembled workflow satisfies the requested output contract.
"""

import attrs
import attrsx

import os
from pathlib import Path
import platform
import uuid
import json
from copy import deepcopy
from typing import Type, Optional, List, Dict, Callable
from pydantic import BaseModel, Field

from .components.wa_general_models import (
    LlmFunctionItem,
    WorkflowErrorType,
    WorkflowError,
    create_avc_items,
    LlmFunctionItemInput,
    make_uid)
from .components.llm_handler import LlmHandler
from .components.workflow_check import WorkflowCheck, WorkflowCheckResponse
from .components.workflow_planner import WorkflowPlanner, WorkflowPlannerResponse
from .components.workflow_adaptor import WorkflowAdaptor, WorkflowAdaptorResponse
from .components.input_collector import InputCollector
from .components.output_comparer import OutputComparer
from .components.workflow_runner import WorkflowRunner, TestedWorkflow, TestedWorkflowBatch
from .components.workflow_storage import WorkflowStorage

__package_metadata__ = {
    "author": "Kyrylo Mordan",
    "author_email": "parachute.repo@gmail.com",
    "description": "Experimental schema-first workflow synthesis tool for assembling simple typed workflows from existing functions.",
    "url" : 'https://kiril-mordan.github.io/adaptive-reusables/workflow_auto_assembler/',
}


class PlanningStepsResp(BaseModel):
    planner : Optional[WorkflowPlannerResponse] = Field(default = None, description = "Planning steps of workflow creation.")
    planner_iters : Optional[List[WorkflowPlannerResponse]] = Field(default = [], description = "Snapshot of planning steps of workflow creation at each reset.")
    adaptor : Optional[WorkflowAdaptorResponse] = Field(default = None, description = "Adapting steps of workflow creation.")
    adaptor_iters : Optional[List[WorkflowAdaptorResponse]] = Field(default = [], description = "Snapshot of adapting steps of workflow creation at each reset.")
    tester : Optional[TestedWorkflow | TestedWorkflowBatch] = Field(default = None, description = "Testing step of workflow creation.")
    planner_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if planner needs reset during retry.")
    adaptor_rerun_needed : Optional[bool] = Field(default = True, description = "Indicates if adaptor needs reset during retry.")
    testing_errors : Optional[List[WorkflowError]] = Field(default = [], description = "Errors during testing workflow.")
    test_retries : int = Field(default = 0, description = "Retries completed during planning and testing loop.")

class WorkflowDescription(BaseModel):
    task_description : Optional[str] = Field(default = None, description="Description of the workflow.")
    input_model_json : Optional[dict] = Field(default = None, description="Input model for workflow.")
    output_model_json : Optional[dict] = Field(default = None, description="Output model for workflow.")

class AssembledWorkflow(BaseModel):
    id : str = Field(description = "Unique id for task based on hash of inputs")
    input_id : str = Field(description = "Unique id for task inputs based on hash of inputs")
    saved_at : Optional[str] = Field(default = None, description = "UTC timestamp of when workflow was saved to storage.")
    init_check : Optional[WorkflowCheckResponse] = Field(default = None, description = "Initial check.")
    planning : Optional[PlanningStepsResp] = Field(default = PlanningStepsResp(), description = "Responses from planning steps.")
    workflow_possible : Optional[bool] = Field(default = None, description = "Indicates if workflow could be planned given provided tools.")
    workflow_completed : Optional[bool] = Field(default = False, description = "Indicates if workflow was completed in the preset amount of retries.")
    workflow : Optional[List[dict]] = Field(default = None, description = "Planned and tested workflow.")
    description : Optional[WorkflowDescription] = Field(default = WorkflowDescription(), description = "Workflow description.")
    loops : Optional[int] = Field(default = 1, description = "Retries completed during planning and testing loop.")

@attrsx.define(handler_specs = {
        "llm_handler" : LlmHandler,
        "check" : WorkflowCheck,
        "planner" : WorkflowPlanner,
        "adaptor" : WorkflowAdaptor,
        "runner" : WorkflowRunner,
        "storage" : WorkflowStorage,
        "input_collector" : InputCollector,
        "output_comparer" : OutputComparer
    },
    logger_chaining={
        'logger' : True
        })
class WorkflowAutoAssembler:

    workflow_error_types = attrs.field(default=WorkflowErrorType)
    workflow_error = attrs.field(default=WorkflowError)

    available_functions: List[LlmFunctionItem] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else deepcopy(v),
    )
    available_callables: Dict[str, Callable] = attrs.field(
        default=None,
        converter=lambda v: None if v is None else dict(v),
    )

    max_output_unexpected : int = attrs.field(default=3)
    max_retry : int = attrs.field(default=10)
    reset_loops : int = attrs.field(default=2)
    storage_path : str = attrs.field(default=None)

    def __attrs_post_init__(self):

        if self.storage_path is None:
            self.storage_path = self._default_storage_path()

        self._initialize_input_collector_h()

        self._initialize_output_comparer_h()
        self._initialize_storage_h(uparams = {
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "model_class" : AssembledWorkflow,
        })
        self._initialize_llm_handler_h()
        self._initialize_planner_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "available_functions" : self.available_functions,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "max_retry" : self.max_retry
        })
        self._initialize_adaptor_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "input_collector_h" : self.input_collector_h,
            "available_functions" : self.available_functions,
            "llm_function_item_class" : LlmFunctionItem,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "max_retry" : self.max_retry
        })
        self._initialize_runner_h(uparams = {
            "output_comparer_h" : self.output_comparer_h,
            "available_functions" : self.available_functions,
            "available_callables" : self.available_callables,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
        })
        self._initialize_check_h(uparams = {
            "llm_h" : self.llm_handler_h,
            "available_functions" : self.available_functions,
            "workflow_error_types" : self.workflow_error_types,
            "workflow_error" : self.workflow_error,
            "max_retry" : self.max_retry
        })

    def _default_storage_path(self) -> str:
        system_name = platform.system()
        home_dir = Path.home()

        if system_name == "Windows":
            base_dir = Path(os.environ.get("LOCALAPPDATA", home_dir / "AppData" / "Local"))
        elif system_name == "Darwin":
            base_dir = home_dir / "Library" / "Application Support"
        else:
            base_dir = Path(os.environ.get("XDG_DATA_HOME", home_dir / ".local" / "share"))

        return str(base_dir / "workflow_auto_assembler")

    def _update_reset_logic(self, wa_resp : AssembledWorkflow, expect_tester_result: bool = False):

        tester_error = None
        if wa_resp.planning.tester is None and expect_tester_result:
            tester_error = self.workflow_error(
                error_message="Workflow execution did not produce tester results.",
                error_type=WorkflowErrorType.RUNNER,
                additional_info={"stage": "update_reset_logic"},
            )
            wa_resp.planning.testing_errors.append(tester_error)
        elif wa_resp.planning.tester is not None:
            tester_error = wa_resp.planning.tester.error

        if tester_error is None:
            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = False
            wa_resp.workflow_completed = True
            self.logger.debug(f"Workflow completed after {wa_resp.planning.test_retries + 1} planning loops!")

            return wa_resp

        self.logger.debug(f"Updating reset logic based on error: {tester_error}",
                          label = tester_error.error_type.name,
                          save_vars = ["wa_resp.planning.tester.error"])
        wa_resp.workflow_completed = False

        if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
            if "differences_by_case" in tester_error.additional_info and "differences" not in tester_error.additional_info:
                flat_differences = []
                for case_diff in tester_error.additional_info.get("differences_by_case", []):
                    case_id = case_diff.get("case_id")
                    for diff in case_diff.get("differences", []):
                        diff_item = dict(diff)
                        diff_item["case_id"] = case_id
                        flat_differences.append(diff_item)
                tester_error.additional_info["differences"] = flat_differences

        wa_resp.planning.planner_iters.append(wa_resp.planning.planner)
        wa_resp.planning.adaptor_iters.append(wa_resp.planning.adaptor)

        if tester_error.error_type is WorkflowErrorType.RUNNER:
            wa_resp.planning.planner.errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = True
            wa_resp.planning.adaptor_rerun_needed = True
            wa_resp.planning.adaptor = None

        if tester_error.error_type is WorkflowErrorType.PLANNING_HF:
            wa_resp.planning.planner.errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = True
            wa_resp.planning.adaptor_rerun_needed = True
            wa_resp.planning.adaptor = None

        if tester_error.error_type is WorkflowErrorType.OUTPUTS_UNEXPECTED:

            n_output_unexpected = len([err for err in wa_resp.planning.testing_errors if err is WorkflowErrorType.OUTPUTS_UNEXPECTED])
            n_planning_reset = len([err for err in wa_resp.planning.testing_errors if err is WorkflowErrorType.PLANNING_RESET])

            n_prev_output_unexpected = 0
            if n_planning_reset > 0:
                n_prev_output_unexpected = n_output_unexpected%n_planning_reset

            failed_cases = []
            if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
                failed_cases = tester_error.additional_info.get("failed_cases", [])


            if n_prev_output_unexpected < self.max_output_unexpected:

                # If the same output fields keep failing, escalate to planner reset sooner.
                if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
                    differences = tester_error.additional_info.get("differences", [])
                    if differences:
                        failing_paths = sorted({d.get("path") for d in differences if d.get("path")})
                        tester_error.additional_info["failing_paths"] = failing_paths

                        prev_paths = set()
                        for err in reversed(wa_resp.planning.testing_errors):
                            if getattr(err, "error_type", None) is WorkflowErrorType.OUTPUTS_UNEXPECTED:
                                prev_paths.update(err.additional_info.get("failing_paths", []))
                        if prev_paths and set(failing_paths) & prev_paths:
                            tester_error.error_type = WorkflowErrorType.PLANNING_RESET
                            wa_resp.planning.planner.errors.append(tester_error)
                            wa_resp.planning.planner_rerun_needed = True
                            wa_resp.planning.adaptor_rerun_needed = True
                            wa_resp.planning.adaptor = None
                            wa_resp.planning.testing_errors.append(tester_error)
                            wa_resp.planning.tester.error = None
                            return wa_resp

                wa_resp.planning.adaptor.all_errors.append(tester_error)

                wa_resp.planning.planner_rerun_needed = False
                wa_resp.planning.adaptor_rerun_needed = True
            else:
                if tester_error.additional_info and isinstance(tester_error.additional_info, dict):
                    differences = tester_error.additional_info.get("differences", [])
                    if differences:
                        failing_paths = sorted({d.get("path") for d in differences if d.get("path")})
                        tester_error.additional_info["failing_paths"] = failing_paths

                tester_error.error_type = WorkflowErrorType.PLANNING_RESET
                wa_resp.planning.planner.errors.append(tester_error)

                wa_resp.planning.planner_rerun_needed = True
                wa_resp.planning.adaptor_rerun_needed = True
                wa_resp.planning.adaptor = None

        if tester_error.error_type is WorkflowErrorType.OUTPUTS_FAILURE:
            wa_resp.planning.adaptor.all_errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True

        if tester_error.error_type is WorkflowErrorType.ADAPTOR_JSON:
            wa_resp.planning.adaptor.all_errors.append(tester_error)

            wa_resp.planning.planner_rerun_needed = False
            wa_resp.planning.adaptor_rerun_needed = True

        wa_resp.planning.testing_errors.append(tester_error)
        if wa_resp.planning.tester is not None:
            wa_resp.planning.tester.error = None

        return wa_resp

    def _init_wa_obj(self,
        task_description : str,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        loops : int = 1,
        init_check : Optional[WorkflowCheckResponse] = None,
        ):

        return AssembledWorkflow(
            id = uuid.uuid4().hex,
            input_id = make_uid(d = {
                "task_description" : task_description,
                "input_model" : input_model.model_json_schema() if input_model else "",
                "output_model" : output_model.model_json_schema() if output_model else ""
                }),
            init_check = init_check,
            description = WorkflowDescription(
                task_description = task_description,
                input_model_json = input_model.model_json_schema() if input_model else None,
                output_model_json = output_model.model_json_schema() if output_model else None
            ),
            loops = loops
        )

    def get_input_id(
        self,
        task_description: str,
        input_model: Type[BaseModel] = None,
        output_model: Type[BaseModel] = None,
    ) -> str:

        """
        Return stable workflow input id for current task and I/O models.
        """

        return make_uid(d={
            "task_description": task_description,
            "input_model": input_model.model_json_schema() if input_model else "",
            "output_model": output_model.model_json_schema() if output_model else "",
        })

    def _get_last_workflow_error(self, workflow_object: AssembledWorkflow):

        """
        Return the latest known workflow error from tester, testing history, adaptor, or planner state.
        """

        if workflow_object.planning.tester is not None and getattr(workflow_object.planning.tester, "error", None) is not None:
            return workflow_object.planning.tester.error

        if workflow_object.planning.testing_errors:
            return workflow_object.planning.testing_errors[-1]

        if workflow_object.planning.adaptor is not None and workflow_object.planning.adaptor.all_errors:
            return workflow_object.planning.adaptor.all_errors[-1]

        if workflow_object.planning.planner is not None and workflow_object.planning.planner.errors:
            return workflow_object.planning.planner.errors[-1]

        return None

    async def _execute_workflow_loop(
        self,
        wa_resp: AssembledWorkflow,
        task_description: str,
        input_model: Type[BaseModel] = None,
        output_model: Type[BaseModel] = None,
        available_functions: List[LlmFunctionItem] = None,
        available_callables: Dict[str, callable] = None,
        max_retry: Optional[int] = None,
        reset_loops: Optional[int] = None,
        ensure_init_check: bool = False,
        test_params: List[Dict[str, Type[BaseModel]]] = None,
        compare_params: dict = None,
        run_inputs: Type[BaseModel] = None,
    ) -> AssembledWorkflow:

        """
        Shared planner/adaptor/test loop used by planning and execution wrappers.
        """

        if max_retry is None:
            max_retry = self.max_retry

        if reset_loops is None:
            reset_loops = self.reset_loops

        while wa_resp.planning.test_retries in range(max_retry):

            if ensure_init_check and wa_resp.workflow_possible is None:

                wa_resp.init_check = await self.check_h.check_workflow(
                    task_description=task_description,
                    input_model=input_model,
                    output_model=output_model,
                    available_functions=available_functions,
                    max_retry=max_retry,
                    checked_workflow=wa_resp.init_check,
                )
                wa_resp.workflow_possible = wa_resp.init_check.workflow_possible

                if wa_resp.workflow_possible is None:
                    continue

                if wa_resp.workflow_possible is False:
                    self.logger.warning("Workflow planning is not possible!")
                    wa_resp.planning.testing_errors.append(
                        self.workflow_error(
                            error_message=wa_resp.init_check.justification or "Workflow planning is not possible.",
                            error_type=None,
                            additional_info={
                                "stage": "init_check",
                                "workflow_possible": False,
                                "justification": wa_resp.init_check.justification,
                            },
                        )
                    )
                    wa_resp.planning.planner_rerun_needed = False
                    wa_resp.planning.adaptor_rerun_needed = False
                    wa_resp.workflow_completed = False
                    break

            if wa_resp.planning.planner_rerun_needed:

                wa_resp.planning.planner = await self.planner_h.generate_workflow(
                    task_description=task_description,
                    input_model=input_model,
                    output_model=output_model,
                    available_functions=available_functions,
                    max_retry=max_retry,
                    planned_workflow=wa_resp.planning.planner,
                )

            if wa_resp.planning.adaptor_rerun_needed:

                wa_resp.planning.adaptor = await self.adaptor_h.adapt_workflow(
                    workflow=wa_resp.planning.planner.workflow,
                    input_model=input_model,
                    output_model=output_model,
                    available_functions=available_functions,
                    max_retry=max_retry,
                    adapted_workflow=wa_resp.planning.adaptor,
                )

            executable_workflow = None
            if wa_resp.planning.adaptor is not None:
                executable_workflow = wa_resp.planning.adaptor.workflow
            elif wa_resp.workflow is not None:
                executable_workflow = wa_resp.workflow

            can_test = executable_workflow is not None and (
                not ensure_init_check or (wa_resp.init_check is not None and wa_resp.init_check.workflow_possible)
            )

            if can_test and test_params is not None:

                wa_resp.planning.tester = self.runner_h.run_workflow(
                    workflow=executable_workflow,
                    test_params=test_params,
                    compare_params=compare_params,
                    output_model=output_model,
                    available_functions=available_functions,
                    available_callables=available_callables,
                )
                if task_description:
                    wa_resp.description.task_description = task_description

            if can_test and run_inputs is not None:

                wa_resp.planning.tester = self.runner_h.run_workflow(
                    workflow=executable_workflow,
                    inputs=run_inputs,
                    output_model=output_model,
                    available_functions=available_functions,
                    available_callables=available_callables,
                )
                if task_description:
                    wa_resp.description.task_description = task_description
                else:
                    task_description = wa_resp.description.task_description

            wa_resp = self._update_reset_logic(
                wa_resp=wa_resp,
                expect_tester_result=(test_params is not None or run_inputs is not None),
            )

            if wa_resp.workflow_completed:
                break

            wa_resp.planning.test_retries += 1
            if wa_resp.planning.tester and wa_resp.planning.tester.error:
                self.logger.warning(
                    f"Planning loop failed with {wa_resp.planning.tester.error.error_type} during testing. Attempts left {max_retry - wa_resp.planning.test_retries} !"
                )

            if wa_resp.planning.test_retries == (max(max_retry, 1) - 1) and reset_loops > 0:

                self.logger.warning("Planning failed to converge, reseting!")
                reset_loops = reset_loops - 1
                prev_check = wa_resp.init_check
                wa_resp = self._init_wa_obj(
                    task_description=task_description,
                    input_model=input_model,
                    output_model=output_model,
                    loops=wa_resp.loops + 1,
                    init_check=prev_check,
                )

        if (not ensure_init_check or (wa_resp.init_check and wa_resp.init_check.workflow_possible)) and wa_resp.planning.adaptor:
            wa_resp.workflow = wa_resp.planning.adaptor.workflow

        return wa_resp

    async def plan_workflow(
        self,
        task_description : str,
        test_params : List[Dict[str, Type[BaseModel]]] = None,
        compare_params : dict = None,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        max_retry : Optional[int] = None,
        reset_loops : Optional[int] = None):

        """
        Uses LLM to plans workflow based on provided tools and description.
        """

        wa_resp = self._init_wa_obj(
            task_description = task_description,
            input_model = input_model,
            output_model = output_model
        )

        self.logger.debug(f"Starting workflow planning ...", label = "START")

        wa_resp = await self._execute_workflow_loop(
            wa_resp=wa_resp,
            task_description=task_description,
            input_model=input_model,
            output_model=output_model,
            available_functions=available_functions,
            available_callables=available_callables,
            max_retry=max_retry,
            reset_loops=reset_loops,
            ensure_init_check=True,
            test_params=test_params,
            compare_params=compare_params,
        )

        if wa_resp.workflow_completed:
            self.logger.debug("Workflow completed.", label = "COMPLETED")
        else:
            self.logger.warning("Workflow failed to converge.", label = "FAILED")

        return wa_resp

    async def run_workflow(
        self,
        workflow_object : AssembledWorkflow,
        task_description : str = None,
        run_inputs : Type[BaseModel] = None,
        input_model : Type[BaseModel] = None,
        output_model : Type[BaseModel] = None,
        available_functions : List[LlmFunctionItem] = None,
        available_callables : Dict[str, callable] = None,
        max_retry : Optional[int] = None,
        reset_loops : Optional[int] = None):

        """
        Uses LLM to plans workflow based on provided tools and description.
        """

        if workflow_object.workflow_completed is False:
            return self._get_last_workflow_error(workflow_object)

        wa_resp = workflow_object.copy()

        if input_model is None:
            input_model = self.runner_h.json_schema_to_base_model(
                workflow_object.description.input_model_json)
        if output_model is None:
            output_model = self.runner_h.json_schema_to_base_model(
                workflow_object.description.output_model_json)

        wa_resp = await self._execute_workflow_loop(
            wa_resp=wa_resp,
            task_description=task_description,
            input_model=input_model,
            output_model=output_model,
            available_functions=available_functions,
            available_callables=available_callables,
            max_retry=max_retry,
            reset_loops=reset_loops,
            ensure_init_check=False,
            run_inputs=run_inputs,
        )

        if wa_resp.workflow_completed is False:
            last_error = self._get_last_workflow_error(wa_resp)
            if last_error is not None:
                return last_error

            return self.workflow_error(
                error_message="Workflow execution failed without a recorded terminal error.",
                error_type=None,
                additional_info={"stage": "run_workflow"},
            )

        tester = wa_resp.planning.tester

        if tester is None:
            return self.workflow_error(
                error_message="Workflow execution did not produce runner results.",
                error_type=None,
                additional_info={"stage": "run_workflow"},
            )

        if getattr(tester, "error", None) is not None:
            return tester.error

        if not wa_resp.workflow:
            return self.workflow_error(
                error_message="Workflow execution did not produce a final workflow.",
                error_type=None,
                additional_info={"stage": "run_workflow"},
            )

        final_step_id = str(wa_resp.workflow[-1]["id"])
        if final_step_id not in tester.outputs:
            return self.workflow_error(
                error_message="Workflow execution did not produce the final workflow output.",
                error_type=None,
                additional_info={
                    "stage": "run_workflow",
                    "final_step_id": final_step_id,
                    "available_output_ids": list(tester.outputs.keys()),
                },
            )

        return tester.outputs[final_step_id]

    async def actualize_workflow(
        self,
        task_description: str,
        force_replan: bool = False,
        run_inputs: Type[BaseModel] = None,
        test_params: List[Dict[str, Type[BaseModel]]] = None,
        compare_params: dict = None,
        input_model: Type[BaseModel] = None,
        output_model: Type[BaseModel] = None,
        available_functions: List[LlmFunctionItem] = None,
        available_callables: Dict[str, callable] = None,
        max_retry: Optional[int] = None,
        reset_loops: Optional[int] = None,
        storage_path: Optional[str] = None,
    ):

        """
        Reuse cached or stored workflow when available, otherwise plan it, persist it, cache it, and run it.
        """

        if storage_path is None:
            storage_path = self.storage_path

        input_id = self.get_input_id(
            task_description=task_description,
            input_model=input_model,
            output_model=output_model,
        )
        self.logger.debug(f"Actualizing workflow for input_id={input_id}")

        used_cached_workflow = False
        workflow_object = None if force_replan else self.storage_h.workflow_cache.get(input_id)
        if workflow_object is not None:
            used_cached_workflow = True

        if workflow_object is None:
            if force_replan:
                self.logger.debug("Force replan requested. Skipping cache and storage lookup.")
            else:
                self.logger.debug(f"Workflow not found in cache for input_id={input_id}")
                workflow_object = self.load_latest_workflow(
                    input_id=input_id,
                    storage_path=storage_path,
                    completed=True,
                )
                if workflow_object is not None:
                    used_cached_workflow = True
                    self.logger.debug(f"Workflow found in storage for input_id={input_id}")

        if workflow_object is None:
            self.logger.debug(f"Planning new workflow for input_id={input_id}")
            workflow_object = await self.plan_workflow(
                task_description=task_description,
                test_params=test_params,
                compare_params=compare_params,
                input_model=input_model,
                output_model=output_model,
                available_functions=available_functions,
                available_callables=available_callables,
                max_retry=max_retry,
                reset_loops=reset_loops,
            )
            self.logger.debug(
                f"Workflow planning completed for input_id={input_id}, workflow_completed={workflow_object.workflow_completed}"
            )
            saved_path = self.save_workflow_to_storage(
                workflow_object=workflow_object,
                storage_path=storage_path,
            )
            self.logger.debug(f"Workflow saved to {saved_path}")
        else:
            self.logger.debug(f"Workflow found in cache for input_id={input_id}")

        if (
            used_cached_workflow
            and workflow_object is not None
            and workflow_object.workflow_completed
            and self._workflow_has_missing_func_ids(
                workflow_object=workflow_object,
                available_functions=available_functions,
            )
        ):
            self.logger.debug(f"Cached workflow for input_id={input_id} references missing function ids. Replanning before execution.")
            workflow_object = await self.plan_workflow(
                task_description=task_description,
                test_params=test_params,
                compare_params=compare_params,
                input_model=input_model,
                output_model=output_model,
                available_functions=available_functions,
                available_callables=available_callables,
                max_retry=max_retry,
                reset_loops=reset_loops,
            )
            saved_path = self.save_workflow_to_storage(
                workflow_object=workflow_object,
                storage_path=storage_path,
            )
            self.add_workflow_to_cache(workflow_object)
            self.logger.debug(f"Replanned workflow saved to {saved_path}")

        if workflow_object.workflow_completed is False:
            self.logger.debug(f"Workflow for input_id={input_id} is incomplete. Returning last known error.")
            last_error = self._get_last_workflow_error(workflow_object)
            if last_error is not None:
                return last_error

            return self.workflow_error(
                error_message="Workflow planning failed without a recorded terminal error.",
                error_type=None,
                additional_info={
                    "stage": "actualize_workflow",
                    "input_id": input_id,
                    "workflow_possible": workflow_object.workflow_possible,
                },
            )

        result = await self.run_workflow(
            workflow_object=workflow_object,
            task_description=task_description,
            run_inputs=run_inputs,
            input_model=input_model,
            output_model=output_model,
            available_functions=available_functions,
            available_callables=available_callables,
            max_retry=max_retry,
            reset_loops=reset_loops,
        )

        if (
            used_cached_workflow
            and not force_replan
            and isinstance(result, WorkflowError)
            and result.error_type is WorkflowErrorType.PLANNING_HF
        ):
            self.logger.debug(f"Cached workflow for input_id={input_id} is stale. Replanning and persisting updated workflow.")
            workflow_object = await self.plan_workflow(
                task_description=task_description,
                test_params=test_params,
                compare_params=compare_params,
                input_model=input_model,
                output_model=output_model,
                available_functions=available_functions,
                available_callables=available_callables,
                max_retry=max_retry,
                reset_loops=reset_loops,
            )
            saved_path = self.save_workflow_to_storage(
                workflow_object=workflow_object,
                storage_path=storage_path,
            )
            self.add_workflow_to_cache(workflow_object)
            self.logger.debug(f"Replanned workflow saved to {saved_path}")

            if workflow_object.workflow_completed is False:
                last_error = self._get_last_workflow_error(workflow_object)
                if last_error is not None:
                    return last_error

                return self.workflow_error(
                    error_message="Workflow replanning failed without a recorded terminal error.",
                    error_type=None,
                    additional_info={
                        "stage": "actualize_workflow",
                        "input_id": input_id,
                        "workflow_possible": workflow_object.workflow_possible,
                    },
                )

            return await self.run_workflow(
                workflow_object=workflow_object,
                task_description=task_description,
                run_inputs=run_inputs,
                input_model=input_model,
                output_model=output_model,
                available_functions=available_functions,
                available_callables=available_callables,
                max_retry=max_retry,
                reset_loops=reset_loops,
            )

        return result

    def add_workflow_to_cache(self, workflow_object: AssembledWorkflow) -> AssembledWorkflow:

        """
        Add workflow object to storage cache keyed by input_id.
        """

        return self.storage_h.add_to_cache(workflow_object=workflow_object)

    def save_workflow_to_storage(
        self,
        workflow_object: AssembledWorkflow,
        storage_path: Optional[str] = None,
        indent: int = 2,
    ):

        """
        Save workflow object to filesystem storage and update cache.
        """

        if storage_path is None:
            storage_path = self.storage_path

        return self.storage_h.save_workflow(
            workflow_object=workflow_object,
            storage_path=storage_path,
            indent=indent,
        )

    def load_latest_workflow(
        self,
        input_id: str,
        storage_path: Optional[str] = None,
        completed : bool = True,
    ) -> Optional[AssembledWorkflow]:

        """
        Load latest stored workflow for the provided input id and cache it.
        """

        if storage_path is None:
            storage_path = self.storage_path

        if completed:
            return self.storage_h.load_latest_complete_workflow(
                storage_path=storage_path,
                input_id=input_id,
            )

        return self.storage_h.load_latest_workflow(
            storage_path=storage_path,
            input_id=input_id,
        )

    def load_workflows_to_cache(
        self,
        storage_path: Optional[str] = None,
        input_ids: Optional[List[str]] = None,
        latest_complete: bool = True,
    ) -> Dict[str, AssembledWorkflow]:

        """
        Alias for loading workflows into storage cache.
        """

        if storage_path is None:
            storage_path = self.storage_path

        return self.storage_h.load_workflows_to_cache(
            storage_path=storage_path,
            input_ids=input_ids,
            latest_complete=latest_complete,
        )

    def _workflow_has_missing_func_ids(
        self,
        workflow_object: AssembledWorkflow,
        available_functions: Optional[List[LlmFunctionItem]] = None,
    ) -> bool:

        """
        Return True when a workflow references non-output function ids unavailable in the current toolset.
        """

        if workflow_object is None or not workflow_object.workflow:
            return False

        if available_functions is None:
            available_functions = getattr(self, "available_functions", None)

        if available_functions is None:
            return False

        available_func_ids = {
            func_item.func_id
            for func_item in available_functions
            if getattr(func_item, "func_id", None) is not None
        }
        workflow_func_ids = {
            workflow_item.get("func_id")
            for workflow_item in workflow_object.workflow
            if workflow_item.get("name") != "output_model"
        }

        return bool(workflow_func_ids - available_func_ids)
