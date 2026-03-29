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

from llm_function_tools import llm_tool
from llm_function import InMemoryToolSource, PythonFileToolSource, LlmFunctionConfig, LlmRuntimeConfig, llm_function

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


tool_sources = [InMemoryToolSource([get_weather])]

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




    [PythonFileToolSource(file_path='/tmp/tmpva36jgth/weather_tools.py', include_plain_typed=False, location_type='local', package_name=None, package_version=None, module_name=None, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')]



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




    LlmFunctionConfig(runtime=LlmRuntimeConfig(llm_handler_params={'llm_h_type': 'ollama', 'llm_h_params': {'connection_string': 'http://localhost:11434', 'model_name': 'gpt-oss:20b'}}, storage_path='/tmp', force_replan=False, max_retry=None, reset_loops=None, compare_params=None, test_params=None), tool_sources=[InMemoryToolSource(tools=[<function get_weather at 0x7b8c78355e10>], location_type='local', package_name=None, package_version=None, origin_ref=None, loggerLvl=20, logger_name=None, logger_format='%(levelname)s:%(name)s:%(message)s')], tool_registry=None)



## Define workflow input and output schemas

The decorated function body is unused. Its signature and docstring define the target typed function contract.



```python
class WfInputs(BaseModel):
    city: str = Field(..., description="Name of the city.")


class WfOutputs(BaseModel):
    city: str = Field(..., description="Name of the city.")
    summary: str = Field(..., description="Forcast summary for user.")

```


```python
@llm_function(config=llm_config)
def get_city_weather(input: WfInputs) -> WfOutputs:
    """
    Get weather for the provided city and prepare a short user-facing forcast summary.
    """
    pass

```

## Call the generated typed function

On each call, the decorator creates a `WorkflowAutoAssembler`, resolves tools from the config, calls `actualize_workflow(...)`, and returns the typed output.



```python
result = get_city_weather(WfInputs(city="Wrocław"))
result

```




    WfOutputs(city='Wrocław', summary='Sunny in Wrocław')


