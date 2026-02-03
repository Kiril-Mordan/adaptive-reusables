import traceback

async def run_wa(available_tools, wa_class, *args, **kwargs):

    wa = wa_class(
            available_functions = available_tools["available_functions"],
            available_callables = available_tools["available_callables"],
            llm_handler_params = {
                "llm_h_type" : "ollama",
                "llm_h_params" : {
                    "connection_string": "http://localhost:11434",
                    "model_name": "gpt-oss:20b"
                }
            }
        )

    try:

    
        wf_obj = await wa.plan_workflow(
        *args, **kwargs
    )
        error = None
    except Exception as e:
        error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        print(error_message)
        wf_obj = None
        error = error_message

    return {"wf_obj" : wf_obj, "error": error }


def check_workflow_plans(task_name, results, expected_results):

    errors = [idx for idx, result in enumerate(results) if result["error"] is not None]
    no_errors = [idx for idx, result in enumerate(results) if result["error"] is None]
    workflow_possible = [idx for idx in no_errors if results[idx]['wf_obj'].workflow_possible == True]
    inpossible_workflow = [idx for idx in no_errors if results[idx]['wf_obj'].workflow_possible != True]
    workflow_completed = [idx for idx in workflow_possible if results[idx]['wf_obj'].workflow_completed == True]
    incompleted_workflows = [idx for idx, result in enumerate(results) if idx not in workflow_completed]

    return {
        "task" : task_name,
        "n_errors" : len(errors),
        "frac_errors" : len(errors)/len(results),
        "failed_retries" : errors,
        "n_workflow_possible": len(workflow_possible),
        "frac_workflow_possible": len(workflow_possible)/len(results),
        "n_workflow_completed": len(workflow_completed),
        "frac_workflow_completed": len(workflow_completed)/len(results),
        "errors_idx" : errors,
        "inpossible_workflows" : inpossible_workflow,
        "incompleted_workflows" : incompleted_workflows


    }