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

#### 0. Initialize Workflow Check


```python
from workflow_auto_assembler import WorkflowCheck, WorkflowErrorType, WorkflowError
import logging

wc = WorkflowCheck(
    workflow_error = WorkflowError,
    workflow_error_types = WorkflowErrorType,
    llm_h = llm_handler,
    available_functions=available_functions,
    loggerLvl = logging.DEBUG)
```

#### 1. Check simple workflow using available functions (no input or output model)


```python
task_description = """Query database to find information on birds and get latest weather for Berlin, then send an email there."""

checked_workflow_obj = await wc.check_workflow(
    task_description=task_description)

```


```python
checked_workflow_obj.workflow_possible
```




    True




```python
print(checked_workflow_obj.justification)
```

    The task can be accomplished by chaining the available tools: use query_database with topic "birds" to retrieve bird information, call get_weather with city "Berlin" for weather data, and finally use send_report_email to send both pieces of information to Berlin. Each function is provided and can be combined in a sequential workflow.


#### 2. Check simple workflow using available functions (no output model)


```python
task_description_a = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

checked_workflow_obj_obj_a = await wc.check_workflow(
    input_model = WfInputs,
    task_description=task_description_a)
```


```python
checked_workflow_obj.workflow_possible
```




    True




```python
print(checked_workflow_obj.justification)
```

    The task can be accomplished by chaining the available tools: use query_database with topic "birds" to retrieve bird information, call get_weather with city "Berlin" for weather data, and finally use send_report_email to send both pieces of information to Berlin. Each function is provided and can be combined in a sequential workflow.


#### 3. Check simple workflow using available functions


```python
task_description_b = """Query database to find information on birds and get latest weather for the city, then send an email there."""

class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather was extracted.")
    information: list[EmailInformationPoint] = Field(default=[], description="Information sent via email.")

checked_workflow_obj_b = await wc.check_workflow(
    input_model = WfInputs,
    output_model = WfOutputs,
    task_description=task_description_b)
```


```python
checked_workflow_obj.workflow_possible
```




    True




```python
print(checked_workflow_obj.justification)
```

    The task can be accomplished by chaining the available tools: use query_database with topic "birds" to retrieve bird information, call get_weather with city "Berlin" for weather data, and finally use send_report_email to send both pieces of information to Berlin. Each function is provided and can be combined in a sequential workflow.

