```python
from workflow_auto_assembler import WorkflowAutoAssembler, WorkflowAssemblerResponse, create_function_item
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
available_functions = [
    create_function_item(get_weather, GetWeatherInput, GetWeatherOutput),
    create_function_item(send_report_email, SendReportEmailInput, SendReportEmailOutput),
    create_function_item(query_database, QueryDatabaseInput, QueryDatabaseOutput)
]

available_callables = {
    "get_weather" : get_weather,
    "send_report_email" : send_report_email,
    "query_database" : query_database
}
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
WorkflowAssemblerResponse.model_fields
```




    {'planner_response': FieldInfo(annotation=Union[WorkflowPlannerResponse, NoneType], required=False, default=None, description='Planning steps of workflow creation.'),
     'adaptor_response': FieldInfo(annotation=Union[WorkflowAdaptorResponse, NoneType], required=False, default=None, description='Adapting step of workflow creation.'),
     'tester_response': FieldInfo(annotation=Union[TestedWorkflow, NoneType], required=False, default=None, description='Testing step of workflow creation.'),
     'testing_errors': FieldInfo(annotation=Union[List[WorkflowError], NoneType], required=False, default=[], description='Errors during testing workflow.'),
     'planner_rerun_needed': FieldInfo(annotation=Union[bool, NoneType], required=False, default=True, description='Indicates if planner needs reset during retry.'),
     'adaptor_rerun_needed': FieldInfo(annotation=Union[bool, NoneType], required=False, default=True, description='Indicates if adaptor needs reset during retry.'),
     'workflow_completed': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False, description='Indicates if workflow was completed in the preset amount of retries.'),
     'test_retries': FieldInfo(annotation=int, required=False, default=0, description='Retries completed during planning and testing loop.'),
     'test_output': FieldInfo(annotation=Union[BaseModel, NoneType], required=False, default=None, description='Errors during testing workflow.'),
     'workflow': FieldInfo(annotation=Union[dict, NoneType], required=False, default=None, description='Planned and tested workflow.')}




```python
wa = WorkflowAutoAssembler(
    available_functions = available_functions,
    available_callables = available_callables,
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


```python
wf_obj.workflow
```


```python
wf_obj.test_output
```


```python
TestedWorkflow.model_fields
```




    {'workflow': FieldInfo(annotation=List[WorkflowItem], required=True),
     'outputs': FieldInfo(annotation=Dict[str, BaseModel], required=True),
     'error': FieldInfo(annotation=Union[BaseModel, NoneType], required=True)}




```python
wf_obj['tested_wf_obj'].workflow
```




    [WorkflowItem(name='query_database', args={'topic': 'birds', 'location': '0.output.city'}),
     WorkflowItem(name='get_weather', args={'city': '0.output.city'}),
     WorkflowItem(name='send_report_email', args={'city': '0.output.city', 'information': [{'title': 'Bird Information', 'content': '1.output.info'}, {'title': 'Weather Condition', 'content': '2.output.condition'}]}),
     WorkflowItem(name='output_model', args={'city': '0.output.city', 'information': [{'title': 'Bird Information', 'content': '1.output.info'}, {'title': 'Weather Condition', 'content': '2.output.condition'}]})]




```python
wf_obj['tested_wf_obj'].outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000'),
     '2': GetWeatherOutput(condition='Sunny', temperature=20.0, humidity=0.6),
     '3': SendReportEmailOutput(email_sent=True, message='Email sent to city of your choosing!'),
     '4': WfOutputs(city='Berlin', information=[EmailInformationPoint(title='Bird Information', content='Content extracted from the database for your query is ...'), EmailInformationPoint(title='Weather Condition', content='Sunny')])}




```python
wf_obj['tested_wf_obj'].error
```
