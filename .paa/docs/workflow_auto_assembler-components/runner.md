```python
from workflow_auto_assembler import create_avc_items, LlmFunctionItemInput

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

available_functions = available_tools["available_functions"]

available_callables = available_tools["available_callables"]
```

#### 1. Initialize Runner


```python
from workflow_auto_assembler import WorkflowRunner, WorkflowError, WorkflowErrorType, OutputComparer

oc = OutputComparer()

wr = WorkflowRunner(
    output_comparer_h = oc,
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    available_callables = available_callables, 
    available_functions = available_functions)
```

#### 2. Testing generated workflow


```python
class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")

adapted_workflow = [{'id': 1,
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
   'information': [{'title': 'Birds Info', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}},
 {'id': 4,
  'func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f',
  'name': 'output_model',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Birds Info', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}}]
```


```python
test_outputs = wr.run_workflow(
    workflow = adapted_workflow, 
    inputs = WfInputs(city = "Berlin"),
    output_model = WfOutputs)

test_outputs.outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000'),
     '2': GetWeatherOutput(condition='Sunny', temperature=20.0, humidity=0.6),
     '3': SendReportEmailOutput(email_sent=True, message='Email sent to city of your choosing!'),
     '4': WfOutputs(city='Berlin', information=[EmailInformationPoint(title='Birds Info', content='Content extracted from the database for your query is ...'), EmailInformationPoint(title='Weather', content='Sunny')])}




```python
expected_output = WfOutputs(
    city='Berlin', 
    information=[
        EmailInformationPoint(title='Birds Info', content='Content extracted from the database for your query is ...'), 
        EmailInformationPoint(title='Weather', content='Sunny')])

test_outputs2 = wr.run_workflow(
    workflow = adapted_workflow, 
    inputs = WfInputs(city = "Berlin"),
    expected_outputs = expected_output,
    output_model = WfOutputs)

```


```python
test_outputs2.outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000'),
     '2': GetWeatherOutput(condition='Sunny', temperature=20.0, humidity=0.6),
     '3': SendReportEmailOutput(email_sent=True, message='Email sent to city of your choosing!'),
     '4': WfOutputs(city='Berlin', information=[EmailInformationPoint(title='Birds Info', content='Content extracted from the database for your query is ...'), EmailInformationPoint(title='Weather', content='Sunny')])}



#### 3. Triggering errors

##### Error in one of the workflow functions


```python
class GetWeatherInput(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class GetWeatherOutput(BaseModel):
    condition: str = Field(..., description="Weather condition in the requested city.")
    temperature: float = Field(..., description="Termperature in C in the requested city.")
    humidity: float = Field(None, description="Name of the city for which weather to be extracted.")

def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
    """Get the current weather for a city from weather forcast api."""
    error
    return GetWeatherOutput(
        condition = "Sunny",
        temperature = 20,
        humidity = 0.6
    )

available_callables2 = available_callables.copy()

available_callables2["5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a"] = get_weather
```


```python
from workflow_auto_assembler import WorkflowPlanner
import logging

wr2 = WorkflowRunner(
    output_comparer_h = oc,
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    available_callables = available_callables2, 
    available_functions = available_functions,
    loggerLvl = logging.DEBUG)

test_outputs2 = wr2.run_workflow(
    workflow = adapted_workflow, 
    available_functions = available_functions,
    available_callables = available_callables2,
    inputs = WfInputs(city = "Berlin"),
    output_model = WfOutputs)

test_outputs2.outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000')}




```python
test_outputs2.error.model_dump()
```




    {'error_message': 'Traceback (most recent call last):\n  File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_auto_assembler/workflow_auto_assembler.py", line 1050, in _run_func\n    output = func(inputs = inputs)\n  File "/tmp/ipykernel_9856/3259375930.py", line 11, in get_weather\n    error\nNameError: name \'error\' is not defined\n',
     'error_type': <WorkflowErrorType.RUNNER: 'runner'>,
     'additional_info': {'ffunction': 'get_weather'}}




```python
print(test_outputs2.error.error_message)
```

    Traceback (most recent call last):
      File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_auto_assembler/workflow_auto_assembler.py", line 1050, in _run_func
        output = func(inputs = inputs)
      File "/tmp/ipykernel_9856/3259375930.py", line 11, in get_weather
        error
    NameError: name 'error' is not defined
    


##### Function from workflow unavailable


```python
adapted_workflow_obj_b3_workflow = [{'id': 1,
'func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029a',
  'name': 'query_database_data',
  'args': {'topic': 'birds', 'location': '0.output.city'}},
 {'id': 2, 
 'func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a',
 'name': 'get_weather', 'args': {'city': '0.output.city'}},
 {'id': 3,
 'func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a',
  'name': 'send_report_email',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Birds Information', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}},
 {'id': '4',
 'func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f',
  'name': 'output_model',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Birds Information', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}}]
```


```python
wr3 = WorkflowRunner(
    output_comparer_h = oc,
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    available_callables = available_callables, 
    available_functions = available_functions,
    loggerLvl = logging.DEBUG)

test_outputs3 = wr3.run_workflow(
    workflow = adapted_workflow_obj_b3_workflow, 
    available_functions = available_functions,
    available_callables = available_callables,
    inputs = WfInputs(city = "Berlin"),
    output_model = WfOutputs)

test_outputs3.outputs
```




    {'0': WfInputs(city='Berlin')}




```python
test_outputs3.error.model_dump()
```




    {'error_message': 'Traceback (most recent call last):\n  File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_auto_assembler/workflow_auto_assembler.py", line 1194, in run_workflow\n    func_item = [av for av in available_functions \\\nIndexError: list index out of range\n',
     'error_type': <WorkflowErrorType.PLANNING_HF: 'planning_hf'>,
     'additional_info': {}}




```python
print(test_outputs3.error.error_message)
```

    Traceback (most recent call last):
      File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_auto_assembler/workflow_auto_assembler.py", line 1194, in run_workflow
        func_item = [av for av in available_functions \
    IndexError: list index out of range
    


##### Example output differs from expected one


```python
expected_output2 = WfOutputs(
    city='London', 
    information=[
        EmailInformationPoint(title='Birds Info', content='Content extracted from the database for your query is ...'), 
        EmailInformationPoint(title='Weather', content='Sunny')])

test_outputs4 = wr.run_workflow(
    workflow = adapted_workflow, 
    inputs = WfInputs(city = "Berlin"),
    expected_outputs = expected_output2,
    output_model = WfOutputs)
```


```python
test_outputs4.error.model_dump()
```




    {'error_message': 'Actual outputs do not match expected!',
     'error_type': <WorkflowErrorType.OUTPUTS_UNEXPECTED: 'outputs_unexpected'>,
     'additional_info': {'step_id': 4,
      'differences': [{'path': 'city',
        'source_key': 'city',
        'diff_type': 'value_mismatch',
        'expected': 'London',
        'actual': 'Berlin',
        'output': '0.output.city',
        'source_step_id': 0,
        'source': 'user_input'}]}}


