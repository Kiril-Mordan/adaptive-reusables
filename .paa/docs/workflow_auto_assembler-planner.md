```python
from workflow_auto_assembler import LlmHandler

llm_handler = LlmHandler(
    llm_h_type="ollama",
    llm_h_params={
        "connection_string": "http://localhost:11434",
        "model_name": "gpt-oss:20b"
    }
)
```


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

#### 0. Initialize Planner


```python
from workflow_auto_assembler import WorkflowPlanner, WorkflowErrorType, WorkflowError
import logging

wp = WorkflowPlanner(
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    llm_h = llm_handler,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)
```

#### 1. Generating simple workflow using available functions (no input or output model)


```python
task_description = """Query database to find information on birds and get latest weather for Berlin, then send an email there."""

planned_workflow_obj = await wp.generate_workflow(
    task_description=task_description)

planned_workflow_obj.workflow
```




    [{'name': 'query_database', 'args': {'topic': 'birds'}},
     {'name': 'get_weather', 'args': {'city': 'Berlin'}},
     {'name': 'send_report_email',
      'args': {'city': 'Berlin',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather Condition',
         'content': 'source: get_weather.output.condition'}]}}]



#### 2. Generating simple workflow using available functions (no output model)


```python
task_description_a = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

planned_workflow_obj_a = await wp.generate_workflow(
    input_model = WfInputs,
    task_description=task_description_a)

planned_workflow_obj_a.workflow
```




    [{'name': 'query_database', 'args': {'topic': 'birds'}},
     {'name': 'get_weather', 'args': {'city': 'source: input_model.output.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Bird Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather Condition',
         'content': 'source: get_weather.output.condition'}]}}]



#### 3. Generating simple workflow using available functions


```python
task_description_b = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")

planned_workflow_obj_b = await wp.generate_workflow(
    input_model = WfInputs,
    output_model = WfOutputs,
    task_description=task_description_b)

planned_workflow_obj_b.workflow
```




    [{'name': 'query_database',
      'args': {'topic': 'birds', 'location': 'source: input_model.output.city'}},
     {'name': 'get_weather', 'args': {'city': 'source: input_model.output.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather', 'content': 'source: get_weather.output.condition'}]}},
     {'name': 'output_model',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather', 'content': 'source: get_weather.output.condition'}]}}]



#### Resetting errors uncovered post planning


```python
from workflow_auto_assembler import WorkflowError, WorkflowErrorType
```

##### Resetting based on runner error


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

def get_weather_report(inputs: GetWeatherInput) -> GetWeatherOutput:
    """Get the current weather for a city from weather forcast api (Improved)."""
    return GetWeatherOutput(
        condition = "Sunny",
        temperature = 20,
        humidity = 0.6
    )
```


```python
# Create structured items for each function

available_tools2 = create_avc_items(functions = [
    LlmFunctionItemInput(**{"func" : get_weather , "input_model" : GetWeatherInput, "output_model" : GetWeatherOutput}),
    LlmFunctionItemInput(**{"func" : send_report_email , "input_model" : SendReportEmailInput, "output_model" : SendReportEmailOutput}),
    LlmFunctionItemInput(**{"func" : query_database , "input_model" : QueryDatabaseInput, "output_model" : QueryDatabaseOutput}),
     LlmFunctionItemInput(**{"func" : get_weather_report , "input_model" : GetWeatherInput, "output_model" : GetWeatherOutput})
])

available_functions2 = available_tools2["available_functions"]

available_callables2 = available_tools2["available_callables"]
```


```python
runner_error = WorkflowError(
    error_message = 'Traceback (most recent call last):\n  File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_auto_assembler/workflow_auto_assembler.py", line 780, in run_workflow\n    func_item = [av for av in available_functions \\\nIndexError: list index out of range\n',
    error_type = WorkflowErrorType.RUNNER,
    additional_info = {
        "ffunction" : "get_weather"
    }
)
```


```python
import logging

wp2 = WorkflowPlanner(
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    llm_h = llm_handler,
    available_functions=available_functions2,
    loggerLvl = logging.DEBUG)

planned_workflow_obj_b.errors.append(runner_error)

planned_workflow_obj_tb = await wp2.generate_workflow(planned_workflow = planned_workflow_obj_b)

```

    DEBUG:WorkflowPlanner:Attempt: 1



```python
planned_workflow_obj_tb.workflow
```




    [{'name': 'query_database',
      'args': {'topic': 'birds', 'location': 'source: input_model.output.city'}},
     {'name': 'get_weather_report',
      'args': {'city': 'source: input_model.output.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather',
         'content': 'source: get_weather_report.output.condition'}]}},
     {'name': 'output_model',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather',
         'content': 'source: get_weather_report.output.condition'}]}}]



##### Resetting based on hallusinated function


```python
from workflow_auto_assembler import WorkflowPlannerResponse
```


```python
planned_workflow_obj_b3 = WorkflowPlannerResponse(
    **{'include_output' :True ,
    'include_input' : True,
    'retries': 0,
 'workflow': [{'name': 'query_database_data', 'args': {'topic': 'birds'}},
  {'name': 'get_weather', 'args': {'city': 'source: WfInputs.output.city'}},
  {'name': 'send_report_email',
   'args': {'city': 'source: WfInputs.output.city',
    'information': [{'title': 'Weather Condition',
      'content': 'source: get_weather.output.condition'},
     {'title': 'Temperature',
      'content': 'source: get_weather.output.temperature'},
     {'title': 'Birds Info',
      'content': 'source: query_database_data.output.info'}]}}],
 'init_messages': [{'role': 'system',
   'content': '## Role\nYou are a Workflow Agent tasked with creating a complete workflow for a given task.  Your workflow must be constructed solely from calls to the functions provided. Each workflow should be represented as a JSON list, where each element is an object representing a single function call. For any function input that is meant to be filled using the output of a previous step rather than provided directly, indicate this using the format: "source: <previous_function_name>.output.<field_name>".\n\n## Output Requirements\n- **Respond ONLY with valid JSON** — specifically, an **array** of objects. - **Do NOT** provide any additional commentary, explanations, or text outside this JSON array. - Each object in the array must represent **one tool call**, with **exactly** the following fields:\n  1. `"name"` (string) - the tool\'s name from the list below.\n  2. `"args"` (object) - any arguments the tool requires.\n- **Important:** If a function argument is intended to be sourced from a previous step\'s output, indicate this using the format: "source: <previous_function_name>.output.<field_name>".\n  \n### Expected Format\n[\n  {\n    "name": "function_name_1",\n    "args": {}\n  },\n  ...,\n  {\n    "name": "function_name_n",\n    "args": {"arg1": "value for arg1"}\n  }\n]\n\n## Available functions\nBelow is the list of available functions that you can use to build your workflow. Each function is defined by its name, a description, and a JSON schema for its parameters. For example, the function list is as follows:\n[{"name": "get_weather", "description": "Get the current weather for a city from weather forcast api.", "input_schema_json": {"properties": {"city": {"description": "Name of the city for which weather to be extracted.", "title": "City", "type": "string"}}, "required": ["city"], "title": "GetWeatherInput", "type": "object"}, "output_schema_json": {"properties": {"condition": {"description": "Weather condition in the requested city.", "title": "Condition", "type": "string"}, "temperature": {"description": "Termperature in C in the requested city.", "title": "Temperature", "type": "number"}, "humidity": {"default": null, "description": "Name of the city for which weather to be extracted.", "title": "Humidity", "type": "number"}}, "required": ["condition", "temperature"], "title": "GetWeatherOutput", "type": "object"}}, {"name": "send_report_email", "description": "Sends a report email with given information points to a city.", "input_schema_json": {"$defs": {"EmailInformationPoint": {"properties": {"title": {"default": null, "description": "Few word description of the information.", "title": "Title", "type": "string"}, "content": {"description": "Content of the information.", "title": "Content", "type": "string"}}, "required": ["content"], "title": "EmailInformationPoint", "type": "object"}}, "properties": {"city": {"description": "Name of the city where report will be send.", "title": "City", "type": "string"}, "information": {"items": {"$ref": "#/$defs/EmailInformationPoint"}, "title": "Information", "type": "array"}}, "required": ["city", "information"], "title": "SendReportEmailInput", "type": "object"}, "output_schema_json": {"properties": {"email_sent": {"description": "Conformation that email was send successfully.", "title": "Email Sent", "type": "boolean"}, "message": {"default": null, "description": "Optional comments from the process.", "title": "Message", "type": "string"}}, "required": ["email_sent"], "title": "SendReportEmailOutput", "type": "object"}}, {"name": "query_database", "description": "Get information from the database with provided filters.", "input_schema_json": {"properties": {"topic": {"description": "Topic of a requested piece of information.", "title": "Topic", "type": "string"}, "location": {"default": null, "description": "Filter for location name.", "title": "Location", "type": "string"}, "uid": {"default": null, "description": "Filter for unique indentifier of the database item.", "title": "Uid", "type": "string"}}, "required": ["topic"], "title": "QueryDatabaseInput", "type": "object"}, "output_schema_json": {"properties": {"info": {"description": "Content of the information.", "title": "Info", "type": "string"}, "uid": {"default": null, "description": "Unique indentifier of the database item.", "title": "Uid", "type": "string"}}, "required": ["info"], "title": "QueryDatabaseOutput", "type": "object"}}]\n\n'},
  {'role': 'user',
   'content': 'Query database to find information on birds and get latest weather for the city, then send an email there.\n--- The following is the expected input model for the workflow, reference values from it if necessesary, given the task with  format "source: input_model.output.<field_name>". \n{\'properties\': {\'city\': {\'description\': \'Name of the city for which weather to be extracted.\', \'title\': \'City\', \'type\': \'string\'}}, \'required\': [\'city\'], \'title\': \'WfInputs\', \'type\': \'object\'}\n---\n\n--- The following is the expected output model for the workflow, outputs from functions selected in the workflow should  be able to populate its fields, given the task with format "source: <previous_workflow_step>.output.<field_name>" or "source: input_model.output.<field_name>". \n{\'$defs\': {\'EmailInformationPoint\': {\'properties\': {\'title\': {\'default\': None, \'description\': \'Few word description of the information.\', \'title\': \'Title\', \'type\': \'string\'}, \'content\': {\'description\': \'Content of the information.\', \'title\': \'Content\', \'type\': \'string\'}}, \'required\': [\'content\'], \'title\': \'EmailInformationPoint\', \'type\': \'object\'}}, \'properties\': {\'city\': {\'description\': \'Name of the city for which weather was extracted.\', \'title\': \'City\', \'type\': \'string\'}, \'information\': {\'default\': [], \'description\': \'Information sent via email.\', \'items\': {\'$ref\': \'#/$defs/EmailInformationPoint\'}, \'title\': \'Information\', \'type\': \'array\'}}, \'required\': [\'city\'], \'title\': \'WfOutputs\', \'type\': \'object\'}\n---\n\n'}],
 'errors': []}
)
```


```python
planning_error = WorkflowError(
    error_message = 'Traceback (most recent call last):\n  File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_auto_assembler/workflow_auto_assembler.py", line 780, in run_workflow\n    func_item = [av for av in available_functions \\\nIndexError: list index out of range\n',
    error_type = WorkflowErrorType.PLANNING_HF,
)
```


```python
import logging

wp3 = WorkflowPlanner(
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    llm_h = llm_handler,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)


planned_workflow_obj_b3.errors.append(planning_error)

planned_workflow_obj_tb3 = await wp3.generate_workflow(planned_workflow = planned_workflow_obj_b3)
```

    DEBUG:WorkflowPlanner:Attempt: 1
    DEBUG:WorkflowPlanner:Attempt: 2



```python
planned_workflow_obj_tb3.workflow
```




    [{'name': 'query_database', 'args': {'topic': 'birds'}},
     {'name': 'get_weather', 'args': {'city': 'source: WfInputs.output.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source: WfInputs.output.city',
       'information': [{'title': 'Weather Condition',
         'content': 'source: get_weather.output.condition'},
        {'title': 'Temperature',
         'content': 'source: get_weather.output.temperature'},
        {'title': 'Birds Info',
         'content': 'source: query_database.output.info'}]}},
     {'name': 'output_model',
      'args': {'city': 'source: WfInputs.output.city',
       'information': [{'title': 'Weather Condition',
         'content': 'source: get_weather.output.condition'},
        {'title': 'Temperature',
         'content': 'source: get_weather.output.temperature'},
        {'title': 'Birds Info',
         'content': 'source: query_database.output.info'}]}}]


