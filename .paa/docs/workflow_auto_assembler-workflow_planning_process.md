```python
from workflow_agent import LlmHandler

llm_handler = LlmHandler(
    llm_h_type="ollama",
    llm_h_params={
        "connection_string": "http://localhost:11434",
        "model_name": "gpt-oss:20b" #"llama3.1:latest" # "gemma3:27b"
    }
)
```


```python
from workflow_agent import create_function_item

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

#### 0. Initialize Planner and Adaptor


```python
from workflow_agent import WorkflowPlanner
import logging

wp = WorkflowPlanner(
    llm_h = llm_handler,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)
```


```python
from workflow_agent import WorkflowAdaptor
from workflow_agent import InputCollector
import logging

wa = WorkflowAdaptor(
    llm_h = llm_handler, 
    input_collector_class = InputCollector,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)
```


```python
from workflow_agent import WorkflowRunner

wr = WorkflowRunner(
    available_callables = available_callables, 
    available_functions = available_functions)
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
        {'title': 'Weather Forecast',
         'content': 'source: get_weather.output.condition'}]}}]




```python
adapted_workflow_obj = await wa.adapt_workflow(
    workflow=planned_workflow_obj.workflow)

adapted_workflow_obj.workflow
```

    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[1].args.city': 'Berlin', '[2].args.city': 'Berlin', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Weather Forecast', '[2].args.information[1].content': 'source: get_weather.output.condition'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].args.topic': 'birds', '[1].id': '2', '[1].args.city': 'Berlin', '[2].id': '3', '[2].args.city': 'Berlin', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Weather Forecast', '[2].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'literal', 'literal', 'literal', 'reference', 'literal', 'reference']
    DEBUG:InputCollector:new_values : ['birds', 'Berlin', 'Berlin', 'Birds Information', '1.output.info', 'Weather Forecast', '2.output.condition']





    [{'id': 1, 'name': 'query_database', 'args': {'topic': 'birds'}},
     {'id': 2, 'name': 'get_weather', 'args': {'city': 'Berlin'}},
     {'id': 3,
      'name': 'send_report_email',
      'args': {'city': 'Berlin',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather Forecast', 'content': '2.output.condition'}]}}]



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




    [{'name': 'query_database',
      'args': {'topic': 'birds', 'location': 'source: WfInputs.city'}},
     {'name': 'get_weather', 'args': {'city': 'source: WfInputs.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source: WfInputs.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather Condition',
         'content': 'source: get_weather.output.condition'}]}}]




```python
adapted_workflow_obj_a = await wa.adapt_workflow(
    workflow=planned_workflow_obj_a.workflow, 
    input_model = WfInputs)

adapted_workflow_obj_a.workflow
```

    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[0].args.location': 'source: WfInputs.city', '[1].args.city': 'source: WfInputs.city', '[2].args.city': 'source: WfInputs.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Weather Condition', '[2].args.information[1].content': 'source: get_weather.output.condition'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].args.topic': 'birds', '[0].args.location': '0.output.city', '[1].id': '2', '[1].args.city': '0.output.city', '[2].id': '3', '[2].args.city': '0.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Weather Condition', '[2].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'reference', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference']
    DEBUG:InputCollector:new_values : ['birds', '0.output.city', '0.output.city', '0.output.city', 'Birds Information', '1.output.info', 'Weather Condition', '2.output.condition']





    [{'id': 1,
      'name': 'query_database',
      'args': {'topic': 'birds', 'location': '0.output.city'}},
     {'id': 2, 'name': 'get_weather', 'args': {'city': '0.output.city'}},
     {'id': 3,
      'name': 'send_report_email',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather Condition', 'content': '2.output.condition'}]}}]



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




    [{'name': 'query_database', 'args': {'topic': 'birds'}},
     {'name': 'get_weather', 'args': {'city': 'source: input_model.output.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather Information',
         'content': 'source: get_weather.output.condition'}]}},
     {'name': 'output_model', 'args': {}}]




```python
adapted_workflow_obj_b = await wa.adapt_workflow(
    workflow=planned_workflow_obj_b.workflow, 
    output_model = WfOutputs,
    input_model = WfInputs)

adapted_workflow_obj_b.workflow
```

    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[1].args.city': 'source: input_model.output.city', '[2].args.city': 'source: input_model.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Weather Information', '[2].args.information[1].content': 'source: get_weather.output.condition', '[4].id': '5'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].args.topic': 'birds', '[1].id': '2', '[1].args.city': '0.output.city', '[2].id': '3', '[2].args.city': '0.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Weather Information', '[2].args.information[1].content': '2.output.condition', '[3].id': '4', '[3].args.city': '0.output.city', '[3].args.information[0].title': 'Birds Information', '[3].args.information[0].content': '1.output.info', '[3].args.information[1].title': 'Weather Information', '[3].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference', 'literal']
    DEBUG:InputCollector:new_values : ['birds', '0.output.city', '0.output.city', 'Birds Information', '1.output.info', 'Weather Information', '2.output.condition', '5']





    [{'id': 1, 'name': 'query_database', 'args': {'topic': 'birds'}},
     {'id': 2, 'name': 'get_weather', 'args': {'city': '0.output.city'}},
     {'id': 3,
      'name': 'send_report_email',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather Information', 'content': '2.output.condition'}]}},
     {'id': 4,
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather Information', 'content': '2.output.condition'}]}}]




```python
adapted_workflow_obj_b.steps[2].errors
```




    []



#### 4. Testing generated workflow


```python
test_outputs = wr.run_workflow(
    workflow = adapted_workflow_obj_b.workflow, 
    inputs = WfInputs(city = "Berlin"),
    output_model = WfOutputs)

test_outputs.outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000'),
     '2': GetWeatherOutput(condition='Sunny', temperature=20.0, humidity=0.6),
     '3': SendReportEmailOutput(email_sent=True, message='Email sent to city of your choosing!'),
     '4': WfOutputs(city='Berlin', information=[EmailInformationPoint(title='Birds Information', content='Content extracted from the database for your query is ...'), EmailInformationPoint(title='Weather Information', content='Sunny')])}



##### Resetting based on runner


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
available_functions2 = [
    create_function_item(get_weather, GetWeatherInput, GetWeatherOutput),
    create_function_item(get_weather_report, GetWeatherInput, GetWeatherOutput),
    create_function_item(send_report_email, SendReportEmailInput, SendReportEmailOutput),
    create_function_item(query_database, QueryDatabaseInput, QueryDatabaseOutput)
]

available_callables2 = {
    "get_weather" : get_weather,
    "get_weather_report" : get_weather_report,
    "send_report_email" : send_report_email,
    "query_database" : query_database
}
```


```python
from workflow_agent import WorkflowPlanner

wr2 = WorkflowRunner(
    available_callables = available_functions2, 
    available_functions = available_callables2,
    loggerLvl = logging.DEBUG)

test_outputs2 = wr2.run_workflow(
    workflow = adapted_workflow_obj_b.workflow, 
    available_functions = available_functions2,
    available_callables = available_callables2,
    inputs = WfInputs(city = "Berlin"),
    output_model = WfOutputs)

test_outputs2.outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000')}




```python
planned_workflow_obj_b.model_dump()
```




    {'retries': 0,
     'workflow': [{'name': 'query_database', 'args': {'topic': 'birds'}},
      {'name': 'get_weather', 'args': {'city': 'source: input_model.output.city'}},
      {'name': 'send_report_email',
       'args': {'city': 'source: input_model.output.city',
        'information': [{'title': 'Birds Information',
          'content': 'source: query_database.output.info'},
         {'title': 'Weather Information',
          'content': 'source: get_weather.output.condition'}]}},
      {'name': 'output_model', 'args': {}}],
     'init_messages': [{'role': 'system',
       'content': '## Role\nYou are a Workflow Agent tasked with creating a complete workflow for a given task.  Your workflow must be constructed solely from calls to the functions provided. Each workflow should be represented as a JSON list, where each element is an object representing a single function call. For any function input that is meant to be filled using the output of a previous step rather than provided directly, indicate this using the format: "source: <previous_function_name>.output.<field_name>".\n\n## Output Requirements\n- **Respond ONLY with valid JSON** — specifically, an **array** of objects. - **Do NOT** provide any additional commentary, explanations, or text outside this JSON array. - Each object in the array must represent **one tool call**, with **exactly** the following fields:\n  1. `"name"` (string) - the tool\'s name from the list below.\n  2. `"args"` (object) - any arguments the tool requires.\n- **Important:** If a function argument is intended to be sourced from a previous step\'s output, indicate this using the format: "source: <previous_function_name>.output.<field_name>".\n  \n### Expected Format\n[\n  {\n    "name": "function_name_1",\n    "args": {}\n  },\n  ...,\n  {\n    "name": "function_name_n",\n    "args": {"arg1": "value for arg1"}\n  }\n]\n\n## Available functions\nBelow is the list of available functions that you can use to build your workflow. Each function is defined by its name, a description, and a JSON schema for its parameters. For example, the function list is as follows:\n[{"name": "get_weather", "description": "Get the current weather for a city from weather forcast api.", "input_schema_json": {"properties": {"city": {"description": "Name of the city for which weather to be extracted.", "title": "City", "type": "string"}}, "required": ["city"], "title": "GetWeatherInput", "type": "object"}, "output_schema_json": {"properties": {"condition": {"description": "Weather condition in the requested city.", "title": "Condition", "type": "string"}, "temperature": {"description": "Termperature in C in the requested city.", "title": "Temperature", "type": "number"}, "humidity": {"default": null, "description": "Name of the city for which weather to be extracted.", "title": "Humidity", "type": "number"}}, "required": ["condition", "temperature"], "title": "GetWeatherOutput", "type": "object"}}, {"name": "send_report_email", "description": "Sends a report email with given information points to a city.", "input_schema_json": {"$defs": {"EmailInformationPoint": {"properties": {"title": {"default": null, "description": "Few word description of the information.", "title": "Title", "type": "string"}, "content": {"description": "Content of the information.", "title": "Content", "type": "string"}}, "required": ["content"], "title": "EmailInformationPoint", "type": "object"}}, "properties": {"city": {"description": "Name of the city where report will be send.", "title": "City", "type": "string"}, "information": {"items": {"$ref": "#/$defs/EmailInformationPoint"}, "title": "Information", "type": "array"}}, "required": ["city", "information"], "title": "SendReportEmailInput", "type": "object"}, "output_schema_json": {"properties": {"email_sent": {"description": "Conformation that email was send successfully.", "title": "Email Sent", "type": "boolean"}, "message": {"default": null, "description": "Optional comments from the process.", "title": "Message", "type": "string"}}, "required": ["email_sent"], "title": "SendReportEmailOutput", "type": "object"}}, {"name": "query_database", "description": "Get information from the database with provided filters.", "input_schema_json": {"properties": {"topic": {"description": "Topic of a requested piece of information.", "title": "Topic", "type": "string"}, "location": {"default": null, "description": "Filter for location name.", "title": "Location", "type": "string"}, "uid": {"default": null, "description": "Filter for unique indentifier of the database item.", "title": "Uid", "type": "string"}}, "required": ["topic"], "title": "QueryDatabaseInput", "type": "object"}, "output_schema_json": {"properties": {"info": {"description": "Content of the information.", "title": "Info", "type": "string"}, "uid": {"default": null, "description": "Unique indentifier of the database item.", "title": "Uid", "type": "string"}}, "required": ["info"], "title": "QueryDatabaseOutput", "type": "object"}}]\n\n'},
      {'role': 'user',
       'content': 'Query database to find information on birds and get latest weather for the city, then send an email there.\n--- The following is the expected input model for the workflow, reference values from it if necessesary, given the task with  format "source: input_model.output.<field_name>". \n{\'properties\': {\'city\': {\'description\': \'Name of the city for which weather to be extracted.\', \'title\': \'City\', \'type\': \'string\'}}, \'required\': [\'city\'], \'title\': \'WfInputs\', \'type\': \'object\'}\n---\n\n--- The following is the expected output model for the workflow, which should be included as additional workflow step named \'output_model\'.  Outputs from functions selected in the workflow should be able to populate its fields,  given the task with format "source: <previous_workflow_step>.output.<field_name>" or "source: input_model.output.<field_name>". \n{\'$defs\': {\'EmailInformationPoint\': {\'properties\': {\'title\': {\'default\': None, \'description\': \'Few word description of the information.\', \'title\': \'Title\', \'type\': \'string\'}, \'content\': {\'description\': \'Content of the information.\', \'title\': \'Content\', \'type\': \'string\'}}, \'required\': [\'content\'], \'title\': \'EmailInformationPoint\', \'type\': \'object\'}}, \'properties\': {\'city\': {\'description\': \'Name of the city for which weather was extracted.\', \'title\': \'City\', \'type\': \'string\'}, \'information\': {\'default\': [], \'description\': \'Information sent via email.\', \'items\': {\'$ref\': \'#/$defs/EmailInformationPoint\'}, \'title\': \'Information\', \'type\': \'array\'}}, \'required\': [\'city\'], \'title\': \'WfOutputs\', \'type\': \'object\'}\n---\n\n'}],
     'errors': [],
     'include_input': True,
     'include_output': True}




```python
test_outputs2.error.model_dump()
```




    {'error_message': 'Traceback (most recent call last):\n  File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_agent/workflow_agent.py", line 539, in _run_func\n    output = func(inputs = inputs)\n  File "/tmp/ipykernel_13361/3203537686.py", line 11, in get_weather\n    error\nNameError: name \'error\' is not defined\n',
     'error_type': <WorkflowErrorType.RUNNER: 'runner'>,
     'additional_info': {'ffunction': 'get_weather'}}




```python
print(test_outputs2.error.error_message)
```

    Traceback (most recent call last):
      File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_agent/workflow_agent.py", line 539, in _run_func
        output = func(inputs = inputs)
      File "/tmp/ipykernel_13361/3203537686.py", line 11, in get_weather
        error
    NameError: name 'error' is not defined
    



```python
test_outputs2.error.error_type
```




    <WorkflowErrorType.RUNNER: 'runner'>




```python
from workflow_agent import WorkflowPlanner
from workflow_agent import WorkflowAdaptor
from workflow_agent import InputCollector
import logging

wp2 = WorkflowPlanner(
    llm_h = llm_handler,
    available_functions=available_functions2,
    loggerLvl = logging.DEBUG)

wa2 = WorkflowAdaptor(
    llm_h = llm_handler, 
    input_collector_class = InputCollector,
    available_functions=available_functions2,
    loggerLvl = logging.DEBUG)

```


```python
planned_workflow_obj_b.errors.append(test_outputs2.error)

planned_workflow_obj_tb = await wp2.generate_workflow(planned_workflow = planned_workflow_obj_b)
```

    DEBUG:WorkflowPlanner:Attempt: 1



```python
planned_workflow_obj_tb.workflow
```




    [{'name': 'query_database', 'args': {'topic': 'birds'}},
     {'name': 'get_weather_report',
      'args': {'city': 'source:input_model.output.city'}},
     {'name': 'send_report_email',
      'args': {'city': 'source:input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source:query_database.output.info'},
        {'title': 'Weather Information',
         'content': 'source:get_weather_report.output.report'}]}},
     {'name': 'output_model', 'args': {}}]



##### Resetting based on hallusinated function


```python
adapted_workflow_obj_b3_workflow = [{'id': 1,
  'name': 'query_database_data',
  'args': {'topic': 'birds', 'location': '0.output.city'}},
 {'id': 2, 'name': 'get_weather', 'args': {'city': '0.output.city'}},
 {'id': 3,
  'name': 'send_report_email',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Birds Information', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}},
 {'id': '4',
  'name': 'output_model',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Birds Information', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}}]
```


```python
from workflow_agent import WorkflowPlannerResponse
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
from workflow_agent import WorkflowPlanner

wr3 = WorkflowRunner(
    available_callables = available_functions, 
    available_functions = available_callables,
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




    {'error_message': 'Traceback (most recent call last):\n  File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_agent/workflow_agent.py", line 677, in run_workflow\n    func_item = [av for av in available_functions \\\nIndexError: list index out of range\n',
     'error_type': <WorkflowErrorType.PLANNING_HF: 'planning_hf'>,
     'additional_info': {}}




```python
print(test_outputs3.error.error_message)
```

    Traceback (most recent call last):
      File "/home/kyriosskia/miniforge3/envs/testenv/lib/python3.10/site-packages/workflow_agent/workflow_agent.py", line 677, in run_workflow
        func_item = [av for av in available_functions \
    IndexError: list index out of range
    



```python
test_outputs3.error.error_type
```




    <WorkflowErrorType.PLANNING_HF: 'planning_hf'>




```python
from workflow_agent import WorkflowPlanner
from workflow_agent import WorkflowAdaptor
from workflow_agent import InputCollector
import logging

wp3 = WorkflowPlanner(
    llm_h = llm_handler,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)

wa3 = WorkflowAdaptor(
    llm_h = llm_handler, 
    input_collector_class = InputCollector,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)

```


```python
planned_workflow_obj_b3.errors.append(test_outputs3.error)

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
     {'name': 'output_model', 'args': {}}]



##### Resetting adaptor

WorkflowErrorType.ADAPTOR_JSON


```python
from workflow_agent import WorkflowErrorType, WorkflowError

adapted_workflow_obj_b4 = adapted_workflow_obj_b.model_copy()
```


```python
adapted_workflow_obj_b4.workflow = [{'id': 1, 'name': 'query_database', 'args': {'topic': 'birds'}},
 {'id': 2, 'name': 'get_weather', 'args': {'city': '0.output.information'}},
 {'id': 3,
  'name': 'send_report_email',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Bird Information', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}},
 {'id': 4,
  'name': 'output_model',
  'args': {'city': '0.output.city',
   'information': [{'title': 'Bird Information', 'content': '1.output.info'},
    {'title': 'Weather', 'content': '2.output.condition'}]}}]

adapted_workflow_obj_b4.all_errors.append(
    WorkflowError(
        error_message = None,
        error_type = WorkflowErrorType.ADAPTOR_JSON,
        additional_info = {
            "step_id" : 2,
            "error_messages" : ["Mapping for key 'information' is invalid."]}
    ))
```


```python
adapted_workflow_obj_b4_reset = await wa3.adapt_workflow(
    adapted_workflow = adapted_workflow_obj_b4,
)
```


```python
adapted_workflow_obj_b4_reset.workflow
```




    [{'id': 1, 'name': 'query_database', 'args': {'topic': 'birds'}},
     {'id': 2, 'name': 'get_weather', 'args': {'city': '0.output.city'}},
     {'id': 3,
      'name': 'send_report_email',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Bird Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}},
     {'id': 4,
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Bird Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}}]




```python
adapted_workflow_obj_b4_reset.planned_workflow
```




    [{'id': 0, 'name': 'input_model'},
     {'id': 1, 'name': 'query_database', 'args': {'topic': 'birds'}},
     {'id': 2,
      'name': 'get_weather',
      'args': {'city': 'source: input_model.output.city'}},
     {'id': 3,
      'name': 'send_report_email',
      'args': {'city': 'source: input_model.output.city',
       'information': [{'title': 'Birds Information',
         'content': 'source: query_database.output.info'},
        {'title': 'Weather Information',
         'content': 'source: get_weather.output.condition'}]}},
     {'id': 4, 'name': 'output_model', 'args': {}}]


