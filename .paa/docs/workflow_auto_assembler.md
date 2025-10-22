```python
from workflow_auto_assembler import WorkflowAutoAssembler, AssembledWorkflow, create_avc_items, LlmFunctionItemInput
```

### 1. Define available tools


```python
from typing import Type
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

# Create structured items for each function

available_tools = create_avc_items(functions = [
    LlmFunctionItemInput(**{"func" : get_weather , "input_model" : GetWeatherInput, "output_model" : GetWeatherOutput}),
    LlmFunctionItemInput(**{"func" : send_report_email , "input_model" : SendReportEmailInput, "output_model" : SendReportEmailOutput}),
    LlmFunctionItemInput(**{"func" : query_database , "input_model" : QueryDatabaseInput, "output_model" : QueryDatabaseOutput})
])
```

### 2. Define task, expected inputs and outputs


```python
task_description = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")
```

### 3. Initialize and run workflow assembler


```python
AssembledWorkflow.model_fields
```




    {'planning': FieldInfo(annotation=Union[PlanningStepsResp, NoneType], required=False, default=PlanningStepsResp(planner=None, adaptor=None, tester=None, planner_rerun_needed=True, adaptor_rerun_needed=True, testing_errors=[], test_retries=0), description='Responses from planning steps.'),
     'workflow_completed': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False, description='Indicates if workflow was completed in the preset amount of retries.'),
     'workflow': FieldInfo(annotation=Union[dict, NoneType], required=False, default=None, description='Planned and tested workflow.'),
     'description': FieldInfo(annotation=Union[WorfklowDescription, NoneType], required=False, default=WorfklowDescription(task_description=None, input_model_json=None, output_model_json=None), description='Workflow description.')}




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

wf_obj = await wa.plan_workflow(
    task_description = task_description,
    input_model = WfInputs,
    output_model = WfOutputs,
    test_inputs = WfInputs(city = "Berlin")
)
```


```python
wf_obj.workflow_completed
```




    True




```python
wf_obj.planning.test_retries
```




    0




```python
wf_obj.workflow
```




    [{'id': 1,
      'func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac',
      'name': 'query_database',
      'args': {'topic': 'birds', 'location': '0.output.city'}},
     {'id': 2,
      'func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a',
      'name': 'get_weather',
      'args': {'city': '0.output.city'}},
     {'id': 3,
      'func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a',
      'name': 'send_report_email',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Bird Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}},
     {'id': 4,
      'func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f',
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Bird Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}}]




```python
wf_obj.planning.tester.outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000'),
     '2': GetWeatherOutput(condition='Sunny', temperature=20.0, humidity=0.6),
     '3': SendReportEmailOutput(email_sent=True, message='Email sent to city of your choosing!'),
     '4': WfOutputs(city='Berlin', information=[EmailInformationPoint(title='Bird Information', content='Content extracted from the database for your query is ...'), EmailInformationPoint(title='Weather', content='Sunny')])}



### 4. Run assembled workflow


```python
output = await wa.run_workflow(
    workflow_object = wf_obj,
    run_inputs = WfInputs(city = "London")
)

output.model_dump()
```




    {'city': 'London',
     'information': [{'title': 'Bird Information',
       'content': 'Content extracted from the database for your query is ...'},
      {'title': 'Weather', 'content': 'Sunny'}]}


