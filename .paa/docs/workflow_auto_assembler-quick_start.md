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
    return SendReportEmailOutput(
        email_sent = True,
        message = "Email sent to city of your choosing!"
    )

# 3. query_database function

class QueryDatabaseInput(BaseModel):
    topic: str = Field(..., description="Topic of a requested piece of information.")
    location: str = Field(None, description="Filter for location name.")
    uid: str = Field(None, description="Filter for unique indentifier of the database item.")

class QueryDatabaseOutput(BaseModel):
    info: str = Field(..., description="Content of the information.")
    uid: str = Field(None, description="Unique indentifier of the database item.")

def query_database(inputs : QueryDatabaseInput) -> QueryDatabaseOutput:
    """Get information from the database with provided filters."""
    return QueryDatabaseOutput(
        info = "Content extracted from the database for your query is ...",
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
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")
```

### 3. Plan the workflow

**What this means:** WAA uses the LLM to draft a workflow that connects your tools into a valid plan for the task.

**What you get back:** an `AssembledWorkflow` object that includes the adapted workflow steps.



```python
import logging

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
    input_model = WfInputs,
    output_model = WfOutputs,
)

```


```python
wf_obj.workflow
```




    [{'id': 1,
      'func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac',
      'name': 'query_database',
      'args': {'topic': 'birds'}},
     {'id': 2,
      'func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a',
      'name': 'get_weather',
      'args': {'city': '0.output.city'}},
     {'id': 3,
      'func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a',
      'name': 'send_report_email',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather Condition', 'content': '2.output.condition'}]}},
     {'id': 4,
      'func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f',
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather Condition', 'content': '2.output.condition'}]}}]



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
     'information': [{'title': 'Birds Information',
       'content': 'Content extracted from the database for your query is ...'},
      {'title': 'Weather Condition', 'content': 'Sunny'}]}


