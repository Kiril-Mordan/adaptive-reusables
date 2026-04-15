Currently intended usage pattern for `llm_function`:

- define typed tools
- mark them with `llm_function_tools`
- pass them into `llm_function` through a tool source
- bundle runtime settings and tools into config
- call the decorated function like a normal Python function



```python
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel, Field
from typing import Type, List, Optional

from llm_function_tools import llm_tool
from llm_function import InMemoryToolSource, PythonFileToolSource, LlmFunctionConfig, LlmFunctionRuntime, LlmRuntimeConfig, llm_function

```

## Define available tools

The runtime can assemble workflows only from tools you expose through tool sources. Tools can be defined directly in the current notebook or kept in a separate `.py` file.



```python
class GetWeatherInput(BaseModel):
    city: str = Field(..., description="City name.")


class GetWeatherOutput(BaseModel):
    forecast: str = Field(..., description="Weather forecast for the city.")


@llm_tool(tags=["weather"])
def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
    """Get current weather for a city."""
    return GetWeatherOutput(forecast=f"Sunny in {inputs.city}")


class EmailInformationPoint(BaseModel):
    title: str = Field(None, description="Few word description of the information.")
    content: str = Field(..., description="Content of the information.")

class SendReportEmailInput(BaseModel):
    city: str = Field(..., description="Name of the city where report will be send.")
    information: list[EmailInformationPoint]

class SendReportEmailOutput(BaseModel):
    email_sent: bool = Field(..., description="Conformation that email was send successfully.")
    message: str = Field(None, description="Optional comments from the process.")

@llm_tool(tags=["email"])
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

class QueryDatabaseInput(BaseModel):
    topic: str = Field(..., description="Topic of a requested piece of information.")
    location: str = Field(..., description="Filter for location name.")
    uid: str = Field(None, description="Filter for unique indentifier of the database item.")

class QueryDatabaseOutput(BaseModel):
    info: str = Field(..., description="Content of the information.")
    uid: str = Field(None, description="Unique indentifier of the database item.")

@llm_tool(tags=["database"])
def query_database(inputs : QueryDatabaseInput) -> QueryDatabaseOutput:
    """Get information from the database with provided filters."""
    return QueryDatabaseOutput(
        info = f"Content extracted from the database for {inputs.topic} in {inputs.location} is ...",
        uid = "0000"
    )

class QueryWebInput(BaseModel):
    search_input: str = Field(..., description="Topic to be searched on the web.")


class QueryWebOutput(BaseModel):
    search_results: List[str] = Field(..., description="List relevant info from search results.")

@llm_tool(tags=["web"])
def query_web(inputs : QueryWebInput) -> QueryWebOutput:
    """Get information from the internet for provided query."""
    return QueryWebOutput(
        search_results = ["Relevant content found in first search result is ..."],
    )


tool_sources = [InMemoryToolSource([get_weather, send_report_email, query_database, query_web])]

```

You can also keep tools in a separate `.py` file and load them with `PythonFileToolSource`:



```python
tmp_dir = TemporaryDirectory()
tool_file = Path(tmp_dir.name) / "weather_tools.py"

tool_file.write_text(
    """
from pydantic import BaseModel, Field
from llm_function_tools import llm_tool


class GetWeatherInput(BaseModel):
    city: str = Field(..., description='City name.')


class GetWeatherOutput(BaseModel):
    forecast: str = Field(..., description='Weather forecast for the city.')


@llm_tool(tags=['weather'])
def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
    '''Get current weather for a city.'''
    return GetWeatherOutput(forecast=f'Sunny in {inputs.city}')
""".strip()
)

file_tool_sources = [PythonFileToolSource(str(tool_file))]
file_tool_sources

```




    [PythonFileToolSource(file_path='/tmp/tmpg4e3db4r/weather_tools.py', include_plain_typed=False, location_type='local', package_name=None, package_version=None, module_name=None, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')]



## Create reusable config

Bundle runtime settings and tool sources once, then reuse that config across multiple decorated functions.



```python
runtime_config = LlmRuntimeConfig(
    llm_handler_params={
        "llm_h_type": "ollama",
        "llm_h_params": {
            "connection_string": "http://localhost:11434",
            "model_name": "gpt-oss:20b",
        },
    },
    storage_path="/tmp",
)

llm_config = LlmFunctionConfig(
    runtime=runtime_config,
    tool_sources=tool_sources,
)

llm_config

```




    LlmFunctionConfig(runtime=LlmRuntimeConfig(llm_handler_params={'llm_h_type': 'ollama', 'llm_h_params': {'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}}, storage_path='/tmp', force_replan=False, max_retry=None, reset_loops=None, compare_params=None, test_params=None), tool_sources=[InMemoryToolSource(tools=[<function get_weather at 0x762e88216f80>, <function send_report_email at 0x762e8823c550>, <function query_database at 0x762e8823c820>, <function query_web at 0x762e8823caf0>], location_type='local', package_name=None, package_version=None, origin_ref=None, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')], tool_registry=None)



## Create reusable runtime

Use `LlmFunctionRuntime` when multiple decorated functions or repeated calls should reuse the same initialized `WorkflowAutoAssembler` and in-memory workflow cache.



```python
llm_runtime = LlmFunctionRuntime(config=llm_config)

llm_runtime

```




    LlmFunctionRuntime(available_functions=None, available_callables=None, tool_registry=None, tool_sources=[InMemoryToolSource(tools=[<function get_weather at 0x762e88216f80>, <function send_report_email at 0x762e8823c550>, <function query_database at 0x762e8823c820>, <function query_web at 0x762e8823caf0>], location_type='local', package_name=None, package_version=None, origin_ref=None, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')], config=LlmFunctionConfig(runtime=LlmRuntimeConfig(llm_handler_params={'llm_h_type': 'ollama', 'llm_h_params': {'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}}, storage_path='/tmp', force_replan=False, max_retry=None, reset_loops=None, compare_params=None, test_params=None), tool_sources=[InMemoryToolSource(tools=[<function get_weather at 0x762e88216f80>, <function send_report_email at 0x762e8823c550>, <function query_database at 0x762e8823c820>, <function query_web at 0x762e8823caf0>], location_type='local', package_name=None, package_version=None, origin_ref=None, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')], tool_registry=None), llm_handler_params={'llm_h_type': 'ollama', 'llm_h_params': {'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}}, storage_path='/tmp', resolved_tools={'available_functions': [LlmFunctionItem(func_id='a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb', name='get_weather', description='Get current weather for a city.', input_schema_json={'properties': {'city': {'description': 'City name.', 'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'GetWeatherInput', 'type': 'object'}, output_schema_json={'properties': {'forecast': {'description': 'Weather forecast for the city.', 'title': 'Forecast', 'type': 'string'}}, 'required': ['forecast'], 'title': 'GetWeatherOutput', 'type': 'object'}), LlmFunctionItem(func_id='a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3', name='send_report_email', description='Sends a report email with given information points to a city.', input_schema_json={'$defs': {'EmailInformationPoint': {'properties': {'title': {'default': None, 'description': 'Few word description of the information.', 'title': 'Title', 'type': 'string'}, 'content': {'description': 'Content of the information.', 'title': 'Content', 'type': 'string'}}, 'required': ['content'], 'title': 'EmailInformationPoint', 'type': 'object'}}, 'properties': {'city': {'description': 'Name of the city where report will be send.', 'title': 'City', 'type': 'string'}, 'information': {'items': {'$ref': '#/$defs/EmailInformationPoint'}, 'title': 'Information', 'type': 'array'}}, 'required': ['city', 'information'], 'title': 'SendReportEmailInput', 'type': 'object'}, output_schema_json={'properties': {'email_sent': {'description': 'Conformation that email was send successfully.', 'title': 'Email Sent', 'type': 'boolean'}, 'message': {'default': None, 'description': 'Optional comments from the process.', 'title': 'Message', 'type': 'string'}}, 'required': ['email_sent'], 'title': 'SendReportEmailOutput', 'type': 'object'}), LlmFunctionItem(func_id='9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568', name='query_database', description='Get information from the database with provided filters.', input_schema_json={'properties': {'topic': {'description': 'Topic of a requested piece of information.', 'title': 'Topic', 'type': 'string'}, 'location': {'description': 'Filter for location name.', 'title': 'Location', 'type': 'string'}, 'uid': {'default': None, 'description': 'Filter for unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['topic', 'location'], 'title': 'QueryDatabaseInput', 'type': 'object'}, output_schema_json={'properties': {'info': {'description': 'Content of the information.', 'title': 'Info', 'type': 'string'}, 'uid': {'default': None, 'description': 'Unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['info'], 'title': 'QueryDatabaseOutput', 'type': 'object'}), LlmFunctionItem(func_id='97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1', name='query_web', description='Get information from the internet for provided query.', input_schema_json={'properties': {'search_input': {'description': 'Topic to be searched on the web.', 'title': 'Search Input', 'type': 'string'}}, 'required': ['search_input'], 'title': 'QueryWebInput', 'type': 'object'}, output_schema_json={'properties': {'search_results': {'description': 'List relevant info from search results.', 'items': {'type': 'string'}, 'title': 'Search Results', 'type': 'array'}}, 'required': ['search_results'], 'title': 'QueryWebOutput', 'type': 'object'})], 'available_callables': {'a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb': <function get_weather at 0x762e88216f80>, 'a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3': <function send_report_email at 0x762e8823c550>, '9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568': <function query_database at 0x762e8823c820>, '97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1': <function query_web at 0x762e8823caf0>}, 'resolved_tools': [ResolvedTool(tool_spec=ToolSpec(func=<function get_weather at 0x762e88216f80>, name='get_weather', description='Get current weather for a city.', input_model=<class '__main__.GetWeatherInput'>, output_model=<class '__main__.GetWeatherOutput'>, metadata={}, tags=[]), func=<function get_weather at 0x762e88216f80>, source_type='memory', location_type='local', package_name=None, package_version=None, module_name='__main__', file_path=None, origin_ref=None, metadata={}), ResolvedTool(tool_spec=ToolSpec(func=<function send_report_email at 0x762e8823c550>, name='send_report_email', description='Sends a report email with given information points to a city.', input_model=<class '__main__.SendReportEmailInput'>, output_model=<class '__main__.SendReportEmailOutput'>, metadata={}, tags=[]), func=<function send_report_email at 0x762e8823c550>, source_type='memory', location_type='local', package_name=None, package_version=None, module_name='__main__', file_path=None, origin_ref=None, metadata={}), ResolvedTool(tool_spec=ToolSpec(func=<function query_database at 0x762e8823c820>, name='query_database', description='Get information from the database with provided filters.', input_model=<class '__main__.QueryDatabaseInput'>, output_model=<class '__main__.QueryDatabaseOutput'>, metadata={}, tags=[]), func=<function query_database at 0x762e8823c820>, source_type='memory', location_type='local', package_name=None, package_version=None, module_name='__main__', file_path=None, origin_ref=None, metadata={}), ResolvedTool(tool_spec=ToolSpec(func=<function query_web at 0x762e8823caf0>, name='query_web', description='Get information from the internet for provided query.', input_model=<class '__main__.QueryWebInput'>, output_model=<class '__main__.QueryWebOutput'>, metadata={}, tags=[]), func=<function query_web at 0x762e8823caf0>, source_type='memory', location_type='local', package_name=None, package_version=None, module_name='__main__', file_path=None, origin_ref=None, metadata={})]}, waa_h=WorkflowAutoAssembler(workflow_error_types=<enum 'WorkflowErrorType'>, workflow_error=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowError'>, available_functions=[LlmFunctionItem(func_id='a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb', name='get_weather', description='Get current weather for a city.', input_schema_json={'properties': {'city': {'description': 'City name.', 'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'GetWeatherInput', 'type': 'object'}, output_schema_json={'properties': {'forecast': {'description': 'Weather forecast for the city.', 'title': 'Forecast', 'type': 'string'}}, 'required': ['forecast'], 'title': 'GetWeatherOutput', 'type': 'object'}), LlmFunctionItem(func_id='a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3', name='send_report_email', description='Sends a report email with given information points to a city.', input_schema_json={'$defs': {'EmailInformationPoint': {'properties': {'title': {'default': None, 'description': 'Few word description of the information.', 'title': 'Title', 'type': 'string'}, 'content': {'description': 'Content of the information.', 'title': 'Content', 'type': 'string'}}, 'required': ['content'], 'title': 'EmailInformationPoint', 'type': 'object'}}, 'properties': {'city': {'description': 'Name of the city where report will be send.', 'title': 'City', 'type': 'string'}, 'information': {'items': {'$ref': '#/$defs/EmailInformationPoint'}, 'title': 'Information', 'type': 'array'}}, 'required': ['city', 'information'], 'title': 'SendReportEmailInput', 'type': 'object'}, output_schema_json={'properties': {'email_sent': {'description': 'Conformation that email was send successfully.', 'title': 'Email Sent', 'type': 'boolean'}, 'message': {'default': None, 'description': 'Optional comments from the process.', 'title': 'Message', 'type': 'string'}}, 'required': ['email_sent'], 'title': 'SendReportEmailOutput', 'type': 'object'}), LlmFunctionItem(func_id='9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568', name='query_database', description='Get information from the database with provided filters.', input_schema_json={'properties': {'topic': {'description': 'Topic of a requested piece of information.', 'title': 'Topic', 'type': 'string'}, 'location': {'description': 'Filter for location name.', 'title': 'Location', 'type': 'string'}, 'uid': {'default': None, 'description': 'Filter for unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['topic', 'location'], 'title': 'QueryDatabaseInput', 'type': 'object'}, output_schema_json={'properties': {'info': {'description': 'Content of the information.', 'title': 'Info', 'type': 'string'}, 'uid': {'default': None, 'description': 'Unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['info'], 'title': 'QueryDatabaseOutput', 'type': 'object'}), LlmFunctionItem(func_id='97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1', name='query_web', description='Get information from the internet for provided query.', input_schema_json={'properties': {'search_input': {'description': 'Topic to be searched on the web.', 'title': 'Search Input', 'type': 'string'}}, 'required': ['search_input'], 'title': 'QueryWebInput', 'type': 'object'}, output_schema_json={'properties': {'search_results': {'description': 'List relevant info from search results.', 'items': {'type': 'string'}, 'title': 'Search Results', 'type': 'array'}}, 'required': ['search_results'], 'title': 'QueryWebOutput', 'type': 'object'})], available_callables={'a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb': <function get_weather at 0x762e88216f80>, 'a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3': <function send_report_email at 0x762e8823c550>, '9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568': <function query_database at 0x762e8823c820>, '97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1': <function query_web at 0x762e8823caf0>}, max_output_unexpected=3, max_retry=10, reset_loops=2, storage_path='/tmp', llm_handler_h=LlmHandler(llm_h_type='ollama', llm_h_params={'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}, llm_h_class=<class 'workflow_auto_assembler.workflow_auto_assembler.OllamaHandlerAsync'>, llm_h=OllamaHandlerAsync(connection_string='http://localhost:11434', model_name='gpt-oss:20b', model=<ollama._client.AsyncClient object at 0x762e883a0190>, kwargs={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), llm_handler_class=<class 'workflow_auto_assembler.workflow_auto_assembler.LlmHandler'>, llm_handler_params={'llm_h_type': 'ollama', 'llm_h_params': {'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}}, check_h=WorkflowCheck(workflow_error_types=<enum 'WorkflowErrorType'>, workflow_error=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowError'>, system_message='{purpose_description}\n{expected_output_schema}\n{function_call_description}\n', system_message_items={'purpose_description': '## Role\nYou are an initial check for Workflow Agent tasked with creating a complete workflow for a given task.  The workflow must be constructed solely from calls to the functions provided. Each workflow should be represented as a JSON list, where each element is an object representing a single function call. For any function input that is meant to be filled using the output of a previous step rather than provided directly, indicate this using the format: "source: <previous_function_name>.output.<field_name>". Your task is to determine whether given provided inputs the workflow could be contracted and explain your decision in few statements tops.\n', 'expected_output_schema': '## Output Requirements\n- **Respond ONLY with valid JSON** — specifically, an object. - **Do NOT** provide any additional commentary, explanations, or text outside this JSON object. - The object must represent structured response, with **exactly** the following fields:\n  1. `"decision"` (bool) - true if required workflow could be assembled from provided tools, false if not. \n  2. `"justification"` (string) - explaination for the `"decision"`.\n  \n### Expected Format\n{\n  "decision": true/false,\n  "justification": "This task can/cannot be solved with provided tools, because ..."\n},\n', 'function_call_description': '## Available functions\nBelow is the list of available functions that you can use to build your workflow. Each function is defined by its name, a description, and a JSON schema for its parameters. For example, the function list is as follows:\n{available_functions}\n'}, debug_prompts={'hf': '\nYour output contains functions that are not available for function calling. Pls try again, this time using only provided functions. \nNot available functions:\n{hfunctions}\nAvailable functions:\n{afunctions}\n\nDo not comment!\n', 'alt': '\nYour output contains function that have failed during function calling. Pls try again, this time contructing the workflow that uses different functions. \nFailed function:\n{ffunction}\nOther available functions:\n{afunctions}\n\nDo not comment!\n', 'mo': 'Your output is missing output_model, pls include it as a final step!\n'}, check_prompt='{task_description}\n{input_schema}\n{output_schema}\nIf the task description includes steps that are not explicitly represented in the output schema, you may ignore those extra steps. However, each required output field must be produced by a function whose name/description clearly matches the field’s intent. Do not map unrelated outputs simply because the types are compatible. If a required output implies a specific operation (e.g., persistence, verification, generation), you must have a function that explicitly performs that operation; otherwise decision must be false.\n', check_prompt_items={'input_schema': '--- The following is the expected input model for the future workflow, Workflow Agent could reference values from it if necessesary, given the task with  format "source: input_model.output.<field_name>". \n{input_model_schema}\n---\n', 'output_schema': '--- The following is the expected output model for the future workflow, which would be included as additional workflow step named \'output_model\'.  Outputs from functions selected in that workflow would be able to populate its fields,  given the task with format "source: <previous_workflow_step>.output.<field_name>" or "source: input_model.output.<field_name>". \n{output_model_schema}\n---\n'}, prompts_filepath=None, available_functions=[LlmFunctionItem(func_id='a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb', name='get_weather', description='Get current weather for a city.', input_schema_json={'properties': {'city': {'description': 'City name.', 'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'GetWeatherInput', 'type': 'object'}, output_schema_json={'properties': {'forecast': {'description': 'Weather forecast for the city.', 'title': 'Forecast', 'type': 'string'}}, 'required': ['forecast'], 'title': 'GetWeatherOutput', 'type': 'object'}), LlmFunctionItem(func_id='a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3', name='send_report_email', description='Sends a report email with given information points to a city.', input_schema_json={'$defs': {'EmailInformationPoint': {'properties': {'title': {'default': None, 'description': 'Few word description of the information.', 'title': 'Title', 'type': 'string'}, 'content': {'description': 'Content of the information.', 'title': 'Content', 'type': 'string'}}, 'required': ['content'], 'title': 'EmailInformationPoint', 'type': 'object'}}, 'properties': {'city': {'description': 'Name of the city where report will be send.', 'title': 'City', 'type': 'string'}, 'information': {'items': {'$ref': '#/$defs/EmailInformationPoint'}, 'title': 'Information', 'type': 'array'}}, 'required': ['city', 'information'], 'title': 'SendReportEmailInput', 'type': 'object'}, output_schema_json={'properties': {'email_sent': {'description': 'Conformation that email was send successfully.', 'title': 'Email Sent', 'type': 'boolean'}, 'message': {'default': None, 'description': 'Optional comments from the process.', 'title': 'Message', 'type': 'string'}}, 'required': ['email_sent'], 'title': 'SendReportEmailOutput', 'type': 'object'}), LlmFunctionItem(func_id='9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568', name='query_database', description='Get information from the database with provided filters.', input_schema_json={'properties': {'topic': {'description': 'Topic of a requested piece of information.', 'title': 'Topic', 'type': 'string'}, 'location': {'description': 'Filter for location name.', 'title': 'Location', 'type': 'string'}, 'uid': {'default': None, 'description': 'Filter for unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['topic', 'location'], 'title': 'QueryDatabaseInput', 'type': 'object'}, output_schema_json={'properties': {'info': {'description': 'Content of the information.', 'title': 'Info', 'type': 'string'}, 'uid': {'default': None, 'description': 'Unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['info'], 'title': 'QueryDatabaseOutput', 'type': 'object'}), LlmFunctionItem(func_id='97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1', name='query_web', description='Get information from the internet for provided query.', input_schema_json={'properties': {'search_input': {'description': 'Topic to be searched on the web.', 'title': 'Search Input', 'type': 'string'}}, 'required': ['search_input'], 'title': 'QueryWebInput', 'type': 'object'}, output_schema_json={'properties': {'search_results': {'description': 'List relevant info from search results.', 'items': {'type': 'string'}, 'title': 'Search Results', 'type': 'array'}}, 'required': ['search_results'], 'title': 'QueryWebOutput', 'type': 'object'})], n_checks=7, max_retry=10, llm_h=LlmHandler(llm_h_type='ollama', llm_h_params={'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}, llm_h_class=<class 'workflow_auto_assembler.workflow_auto_assembler.OllamaHandlerAsync'>, llm_h=OllamaHandlerAsync(connection_string='http://localhost:11434', model_name='gpt-oss:20b', model=<ollama._client.AsyncClient object at 0x762e883a0190>, kwargs={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), llm_class=<class 'workflow_auto_assembler.workflow_auto_assembler.LlmHandlerMock'>, llm_params={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), check_class=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowCheck'>, check_params={}, planner_h=WorkflowPlanner(workflow_error_types=<enum 'WorkflowErrorType'>, workflow_error=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowError'>, system_message='{purpose_description}\n{expected_output_schema}\n{function_call_description}\n', system_message_items={'purpose_description': '## Role\nYou are a Workflow Agent tasked with creating a complete workflow for a given task.  Your workflow must be constructed solely from calls to the functions provided. Each workflow should be represented as a JSON list, where each element is an object representing a single function call. For any function input that is meant to be filled using the output of a previous step rather than provided directly, indicate this using the format: "source: <previous_function_name>.output.<field_name>".\n', 'expected_output_schema': '## Output Requirements\n- **Respond ONLY with valid JSON** — specifically, an **array** of objects. - **Do NOT** provide any additional commentary, explanations, or text outside this JSON array. - Each object in the array must represent **one tool call**, with **exactly** the following fields:\n  1. `"name"` (string) - the tool\'s name from the list below.\n  2. `"args"` (object) - any arguments the tool requires.\n- **Important:** If a function argument is intended to be sourced from a previous step\'s output, indicate this using the format: "source: <previous_function_name>.output.<field_name>". - **No expressions:** All argument values must be valid JSON literals (string/number/boolean/null/object/array). Do not use operators like `+` or string concatenation. If you need to include a referenced value inside a longer message, put the full message as a single JSON string (for example: "Converted value: source: convert_units.output.converted_value").\n  \n### Expected Format\n[\n  {\n    "name": "function_name_1",\n    "args": {}\n  },\n  ...,\n  {\n    "name": "function_name_n",\n    "args": {"arg1": "value for arg1"}\n  }\n]\n', 'function_call_description': '## Available functions\nBelow is the list of available functions that you can use to build your workflow. Each function is defined by its name, a description, and a JSON schema for its parameters. For example, the function list is as follows:\n{available_functions}\n'}, debug_prompts={'hf': '\nYour output contains functions that are not available for function calling. Pls try again, this time using only provided functions. \nNot available functions:\n{hfunctions}\nAvailable functions:\n{afunctions}\n\nDo not comment!\n', 'alt': '\nYour output contains function that have failed during function calling. Pls try again, this time contructing the workflow that uses different functions. \nFailed function:\n{ffunction}\nOther available functions:\n{afunctions}\n\nDo not comment!\n', 'mo': '\nThe following is the expected output model for the workflow, which should be included as additional workflow step named \'output_model\'.  Outputs from functions selected in the workflow should be able to populate its fields,  given the task with format "source: <previous_workflow_step>.output.<field_name>" or "source: input_model.output.<field_name>". \n{output_model_schema}\nYour output is missing output_model, pls include it as a final step!\n', 'om': '\nThe output_model step exists but its "args" are missing or empty. Pls include all required output_model fields and map them from previous steps or input_model.\nThe expected output model schema is: {output_model_schema}\n', 'unexpected': '\nYour planned workflow was assembled and ran using some example inputs. As a result of running your workflow, the output deviated from the expected one. Here are the differences:\n{differences}\nThe differences may include a summary line like "Unsatisfied output fields: ...", and may include case ids when multiple test cases were used. Use this info to rethink the workflow wiring.\nPlease adjust steps in your workflow that might have contributed to those differences by changing inputs to later refferenced steps or swapping functions for something else all together. Steps in the refferences are in the same order as items in your planned workflow, starting with 1. If output fields are unsatisfied, consider rewiring the output_model mappings to different existing steps or to input_model fields when appropriate. If rewiring is not enough, change functions or reorder steps. Do not repeat the exact same wiring that produced the mismatched outputs.\nDo not comment!\n'}, plan_prompt='{task_description}\n{input_schema}\n{output_schema}\n', plan_prompt_items={'input_schema': '--- The following is the expected input model for the workflow, reference values from it if necessesary, given the task with  format "source: input_model.output.<field_name>". \n{input_model_schema}\n---\n', 'output_schema': '--- The following is the expected output model for the workflow, which should be included as additional workflow step named \'output_model\'.  Outputs from functions selected in the workflow should be able to populate its fields,  given the task with format "source: <previous_workflow_step>.output.<field_name>" or "source: input_model.output.<field_name>". \n{output_model_schema}\n---\n'}, prompts_filepath=None, available_functions=[LlmFunctionItem(func_id='a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb', name='get_weather', description='Get current weather for a city.', input_schema_json={'properties': {'city': {'description': 'City name.', 'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'GetWeatherInput', 'type': 'object'}, output_schema_json={'properties': {'forecast': {'description': 'Weather forecast for the city.', 'title': 'Forecast', 'type': 'string'}}, 'required': ['forecast'], 'title': 'GetWeatherOutput', 'type': 'object'}), LlmFunctionItem(func_id='a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3', name='send_report_email', description='Sends a report email with given information points to a city.', input_schema_json={'$defs': {'EmailInformationPoint': {'properties': {'title': {'default': None, 'description': 'Few word description of the information.', 'title': 'Title', 'type': 'string'}, 'content': {'description': 'Content of the information.', 'title': 'Content', 'type': 'string'}}, 'required': ['content'], 'title': 'EmailInformationPoint', 'type': 'object'}}, 'properties': {'city': {'description': 'Name of the city where report will be send.', 'title': 'City', 'type': 'string'}, 'information': {'items': {'$ref': '#/$defs/EmailInformationPoint'}, 'title': 'Information', 'type': 'array'}}, 'required': ['city', 'information'], 'title': 'SendReportEmailInput', 'type': 'object'}, output_schema_json={'properties': {'email_sent': {'description': 'Conformation that email was send successfully.', 'title': 'Email Sent', 'type': 'boolean'}, 'message': {'default': None, 'description': 'Optional comments from the process.', 'title': 'Message', 'type': 'string'}}, 'required': ['email_sent'], 'title': 'SendReportEmailOutput', 'type': 'object'}), LlmFunctionItem(func_id='9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568', name='query_database', description='Get information from the database with provided filters.', input_schema_json={'properties': {'topic': {'description': 'Topic of a requested piece of information.', 'title': 'Topic', 'type': 'string'}, 'location': {'description': 'Filter for location name.', 'title': 'Location', 'type': 'string'}, 'uid': {'default': None, 'description': 'Filter for unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['topic', 'location'], 'title': 'QueryDatabaseInput', 'type': 'object'}, output_schema_json={'properties': {'info': {'description': 'Content of the information.', 'title': 'Info', 'type': 'string'}, 'uid': {'default': None, 'description': 'Unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['info'], 'title': 'QueryDatabaseOutput', 'type': 'object'}), LlmFunctionItem(func_id='97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1', name='query_web', description='Get information from the internet for provided query.', input_schema_json={'properties': {'search_input': {'description': 'Topic to be searched on the web.', 'title': 'Search Input', 'type': 'string'}}, 'required': ['search_input'], 'title': 'QueryWebInput', 'type': 'object'}, output_schema_json={'properties': {'search_results': {'description': 'List relevant info from search results.', 'items': {'type': 'string'}, 'title': 'Search Results', 'type': 'array'}}, 'required': ['search_results'], 'title': 'QueryWebOutput', 'type': 'object'})], max_retry=10, llm_h=LlmHandler(llm_h_type='ollama', llm_h_params={'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}, llm_h_class=<class 'workflow_auto_assembler.workflow_auto_assembler.OllamaHandlerAsync'>, llm_h=OllamaHandlerAsync(connection_string='http://localhost:11434', model_name='gpt-oss:20b', model=<ollama._client.AsyncClient object at 0x762e883a0190>, kwargs={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), llm_class=<class 'workflow_auto_assembler.workflow_auto_assembler.LlmHandlerMock'>, llm_params={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), planner_class=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowPlanner'>, planner_params={}, adaptor_h=WorkflowAdaptor(workflow_error_types=<enum 'WorkflowErrorType'>, workflow_error=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowError'>, system_message='{purpose_description}\n{generated_workflow}\n{workflow_current_state}\n{expected_output_schema}\n', system_message_items={'purpose_description': "## Role\nYou are the Adaptor Agent. Your task is to generate a mapping for the selected function's inputs  from the planning agent's workflow output and the available state, which represents outputs from each step of the workflow. Do not reference the output of the same function as an input for that function. All references must point to outputs from previous steps or come from external inputs.\n", 'generated_workflow': "## Generated Workflow\nThe planning agent's workflow is:\n{raw_workflow}\n", 'workflow_current_state': '## Current State Schema\nThe current state (available outputs schema from previous functions) is:\n{workflow_current_state}\n', 'expected_output_schema': '## Output Requirements\nGenerate a valid JSON object that maps the inputs for the selected function id.  For any input that should be derived from a previous step\'s output, reference the source using this format: <function_identifier>.output.<field_name>. Do not use function names as <function_identifier>, but instead use \'id\' from generated workflow. If a literal value is already valid for an input (for example, "Berlin" for the city), do not convert it to a reference. Your response must consist solely of the JSON object with no extra text, explanations, or markdown formatting. The workflow may referance the `input_model` which should be expected under `function_identifier` = 0. \nIf the selected function\'s input schema has required fields, your output must be a JSON object that includes all required fields. Do not return null for the entire args object when required fields exist. Return an object with explicit fields instead. If the input schema has no required fields, an empty object {} is acceptable. Always return a JSON object (not null, not a list). Preserve any valid literals already present in the planned workflow.\nFor instance, if the required mapping is:\n{\n  "input_field_1": "id_1.output.fieldX",\n  "input_field_2": "literal_value",\n  "input_field_3": [\n    {"subfield": "id_2.output.fieldY"}\n  ]\n}\nThen your response should include exactly that JSON object and nothing else.\n'}, debug_prompts={'mapping': '\nYour output does not seem to be formated propperly,  and some of the fields expect different kinds of inputs. Pls try again, this time making sure inputs are compatible with expected input schema. \nProblems with generated mapping: {mapping_errors}\n\nDo not comment!\n', 'unexpected': '\nYour planned workflow was assembled and ran using some example inputs. As a result of running your workflow, the output deviated from the expected one. Here are the differences:\n{differences}\nPlease adjust your workflow.\nDo not comment!\n'}, adapt_prompt='Function: {selected_function_name}\nExpected Input Schema: {selected_function_input_schema}\n', prompts_filepath=None, available_functions=[LlmFunctionItem(func_id='a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb', name='get_weather', description='Get current weather for a city.', input_schema_json={'properties': {'city': {'description': 'City name.', 'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'GetWeatherInput', 'type': 'object'}, output_schema_json={'properties': {'forecast': {'description': 'Weather forecast for the city.', 'title': 'Forecast', 'type': 'string'}}, 'required': ['forecast'], 'title': 'GetWeatherOutput', 'type': 'object'}), LlmFunctionItem(func_id='a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3', name='send_report_email', description='Sends a report email with given information points to a city.', input_schema_json={'$defs': {'EmailInformationPoint': {'properties': {'title': {'default': None, 'description': 'Few word description of the information.', 'title': 'Title', 'type': 'string'}, 'content': {'description': 'Content of the information.', 'title': 'Content', 'type': 'string'}}, 'required': ['content'], 'title': 'EmailInformationPoint', 'type': 'object'}}, 'properties': {'city': {'description': 'Name of the city where report will be send.', 'title': 'City', 'type': 'string'}, 'information': {'items': {'$ref': '#/$defs/EmailInformationPoint'}, 'title': 'Information', 'type': 'array'}}, 'required': ['city', 'information'], 'title': 'SendReportEmailInput', 'type': 'object'}, output_schema_json={'properties': {'email_sent': {'description': 'Conformation that email was send successfully.', 'title': 'Email Sent', 'type': 'boolean'}, 'message': {'default': None, 'description': 'Optional comments from the process.', 'title': 'Message', 'type': 'string'}}, 'required': ['email_sent'], 'title': 'SendReportEmailOutput', 'type': 'object'}), LlmFunctionItem(func_id='9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568', name='query_database', description='Get information from the database with provided filters.', input_schema_json={'properties': {'topic': {'description': 'Topic of a requested piece of information.', 'title': 'Topic', 'type': 'string'}, 'location': {'description': 'Filter for location name.', 'title': 'Location', 'type': 'string'}, 'uid': {'default': None, 'description': 'Filter for unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['topic', 'location'], 'title': 'QueryDatabaseInput', 'type': 'object'}, output_schema_json={'properties': {'info': {'description': 'Content of the information.', 'title': 'Info', 'type': 'string'}, 'uid': {'default': None, 'description': 'Unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['info'], 'title': 'QueryDatabaseOutput', 'type': 'object'}), LlmFunctionItem(func_id='97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1', name='query_web', description='Get information from the internet for provided query.', input_schema_json={'properties': {'search_input': {'description': 'Topic to be searched on the web.', 'title': 'Search Input', 'type': 'string'}}, 'required': ['search_input'], 'title': 'QueryWebInput', 'type': 'object'}, output_schema_json={'properties': {'search_results': {'description': 'List relevant info from search results.', 'items': {'type': 'string'}, 'title': 'Search Results', 'type': 'array'}}, 'required': ['search_results'], 'title': 'QueryWebOutput', 'type': 'object'})], llm_function_item_class=<class 'workflow_auto_assembler.workflow_auto_assembler.LlmFunctionItem'>, max_retry=10, llm_h=LlmHandler(llm_h_type='ollama', llm_h_params={'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}, llm_h_class=<class 'workflow_auto_assembler.workflow_auto_assembler.OllamaHandlerAsync'>, llm_h=OllamaHandlerAsync(connection_string='http://localhost:11434', model_name='gpt-oss:20b', model=<ollama._client.AsyncClient object at 0x762e883a0190>, kwargs={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), llm_class=<class 'workflow_auto_assembler.workflow_auto_assembler.LlmHandlerMock'>, llm_params={}, input_collector_h=InputCollector(loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), input_collector_class=<class 'workflow_auto_assembler.workflow_auto_assembler.InputCollectorMock'>, input_collector_params={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), adaptor_class=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowAdaptor'>, adaptor_params={}, runner_h=WorkflowRunner(workflow_error_types=<enum 'WorkflowErrorType'>, workflow_error=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowError'>, available_functions=[LlmFunctionItem(func_id='a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb', name='get_weather', description='Get current weather for a city.', input_schema_json={'properties': {'city': {'description': 'City name.', 'title': 'City', 'type': 'string'}}, 'required': ['city'], 'title': 'GetWeatherInput', 'type': 'object'}, output_schema_json={'properties': {'forecast': {'description': 'Weather forecast for the city.', 'title': 'Forecast', 'type': 'string'}}, 'required': ['forecast'], 'title': 'GetWeatherOutput', 'type': 'object'}), LlmFunctionItem(func_id='a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3', name='send_report_email', description='Sends a report email with given information points to a city.', input_schema_json={'$defs': {'EmailInformationPoint': {'properties': {'title': {'default': None, 'description': 'Few word description of the information.', 'title': 'Title', 'type': 'string'}, 'content': {'description': 'Content of the information.', 'title': 'Content', 'type': 'string'}}, 'required': ['content'], 'title': 'EmailInformationPoint', 'type': 'object'}}, 'properties': {'city': {'description': 'Name of the city where report will be send.', 'title': 'City', 'type': 'string'}, 'information': {'items': {'$ref': '#/$defs/EmailInformationPoint'}, 'title': 'Information', 'type': 'array'}}, 'required': ['city', 'information'], 'title': 'SendReportEmailInput', 'type': 'object'}, output_schema_json={'properties': {'email_sent': {'description': 'Conformation that email was send successfully.', 'title': 'Email Sent', 'type': 'boolean'}, 'message': {'default': None, 'description': 'Optional comments from the process.', 'title': 'Message', 'type': 'string'}}, 'required': ['email_sent'], 'title': 'SendReportEmailOutput', 'type': 'object'}), LlmFunctionItem(func_id='9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568', name='query_database', description='Get information from the database with provided filters.', input_schema_json={'properties': {'topic': {'description': 'Topic of a requested piece of information.', 'title': 'Topic', 'type': 'string'}, 'location': {'description': 'Filter for location name.', 'title': 'Location', 'type': 'string'}, 'uid': {'default': None, 'description': 'Filter for unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['topic', 'location'], 'title': 'QueryDatabaseInput', 'type': 'object'}, output_schema_json={'properties': {'info': {'description': 'Content of the information.', 'title': 'Info', 'type': 'string'}, 'uid': {'default': None, 'description': 'Unique indentifier of the database item.', 'title': 'Uid', 'type': 'string'}}, 'required': ['info'], 'title': 'QueryDatabaseOutput', 'type': 'object'}), LlmFunctionItem(func_id='97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1', name='query_web', description='Get information from the internet for provided query.', input_schema_json={'properties': {'search_input': {'description': 'Topic to be searched on the web.', 'title': 'Search Input', 'type': 'string'}}, 'required': ['search_input'], 'title': 'QueryWebInput', 'type': 'object'}, output_schema_json={'properties': {'search_results': {'description': 'List relevant info from search results.', 'items': {'type': 'string'}, 'title': 'Search Results', 'type': 'array'}}, 'required': ['search_results'], 'title': 'QueryWebOutput', 'type': 'object'})], available_callables={'a1ab73be67259e736149bd35da129a143206383d6b63749e5cbbe8ec49dbc9eb': <function get_weather at 0x762e88216f80>, 'a5f3428a9f0b010f6bfdd9c8e956600f0a627ec520ee5967942a2844909515a3': <function send_report_email at 0x762e8823c550>, '9bed51d9fc2fa9d99609fc920b83b1f60cf2c5df311b33a7292b21b3cfec6568': <function query_database at 0x762e8823c820>, '97bd46f01b044bda078ac8171188e74d1e9428778f00a510b8a070b4b9110ff1': <function query_web at 0x762e8823caf0>}, output_comparer_h=OutputComparer(ignore_optional=True, max_decimals=None, ignore_fields=set(), ignore_types=set(), loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), output_comparer_class=<class 'workflow_auto_assembler.workflow_auto_assembler.OutputComparerMock'>, output_comparer_params={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), runner_class=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowRunner'>, runner_params={}, storage_h=WorkflowStorage(workflow_error_types=<enum 'WorkflowErrorType'>, workflow_error=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowError'>, model_class=<class 'workflow_auto_assembler.workflow_auto_assembler.AssembledWorkflow'>, workflow_cache={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), storage_class=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowStorage'>, storage_params={}, input_collector_h=InputCollector(loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), input_collector_class=<class 'workflow_auto_assembler.workflow_auto_assembler.InputCollector'>, input_collector_params={}, output_comparer_h=OutputComparer(ignore_optional=True, max_decimals=None, ignore_fields=set(), ignore_types=set(), loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), output_comparer_class=<class 'workflow_auto_assembler.workflow_auto_assembler.OutputComparer'>, output_comparer_params={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s'), waa_class=<class 'workflow_auto_assembler.workflow_auto_assembler.WorkflowAutoAssembler'>, waa_params={}, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')



## Define workflow input and output schemas

The decorated function body is unused. Its signature and docstring define the target typed function contract.



```python
class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city for which weather to be extracted.")

class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city for which the report email was sent.")
    email_sent: bool = Field(..., description="Confirmation that the report email was sent.")
    info : str  = Field(..., description="Information found in the database.")
    message: str = Field(..., description="Optional comments from the email sending process.")

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
        "inputs": WfInputs(city = "Sydney"),
        "outputs": WfOutputs(
            city = "Sydney",
            info = "Content extracted from the database for Birds in Sydney is ...",
            email_sent = False,
            message = "Email was not sent to Sydney!"
        )
    }
] 

@llm_function(runtime=llm_runtime, test_params = test_params)
def query_db_and_send_email(input: WfInputs) -> WfOutputs:
    """
    Query  database to find information on birds and get latest weather for the city, then send an email there.
    """
    pass

```

## Call the generated typed function

On each call, the decorator reuses the shared `LlmFunctionRuntime`, calls `actualize_workflow(...)`, and returns the typed output.



```python
result = query_db_and_send_email(WfInputs(city="London"))
result
```




    WfOutputs(city='London', email_sent=True, info='Content extracted from the database for Birds in London is ...', message='Email sent to London!')




```python
result = query_db_and_send_email(WfInputs(city="Wrocław"))
result

```




    WfOutputs(city='Wrocław', email_sent=False, info='Content extracted from the database for Birds in Wrocław is ...', message='Email was not sent to Wrocław!')



If planning is not possible or failed along the way, a function suppose to return `LlmFunctionError` error.


```python
class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city.")


class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city.")
    summary: str = Field(..., description="Some summary that is not about forcasting.")


@llm_function(config=llm_config)
def impossible_get_city_weather(input: WfInputs) -> WfOutputs:
    """
    Get weather for the provided city and prepare a short user-facing non forcast summary.
    """
    pass

result = impossible_get_city_weather(WfInputs(city="Wrocław"))
result

```

    WARNING:WorkflowAutoAssembler:Workflow planning is not possible!
    WARNING:WorkflowAutoAssembler:Workflow failed to converge.



    ---------------------------------------------------------------------------

    LlmFunctionError                          Traceback (most recent call last)

    Cell In[9], line 17
         12     """
         13     Get weather for the provided city and prepare a short user-facing non forcast summary.
         14     """
         15     pass
    ---> 17 result = impossible_get_city_weather(WfInputs(city="Wrocław"))
         18 result


    File ~/miniforge3/envs/testenv/lib/python3.10/site-packages/llm_function/llm_function.py:596, in LlmFunction.as_decorator.<locals>.decorator.<locals>.sync_wrapper(*args, **kwargs)
        593 @wraps(func)
        594 def sync_wrapper(*args, **kwargs):
        595     bound = signature.bind(*args, **kwargs)
    --> 596     return self._run_coro_blocking(_invoke_async(bound.arguments[input_name]))


    File ~/miniforge3/envs/testenv/lib/python3.10/site-packages/llm_function/llm_function.py:509, in LlmFunction._run_coro_blocking(self, coro)
        507 if "value" in error:
        508     if isinstance(error["value"], LlmFunctionError):
    --> 509         raise LlmFunctionError(error["value"].workflow_error) from None
        510     raise error["value"]
        512 return result["value"]


    LlmFunctionError: The only provided function that obtains weather data is get_weather, which returns a forecast string. There is no function available that can transform this forecast into a short user-facing non‑forecast summary as required by the output schema. Therefore the task cannot be completed with the given tools.

