This notebook introduces the core usage pattern of `workflow_auto_assembler`: define typed tools, define the target input/output schemas, ask the model to assemble a workflow, and run the resulting artifact.

WAA is best understood as an experimental schema-first workflow synthesis tool, not a general-purpose autonomous agent. It works best when the task can be expressed as a simple linear composition of the available typed functions.

This page stays practical and light on internals. For deeper details, see the dedicated component docs and the research notes.


### 1. Define functions (tools)

**What this means:** WAA can only use the functions you provide. Each function must have a Pydantic input/output model so the planner can wire them correctly.

**Things to keep in mind:**
- Keep functions deterministic (same input -> same output).
- Avoid side effects in planning tests.
- Use descriptive field names and docstrings.



```python
from workflow_auto_assembler import WorkflowAutoAssembler, AssembledWorkflow, create_avc_items, LlmFunctionItemInput
```


```python
from typing import Type, List
from pydantic import BaseModel, Field

# --- Example usage ---

# Define mock functions and their associated Pydantic models:

# 1. get_weather function

class GetWeatherInput(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class GetWeatherOutput(BaseModel):
    condition: str = Field(..., description="Weather condition in the requested city.")
    temperature: float = Field(..., description="Termperature in C in the requested city.")
    humidity: float = Field(None, description="Name of the city for which weather to be extracted.")

def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
    """Get the current weather for a city from weather forcast api."""
    return GetWeatherOutput(
        condition = "Sunny",
        temperature = 20,
        humidity = 0.6
    )

# 2. send_report_email function

class EmailInformationPoint(BaseModel):
    title: str = Field(None, description="Few word description of the information.")
    content: str = Field(..., description="Content of the information.")

class SendReportEmailInput(BaseModel):
    city: str = Field(..., description="Name of the city where report will be send.")
    information: list[EmailInformationPoint]

class SendReportEmailOutput(BaseModel):
    email_sent: bool = Field(..., description="Conformation that email was send successfully.")
    message: str = Field(None, description="Optional comments from the process.")

def send_report_email(inputs: SendReportEmailInput) -> SendReportEmailOutput:
    """Sends a report email with given information points to a city."""

    if inputs.city not in ["London", "Berlin"]:
        return SendReportEmailOutput(
            email_sent = False,
            message = f"Email was not sent to {inputs.city}!"
        )
    else:
        return SendReportEmailOutput(
            email_sent = True,
            message = f"Email sent to {inputs.city}!"
        )

# 3. query_database function

class QueryDatabaseInput(BaseModel):
    topic: str = Field(..., description="Topic of a requested piece of information.")
    location: str = Field(..., description="Filter for location name.")
    uid: str = Field(None, description="Filter for unique indentifier of the database item.")

class QueryDatabaseOutput(BaseModel):
    info: str = Field(..., description="Content of the information.")
    uid: str = Field(None, description="Unique indentifier of the database item.")

def query_database(inputs : QueryDatabaseInput) -> QueryDatabaseOutput:
    """Get information from the database with provided filters."""
    return QueryDatabaseOutput(
        info = f"Content extracted from the database for {inputs.topic} in {inputs.location} is ...",
        uid = "0000"
    )

# 4. query_web function

class QueryWebInput(BaseModel):
    search_input: str = Field(..., description="Topic to be searched on the web.")


class QueryWebOutput(BaseModel):
    search_results: List[str] = Field(..., description="List relevant info from search results.")


def query_web(inputs : QueryWebInput) -> QueryWebOutput:
    """Get information from the internet for provided query."""
    return QueryWebOutput(
        search_results = ["Relevant content found in first search result is ..."],
    )

# Create structured items for each function 
available_tools = create_avc_items(functions = [
    LlmFunctionItemInput(**{"func" : get_weather , "input_model" : GetWeatherInput, "output_model" : GetWeatherOutput}),
    LlmFunctionItemInput(**{"func" : send_report_email , "input_model" : SendReportEmailInput, "output_model" : SendReportEmailOutput}),
    LlmFunctionItemInput(**{"func" : query_database , "input_model" : QueryDatabaseInput, "output_model" : QueryDatabaseOutput}),
    LlmFunctionItemInput(**{"func" : query_web , "input_model" : QueryWebInput, "output_model" : QueryWebOutput})
])
```

### 2. Define the task (inputs and outputs)

**What this means:** You describe the goal in plain language and define the input/output schemas the workflow should satisfy.

**Why it matters:** The planner uses these schemas to decide which tools to call and how to connect them.



```python
task_description = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which the report email was sent.")
    email_sent: bool = Field(..., description="Confirmation that the report email was sent.")
    info : str  = Field(..., description="Information found in the database.")
    message: str = Field(None, description="Optional comments from the email sending process.")

```

### 3. Plan the workflow

**What this means:** WAA uses the LLM to draft and validate a workflow that connects your tools into a valid plan for the task.

**What you get back:** an `AssembledWorkflow` object that includes the adapted workflow steps and planning state.

**Include tests:** Passing `test_params` is recommended because it lets WAA check the assembled workflow against expected outputs before you reuse it later.



```python
import logging

test_params = [
    {
        "inputs": WfInputs(city = "London"),
        "outputs": WfOutputs(
            city = "London",
            info = "Content extracted from the database for Birds in London is ...",
            email_sent = True,
            message = "Email sent to London!"
        )
    },
    {
        "inputs": WfInputs(city = "Berlin"),
        "outputs": WfOutputs(
            city = "Berlin",
            info = "Content extracted from the database for Birds in Berlin is ...",
            email_sent = True,
            message = "Email sent to Berlin!"
        )
    }
]

wa = WorkflowAutoAssembler(
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

wf_obj = await wa.plan_workflow(
    task_description = task_description,
    test_params = test_params,
    input_model = WfInputs,
    output_model = WfOutputs,
)

```


```python
wf_obj.workflow_completed
```




    True




```python
wf_obj.workflow
```




    [{'id': 1,
      'func_id': '358894ca32285be1fba1f3f7b49020b86375ed1bf3d3e9a1b90bf1a17be29ff7',
      'name': 'query_database',
      'args': {'topic': 'Birds', 'location': '0.output.city'}},
     {'id': 2,
      'func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a',
      'name': 'get_weather',
      'args': {'city': '0.output.city'}},
     {'id': 3,
      'func_id': '879952407bf2ea9735064f8069fbd776592f7bd541fcfe0727acdce61c42a94c',
      'name': 'send_report_email',
      'args': {'city': '0.output.city',
       'information': [{'content': '1.output.info'}]}},
     {'id': 4,
      'func_id': '842ee0f8580f0e6a379e52fc7c551c726797423bf7c1c0cf5eab9e890a225815',
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'email_sent': '3.output.email_sent',
       'info': '1.output.info',
       'message': '3.output.message'}}]



### 4. Run the workflow later

**What this means:** You can reuse the planned workflow for new inputs without re-planning each time.

**Why LLM params appear again:** The runner can still need the LLM if it has to repair a broken workflow
(for example, remapping `output_model` after a validation failure). So you provide the LLM handler
configuration again even though you are not explicitly planning from scratch.

**Note:** `run_workflow` returns only the final output model instance by default.



```python
wa = WorkflowAutoAssembler(
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

output = await wa.run_workflow(
    workflow_object = wf_obj,
    run_inputs = WfInputs(city = "London")
)

output.model_dump()

```




    {'city': 'London',
     'email_sent': True,
     'info': 'Content extracted from the database for Birds in London is ...',
     'message': 'Email sent to London!'}



### 5. Plan and run workflows with cache

**What this means:** `actualize_workflow` is the high-level entrypoint. It reuses an existing workflow from cache or storage when possible, otherwise it plans one, saves it, caches it, and then runs it. Use `force_replan=True` to skip reuse and force planning again.



```python
wa = WorkflowAutoAssembler(
    available_functions = available_tools["available_functions"],
    available_callables = available_tools["available_callables"],
    storage_path = "/tmp", # Optional, otherwise would use some dir in your system
    llm_handler_params = {
        "llm_h_type" : "ollama",
        "llm_h_params" : {
            "connection_string": "http://localhost:11434",
            "model_name": "gpt-oss:20b"
        }
    }
)

output = await wa.actualize_workflow(
    task_description = task_description,
    input_model = WfInputs,
    output_model = WfOutputs,
    run_inputs = WfInputs(city = "Berlin")
)


output.model_dump()

```




    {'city': 'Berlin',
     'email_sent': True,
     'info': 'Content extracted from the database for birds in Berlin is ...',
     'message': 'Email sent to Berlin!'}



Force replanning instead of reusing cache/storage


```python
test_params = [
    {
        "inputs": WfInputs(city = "London"),
        "outputs": WfOutputs(
            city = "London",
            info = "Content extracted from the database for Birds in London is ...",
            email_sent = True,
            message = "Email sent to London!"
        )
    },
    {
        "inputs": WfInputs(city = "Berlin"),
        "outputs": WfOutputs(
            city = "Berlin",
            info = "Content extracted from the database for Birds in Berlin is ...",
            email_sent = True,
            message = "Email sent to Berlin!"
        )
    },
    {
        "inputs": WfInputs(city = "Sydney"),
        "outputs": WfOutputs(
            city = "Sydney",
            info = "Content extracted from the database for Birds in Sydney is ...",
            email_sent = False,
            message = "Email sent to Sydney!"
        )
    }
]

output = await wa.actualize_workflow(
    task_description = task_description,
    input_model = WfInputs,
    output_model = WfOutputs,
    run_inputs = WfInputs(city = "Sydney"),
    force_replan = True,
)

output.model_dump()
```




    {'city': 'Sydney',
     'email_sent': False,
     'info': 'Content extracted from the database for birds in Sydney is ...',
     'message': 'Email was not sent to Sydney!'}


