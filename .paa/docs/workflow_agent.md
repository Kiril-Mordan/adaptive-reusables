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


```python
from workflow_agent import WorkflowAgent, TestedWorkflow
import logging

wa = WorkflowAgent(
    available_functions = available_functions,
    available_callables = available_callables,
    llm_handler_params = {
        "llm_h_type" : "ollama",
        "llm_h_params" : {
            "connection_string": "http://localhost:11434",
            "model_name": "gpt-oss:20b"
        }
    },
    loggerLvl = logging.DEBUG
)
```


```python
task_description = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")

wf_obj = await wa.plan_workflow(
    task_description = task_description,
    input_model = WfInputs,
    output_model = WfOutputs,
    test_inputs = WfInputs(city = "Berlin")
)
```

    DEBUG:InputCollector:og_leaves : {'[0].args.topic': 'birds', '[0].args.location': 'source: input_model.output.city', '[1].args.city': 'source: input_model.output.city', '[2].args.city': 'source: input_model.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': 'source: query_database.output.info', '[2].args.information[1].title': 'Current Weather', '[2].args.information[1].content': 'source: get_weather.output.condition', '[3].args.city': 'source: input_model.output.city', '[3].args.information[0].title': 'Birds Information', '[3].args.information[0].content': 'source: query_database.output.info', '[3].args.information[1].title': 'Current Weather', '[3].args.information[1].content': 'source: get_weather.output.condition', '[4].id': '5'}
    DEBUG:InputCollector:mod_leaves : {'[0].id': '1', '[0].args.topic': 'birds', '[0].args.location': '0.output.city', '[1].id': '2', '[1].args.city': '0.output.city', '[2].id': '3', '[2].args.city': '0.output.city', '[2].args.information[0].title': 'Birds Information', '[2].args.information[0].content': '1.output.info', '[2].args.information[1].title': 'Current Weather', '[2].args.information[1].content': '2.output.condition', '[3].id': '4', '[3].args.city': '0.output.city', '[3].args.information[0].title': 'Birds Information', '[3].args.information[0].content': '1.output.info', '[3].args.information[1].title': 'Current Weather', '[3].args.information[1].content': '2.output.condition'}
    DEBUG:InputCollector:ic_results : ['literal', 'reference', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference', 'reference', 'literal', 'reference', 'literal', 'reference', 'literal']
    DEBUG:InputCollector:new_values : ['birds', '0.output.city', '0.output.city', '0.output.city', 'Birds Information', '1.output.info', 'Current Weather', '2.output.condition', '0.output.city', 'Birds Information', '1.output.info', 'Current Weather', '2.output.condition', '5']



```python
TestedWorkflow.model_fields
```




    {'workflow': FieldInfo(annotation=List[WorkflowItem], required=True),
     'outputs': FieldInfo(annotation=Dict[str, BaseModel], required=True),
     'error': FieldInfo(annotation=Union[WorkflowError, NoneType], required=True)}




```python
wf_obj['tested_wf_obj'].workflow
```




    [WorkflowItem(name='query_database', args={'topic': 'birds', 'location': '0.output.city'}),
     WorkflowItem(name='get_weather', args={'city': '0.output.city'}),
     WorkflowItem(name='send_report_email', args={'city': '0.output.city', 'information': [{'title': 'Birds Information', 'content': '1.output.info'}, {'title': 'Current Weather', 'content': '2.output.condition'}]}),
     WorkflowItem(name='output_model', args={'city': '0.output.city', 'information': [{'title': 'Birds Information', 'content': '1.output.info'}, {'title': 'Current Weather', 'content': '2.output.condition'}]})]




```python
wf_obj['tested_wf_obj'].outputs
```




    {'0': WfInputs(city='Berlin'),
     '1': QueryDatabaseOutput(info='Content extracted from the database for your query is ...', uid='0000'),
     '2': GetWeatherOutput(condition='Sunny', temperature=20.0, humidity=0.6),
     '3': SendReportEmailOutput(email_sent=True, message='Email sent to city of your choosing!'),
     '4': WfOutputs(city='Berlin', information=[EmailInformationPoint(title='Birds Information', content='Content extracted from the database for your query is ...'), EmailInformationPoint(title='Current Weather', content='Sunny')])}




```python
wf_obj['tested_wf_obj'].error
```
