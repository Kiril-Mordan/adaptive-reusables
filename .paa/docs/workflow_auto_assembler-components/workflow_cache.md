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




    (PosixPath('/tmp/workflows/5101a357c99628ff74cdef1053edefc4af1c018e2c1a0e4f69907bb0f7cb3eb0_1710b456c224457ab445ebfadd0652a3_20260328T182338374545Z.json'),
     '1710b456c224457ab445ebfadd0652a3')



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




    ['5101a357c99628ff74cdef1053edefc4af1c018e2c1a0e4f69907bb0f7cb3eb0',
     '98d99dff74ad140aa88b3e8205280ce05d9ba3f08e326204b2d3244a1e66602e']



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




```python
# Force a fresh plan instead of reusing cache or storage
result = await wa.actualize_workflow(
    task_description="Get weather for a city",
    input_model=WfInputs,
    output_model=WfOutputs,
    run_inputs=WfInputs(city="Berlin"),
    storage_path="/tmp",
    force_replan=True,
)

result.model_dump()

```




    {'condition': 'Sunny'}


