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

#### 0. Initialize Planner and Adaptor


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


```python
from workflow_auto_assembler import WorkflowAdaptor
from workflow_auto_assembler import InputCollector
import logging

wa = WorkflowAdaptor(
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    llm_h = llm_handler, 
    input_collector_class = InputCollector,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)
```

#### 1. Generating simple workflow using available functions (no input or output model)


```python
planned_workflow = [{'name': 'query_database', 'args': {'topic': 'birds'}},
 {'name': 'get_weather', 'args': {'city': 'Berlin'}},
 {'name': 'send_report_email',
  'args': {'city': 'Berlin',
   'information': [{'title': 'Birds Information',
     'content': 'source: query_database.output.info'},
    {'title': 'Current Weather Condition',
     'content': 'source: get_weather.output.condition'},
    {'title': 'Temperature (C)',
     'content': 'source: get_weather.output.temperature'}]}}]
```


```python
adapted_workflow_obj = await wa.adapt_workflow(
    workflow=planned_workflow)

adapted_workflow_obj.workflow
```

    DEBUG:WorkflowAdaptor:Adapting all steps!
    DEBUG:WorkflowAdaptor:Reset caused by ADAPTOR_JSON type error!
    DEBUG:WorkflowAdaptor:Attempt for send_report_email: 1
    DEBUG:WorkflowAdaptor:Reset caused by ADAPTOR_JSON type error!
    DEBUG:WorkflowAdaptor:Attempt for send_report_email: 2
    DEBUG:WorkflowAdaptor:Reset caused by ADAPTOR_JSON type error!
    DEBUG:WorkflowAdaptor:Attempt for send_report_email: 3
    DEBUG:WorkflowAdaptor:All steps were initially adapted!
    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[1].args.city': 'Berlin', '[2].args.city': 'Berlin', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Current Weather Condition', '[2].args.information[1].content': 'source: get_weather.output.condition', '[2].args.information[2].title': 'Temperature (C)', '[2].args.information[2].content': 'source: get_weather.output.temperature'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac', '[0].args.topic': 'birds', '[1].id': '2', '[1].func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a', '[1].args.city': 'Berlin', '[2].id': '3', '[2].func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a', '[2].args.city': 'Berlin', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Current Weather Condition', '[2].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'literal', 'literal', 'literal', 'reference', 'literal', 'reference', 'literal', 'reference']
    DEBUG:InputCollector:new_values : ['birds', 'Berlin', 'Berlin', 'Birds Information', '1.output.info', 'Current Weather Condition', '2.output.condition', 'Temperature (C)', None]





    [{'id': 1,
      'func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac',
      'name': 'query_database',
      'args': {'topic': 'birds'}},
     {'id': 2,
      'func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a',
      'name': 'get_weather',
      'args': {'city': 'Berlin'}},
     {'id': 3,
      'func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a',
      'name': 'send_report_email',
      'args': {'city': 'Berlin',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Current Weather Condition', 'content': '2.output.condition'}]}}]



#### 2. Generating simple workflow using available functions (no output model)


```python
class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

planned_workflow_a = [{'name': 'query_database', 'args': {'topic': 'birds'}},
 {'name': 'get_weather', 'args': {'city': 'source: input_model.output.city'}},
 {'name': 'send_report_email',
  'args': {'city': 'source: input_model.output.city',
   'information': [{'title': 'Birds Information',
     'content': 'source: query_database.output.info'},
    {'title': 'Weather', 'content': 'source: get_weather.output.condition'}]}}]
```


```python
adapted_workflow_obj_a = await wa.adapt_workflow(
    workflow=planned_workflow_a, 
    input_model = WfInputs)

adapted_workflow_obj_a.workflow
```

    DEBUG:WorkflowAdaptor:Adapting all steps!
    DEBUG:WorkflowAdaptor:All steps were initially adapted!
    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[1].args.city': 'source: input_model.output.city', '[2].args.city': 'source: input_model.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Weather', '[2].args.information[1].content': 'source: get_weather.output.condition'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac', '[0].args.topic': 'birds', '[1].id': '2', '[1].func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a', '[1].args.city': '0.output.city', '[2].id': '3', '[2].func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a', '[2].args.city': '0.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Weather', '[2].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference']
    DEBUG:InputCollector:new_values : ['birds', '0.output.city', '0.output.city', 'Birds Information', '1.output.info', 'Weather', '2.output.condition']





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
        {'title': 'Weather', 'content': '2.output.condition'}]}}]



#### 3. Generating simple workflow using available functions


```python
class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")

planned_workflow_b = [{'name': 'query_database', 'args': {'topic': 'birds'}},
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
```


```python
adapted_workflow_obj_b = await wa.adapt_workflow(
    workflow=planned_workflow_b, 
    output_model = WfOutputs,
    input_model = WfInputs)

adapted_workflow_obj_b.workflow
```

    DEBUG:WorkflowAdaptor:Adapting all steps!
    DEBUG:WorkflowAdaptor:All steps were initially adapted!
    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[1].args.city': 'source: input_model.output.city', '[2].args.city': 'source: input_model.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Weather', '[2].args.information[1].content': 'source: get_weather.output.condition', '[3].args.city': 'source: input_model.output.city', '[3].args.information[0].title': 'Birds Information', '[3].args.information[0].content': 'source: query_database.output.info', '[3].args.information[1].title': 'Weather', '[3].args.information[1].content': 'source: get_weather.output.condition', '[4].id': '5'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac', '[0].args.topic': 'birds', '[1].id': '2', '[1].func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a', '[1].args.city': '0.output.city', '[2].id': '3', '[2].func_id': '0e2e920002a93f313712e76199c5a1374ecdb59cab74d1a3d1580854c8b60b9a', '[2].args.city': '0.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Weather', '[2].args.information[1].content': '2.output.condition', '[3].id': '4', '[3].func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f', '[3].args.city': '0.output.city', '[3].args.information[0].title': 'Birds Information', '[3].args.information[0].content': '1.output.info', '[3].args.information[1].title': 'Weather', '[3].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference', 'literal']
    DEBUG:InputCollector:new_values : ['birds', '0.output.city', '0.output.city', 'Birds Information', '1.output.info', 'Weather', '2.output.condition', '0.output.city', 'Birds Information', '1.output.info', 'Weather', '2.output.condition', '5']





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
        {'title': 'Weather', 'content': '2.output.condition'}]}},
     {'id': 4,
      'func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f',
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Birds Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}}]



#### Resetting errors uncovered post adapting

##### Resetting adaptor


```python
from workflow_auto_assembler import WorkflowErrorType, WorkflowError

adapted_workflow_obj_b4 = adapted_workflow_obj_b.model_copy()
```


```python
adapted_workflow_obj_b4.workflow = [{'id': 1, 
'func_id': '7dcdbc070e6f7634effda970c2c0490e368f56b98a10c1a404d662ea176029ac',
'name': 'query_database', 'args': {'topic': 'birds'}},
 {'id': 2, 
 'func_id': '5f1173f2ce5662c1502e33d637c0b45efa42576300eea222a130ee3169089b4a',
 'name': 'get_weather', 'args': {'city': '0.output.information'}},
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
adapted_workflow_obj_b4_reset = await wa.adapt_workflow(
    adapted_workflow = adapted_workflow_obj_b4,
)
```

    DEBUG:WorkflowAdaptor:Reset caused by ADAPTOR_JSON type error!
    DEBUG:WorkflowAdaptor:Reset caused by ADAPTOR_JSON type error!
    DEBUG:WorkflowAdaptor:Attempt for get_weather: 1



```python
adapted_workflow_obj_b4_reset.workflow
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
       'information': [{'title': 'Bird Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}},
     {'id': 4,
      'func_id': '16a96f6083291385531909618374913abd08df9c4b3bbe0ac81969ae7856887f',
      'name': 'output_model',
      'args': {'city': '0.output.city',
       'information': [{'title': 'Bird Information', 'content': '1.output.info'},
        {'title': 'Weather', 'content': '2.output.condition'}]}}]


