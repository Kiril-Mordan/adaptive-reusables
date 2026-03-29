Currently intended usage pattern for `llm_function_tools`:

- define typed tools with `@llm_tool`
- inspect the attached `ToolSpec`
- discover tools from a Python module
- load tools from a standalone `.py` file



```python
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel, Field

from llm_function_tools import (
    discover_tools_in_module,
    get_tool_spec,
    llm_tool,
    load_tools_from_python_file,
    tool_from_callable,
)

```

## Define typed tools

A tool is just a function with one `BaseModel` input and one `BaseModel` output. `@llm_tool` attaches a normalized `ToolSpec` to the function.



```python
class WeatherInput(BaseModel):
    city: str = Field(..., description="City name.")


class WeatherOutput(BaseModel):
    forecast: str = Field(..., description="Weather forecast.")


@llm_tool(tags=["weather"], metadata={"scope": "demo"})
def get_weather(inputs: WeatherInput) -> WeatherOutput:
    """Get current weather for a city."""
    return WeatherOutput(forecast=f"Sunny in {inputs.city}")


tool_spec = get_tool_spec(get_weather)
tool_spec

```




    ToolSpec(func=<function get_weather at 0x7e0640de5360>, name='get_weather', description='Get current weather for a city.', input_model=<class '__main__.WeatherInput'>, output_model=<class '__main__.WeatherOutput'>, metadata={'scope': 'demo'}, tags=['weather'])



## Create a `ToolSpec` from a plain callable

You can also build `ToolSpec` directly without decorating the function.



```python
class SearchInput(BaseModel):
    query: str


class SearchOutput(BaseModel):
    result: str


def search_notes(inputs: SearchInput) -> SearchOutput:
    """Search local notes."""
    return SearchOutput(result=f"Found: {inputs.query}")


tool_from_callable(search_notes)

```




    ToolSpec(func=<function search_notes at 0x7e0640de5090>, name='search_notes', description='Search local notes.', input_model=<class '__main__.SearchInput'>, output_model=<class '__main__.SearchOutput'>, metadata={}, tags=[])



## Discover tools from a module

In normal usage, loaders will inspect a Python module or file and collect decorated tools from it.

In a notebook, `__main__` behaves as the current module, so we can demonstrate the same discovery flow here.



```python
import __main__

discovered = discover_tools_in_module(__main__)
[(tool.name, tool.tags, tool.metadata) for tool in discovered]

```




    [('get_weather', ['weather'], {'scope': 'demo'})]



## Load tools from a standalone `.py` file

This is closer to the future `llm_function` use case where tools live outside the runtime module.



```python
tmp_dir = TemporaryDirectory()
tool_file = Path(tmp_dir.name) / "sample_tools.py"
tool_file.write_text(
    """
from pydantic import BaseModel
from llm_function_tools import llm_tool


class MathInput(BaseModel):
    x: int


class MathOutput(BaseModel):
    y: int


@llm_tool(tags=['math'])
def add_one(inputs: MathInput) -> MathOutput:
    '''Add one to the input value.'''
    return MathOutput(y=inputs.x + 1)
""".strip()
)

file_tools = load_tools_from_python_file(str(tool_file))
[(tool.name, tool.description, tool.tags) for tool in file_tools]

```




    [('add_one', 'Add one to the input value.', ['math'])]




```python
file_tools
```




    [ToolSpec(func=<function add_one at 0x7e06361ae830>, name='add_one', description='Add one to the input value.', input_model=<class '_llm_function_tools_sample_tools_8306dd8f7421.MathInput'>, output_model=<class '_llm_function_tools_sample_tools_8306dd8f7421.MathOutput'>, metadata={}, tags=['math'])]



The resulting `ToolSpec` objects are the input that a higher-level runtime such as `llm_function` can later resolve into runnable tool registries with provenance metadata.

