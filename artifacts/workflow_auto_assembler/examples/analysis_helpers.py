import traceback


async def run_wa(available_tools, wa_class, logger = None, *args, **kwargs):

    wa = wa_class(
            logger = logger,
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
        wa = None

    return {"wf_obj" : wf_obj, "error": error, "wa" : wa}


def check_workflow_plans(outputs):

    check = {"completed" : 0, 
             "test_case_errors" : []}

    check["errors"] = [idx for idx, result in enumerate(outputs) if result["error"] is not None]

    for out in outputs:

        if out.get("wf_obj"):

            check["completed"] += 1
            if out["wf_obj"].planning.tester:
                check["test_case_errors"].append(len([tc for tc in out["wf_obj"].planning.tester.case_results if tc.error is not None]))
            else:
                check["test_case_errors"].append(None)
        else:
            check["test_case_errors"].append(None)


    return check