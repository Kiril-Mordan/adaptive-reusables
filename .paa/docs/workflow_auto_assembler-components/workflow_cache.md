```python
from workflow_auto_assembler import WorkflowAutoAssembler, LlmFunctionItemInput, create_avc_items
from pydantic import BaseModel, Field

def get_weather(inputs):
    return WeatherOutput(condition="Sunny")

class WeatherInput(BaseModel):
    city: str = Field(..., description="City name")

class WeatherOutput(BaseModel):
    condition: str = Field(..., description="Weather condition")

class WfInputs(BaseModel):
    city: str = Field(..., description="City name")

class WfOutputs(BaseModel):
    condition: str = Field(..., description="Weather condition")

available_tools = create_avc_items([
    LlmFunctionItemInput(func=get_weather, input_model=WeatherInput, output_model=WeatherOutput)
])

wa = WorkflowAutoAssembler(
    available_functions=available_tools["available_functions"],
    available_callables=available_tools["available_callables"],
    llm_handler_params={
        "llm_h_type": "ollama",
        "llm_h_params": {
            "connection_string": "http://localhost:11434",
            "model_name": "gpt-oss:20b"
        }
    }
)

```

#### 1. Compute workflow input id

Use `get_input_id` when you want the stable cache/storage key for a task and its input/output schemas.



```python
input_id = wa.get_input_id(
    task_description="Get weather for a city",
    input_model=WfInputs,
    output_model=WfOutputs,
)

input_id

```




    '5101a357c99628ff74cdef1053edefc4af1c018e2c1a0e4f69907bb0f7cb3eb0'



#### 2. Save and load workflows

After planning, save the workflow to storage and later load the latest reusable one for the same `input_id`.



```python
workflow_object = await wa.plan_workflow(
    task_description="Get weather for a city",
    input_model=WfInputs,
    output_model=WfOutputs,
)

saved_path = wa.save_workflow_to_storage(workflow_object, storage_path="/tmp")
loaded_workflow = wa.load_latest_workflow(
    input_id=input_id,
    storage_path="/tmp",
    completed=True,
)

saved_path, loaded_workflow.id

```




    (PosixPath('/tmp/workflows/5101a357c99628ff74cdef1053edefc4af1c018e2c1a0e4f69907bb0f7cb3eb0_c975d8c47b974165bc3829407ace643a_20260412T225457203768Z.json'),
     'c975d8c47b974165bc3829407ace643a')



#### 3. Warm up workflow cache

Load one or many stored workflows into the in-memory cache. Use `input_ids=None` to load all latest complete workflows from storage.



```python
cached_workflows = wa.load_workflows_to_cache(
    storage_path="/tmp",
    input_ids=None,
    latest_complete=True,
)

list(cached_workflows.keys())

```




    ['29ff02651cdded671bb38486e0ed7aa3baa8077219d2db1c812b348b09c773b5',
     '5101a357c99628ff74cdef1053edefc4af1c018e2c1a0e4f69907bb0f7cb3eb0',
     '6f16cf276cd92fe07d482ed492d2860b1127c04d94b6c268008f65d4850143ae']



#### 4. Actualize workflows

`actualize_workflow` is the public high-level entrypoint. It checks cache, then storage, then plans if missing, saves the workflow, caches it, and finally runs it.



```python
result = await wa.actualize_workflow(
    task_description="Get weather for a city",
    input_model=WfInputs,
    output_model=WfOutputs,
    run_inputs=WfInputs(city="Berlin"),
    storage_path="/tmp",
)

result.model_dump()

```




    {'condition': 'Sunny'}



#### 5. Replan stale cached workflows

If a stored workflow references tool `func_id`s that are no longer available, `actualize_workflow` will discard that stale workflow, replan with the current tools, save the repaired workflow, and then run it.



```python
def fetch_weather(inputs):
    return WeatherOutput(condition="Windy")

stale_task_description = "Get weather for a city (stale cache replan demo)"

stale_workflow = await wa.plan_workflow(
    task_description=stale_task_description,
    input_model=WfInputs,
    output_model=WfOutputs,
)

wa.save_workflow_to_storage(stale_workflow, storage_path="/tmp")

available_tools_v2 = create_avc_items([
    LlmFunctionItemInput(func=fetch_weather, input_model=WeatherInput, output_model=WeatherOutput)
])
```


```python
wa_replanned = WorkflowAutoAssembler(
    available_functions=available_tools_v2["available_functions"],
    available_callables=available_tools_v2["available_callables"],
    llm_handler_params={
        "llm_h_type": "ollama",
        "llm_h_params": {
            "connection_string": "http://localhost:11434",
            "model_name": "gpt-oss:20b"
        }
    }
)

replanned_result = await wa_replanned.actualize_workflow(
    task_description=stale_task_description,
    input_model=WfInputs,
    output_model=WfOutputs,
    run_inputs=WfInputs(city="Berlin"),
    storage_path="/tmp",
)

replanned_result.model_dump()
```




    {'condition': 'Windy'}




```python
replanned_workflow = wa_replanned.load_latest_workflow(
    input_id=wa_replanned.get_input_id(
        task_description=stale_task_description,
        input_model=WfInputs,
        output_model=WfOutputs,
    ),
    storage_path="/tmp",
    completed=True,
)

[step["name"] for step in replanned_workflow.workflow]
```




    ['fetch_weather', 'output_model']


