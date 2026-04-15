# Errors

`llm_function` raises `LlmFunctionError` when [`workflow_auto_assembler`](https://pypi.org/project/workflow-auto-assembler/) returns a workflow error.

This keeps the typed function contract clean:

- successful calls return the declared output model
- failed calls raise

## Underlying Workflow Error

The original workflow error is available on:

- `exc.workflow_error`

This makes it possible to:

- catch one stable exception type at the `llm_function` layer
- still inspect the underlying workflow failure details


## Example

Example raised error:

```python
---------------------------------------------------------------------------
LlmFunctionError                          Traceback (most recent call last)
Cell In[9], line 17
     12     """
     13     Get weather for the provided city and prepare a short user-facing non forcast summary.
     14     """
     15     pass
---> 17 result = impossible_get_city_weather(WfInputs(city="Wrocław"))
     18 result

File ~/miniforge3/envs/testenv/lib/python3.10/site-packages/llm_function/llm_function.py:596, in LlmFunction.as_decorator.<locals>.decorator.<locals>.sync_wrapper(*args, **kwargs)
    593 @wraps(func)
    594 def sync_wrapper(*args, **kwargs):
    595     bound = signature.bind(*args, **kwargs)
--> 596     return self._run_coro_blocking(_invoke_async(bound.arguments[input_name]))

File ~/miniforge3/envs/testenv/lib/python3.10/site-packages/llm_function/llm_function.py:509, in LlmFunction._run_coro_blocking(self, coro)
    507 if "value" in error:
    508     if isinstance(error["value"], LlmFunctionError):
--> 509         raise LlmFunctionError(error["value"].workflow_error) from None
    510     raise error["value"]
    512 return result["value"]

LlmFunctionError: The required output field "summary" must contain a non‑forecast description of the weather, and no available function explicitly performs weather summarization or non‑forecast content generation. The only tool that provides weather information is get_weather, which returns a forecast string, not a separate summary. Since there is no function that can transform or produce a non‑forecast summary from the inputs, the task cannot be constructed with the provided tools.
```

Example underlying workflow error:

```python
{
    "error_message": "The available functions only allow retrieving weather information and sending an email. There is no function that can query the database to obtain bird information, so the required 'info' field in the output schema cannot be produced.",
    "error_type": None,
    "additional_info": {
        "stage": "init_check",
        "workflow_possible": False,
        "justification": "The available functions only allow retrieving weather information and sending an email. There is no function that can query the database to obtain bird information, so the required 'info' field in the output schema cannot be produced."
    }
}
```
