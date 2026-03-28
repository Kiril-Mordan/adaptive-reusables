from pydantic import BaseModel, Field

from python_modules.components.workflow_adaptor import WorkflowAdaptor
from python_modules.components.wa_general_models import LlmFunctionItemInput, create_avc_items


class GetWeatherInput(BaseModel):
    city: str = Field(..., description="City name.")


class GetWeatherOutput(BaseModel):
    condition: str = Field(..., description="Weather condition.")


def get_weather(inputs: GetWeatherInput) -> GetWeatherOutput:
    return GetWeatherOutput(condition="Sunny")


class WfInputs(BaseModel):
    city: str


class WfOutputs(BaseModel):
    city: str


def test_adaptor_add_fcall_ids_with_input_model():
    adaptor = WorkflowAdaptor.__new__(WorkflowAdaptor)

    workflow = [
        {"name": "get_weather", "args": {"city": "Berlin"}},
    ]

    wf_with_ids, id_map = adaptor._add_fcall_ids(
        workflow=workflow,
        input_model=WfInputs,
    )

    assert wf_with_ids[0]["id"] == 0
    assert wf_with_ids[0]["name"] == "input_model"
    assert wf_with_ids[1]["id"] == 1
    assert wf_with_ids[1]["name"] == "get_weather"
    assert id_map["0"] == "input_model"
    assert id_map["1"] == "get_weather"


def test_adaptor_mod_inputs_adds_output_model():
    adaptor = WorkflowAdaptor.__new__(WorkflowAdaptor)

    avc = create_avc_items([
        LlmFunctionItemInput(func=get_weather, input_model=GetWeatherInput, output_model=GetWeatherOutput)
    ])
    available_functions = avc["available_functions"]

    workflow = [{"id": 1, "name": "get_weather", "args": {"city": "Berlin"}}]
    adaptor.llm_function_item_class = type(available_functions[0])

    workflow_s, available_functions_t = adaptor._mod_inputs_for_output_model(
        workflow=workflow.copy(),
        output_model=WfOutputs,
        available_functions=available_functions,
    )

    assert workflow_s[-1]["name"] == "output_model"
    assert workflow_s[-1]["id"] == 2
    assert available_functions_t[-1].name == "output_model"
