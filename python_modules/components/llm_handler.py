from datetime import datetime
import importlib
import logging
from typing import Optional, List, Dict, Any
import attrs
import attrsx
from pydantic import BaseModel, Field

#! import openai
#! import ollama

  

class LlmHandlerBaseResponse(BaseModel):
    """
    Follows Ollama BaseGenerateResponse model
    """

    model: Optional[str] = Field(default = None, description ='Model used to generate response.')
    created_at: Optional[str] = Field(default = None, description ='Time when the request was created.')
    total_duration: Optional[int] = Field(default = None, description ='Total duration in nanoseconds.')

    def as_dict(self) -> dict:
        """Return a dict representation of the response."""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()

    def as_json(self) -> str:
        """Return a JSON string representation of the response."""
        if hasattr(self, "model_dump_json"):
            return self.model_dump_json()
        return self.json()

class LlmMessage(BaseModel):
    """
    Chat message based on Ollama.
    """

    role: str = Field(description="Assumed role of the message. Response messages has role 'assistant' or 'tool'.")
    content: Optional[str] = Field(
        default=None,
        description="Content of the message. Response messages contains message fragments when streaming.",
    )
    thinking: Optional[str] = Field(
        default=None,
        description="Thinking content. Only present when thinking is enabled.",
    )

    def as_dict(self) -> dict:
        """Return a dict representation of the message."""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()

    def as_json(self) -> str:
        """Return a JSON string representation of the message."""
        if hasattr(self, "model_dump_json"):
            return self.model_dump_json()
        return self.json()


class LlmHandlerChatOutput(LlmHandlerBaseResponse):

    """
    Follows Ollama ChatResponse model
    """

    message: Optional[LlmMessage] = Field(default = None, description ='Response message.')
    def as_dict(self) -> dict:
        """Return a dict representation of the chat output."""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()

    def as_json(self) -> str:
        """Return a JSON string representation of the chat output."""
        if hasattr(self, "model_dump_json"):
            return self.model_dump_json()
        return self.json()


@attrsx.define
class OllamaHandlerAsync():
    """
    Extended OllamaHandlerAsync supporting chat with optional function calling.
    """

    connection_string: Optional[str] = attrs.field(default=None)
    model_name: Optional[str] = attrs.field(default=None)

    model = attrs.field(default=None)

    kwargs: Dict[str, Any] = attrs.field(factory=dict)

    def __attrs_post_init__(self):

        self._initialize_ollama()

    def _initialize_ollama(self):

        try:
            AsyncClient = importlib.import_module("ollama").AsyncClient
        except ImportError as e:
            raise ImportError("Failed to import ollama!") from e

        if self.model is None:
            self.model = AsyncClient(
                host = self.connection_string,
                **dict(self.kwargs),
            )


    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model_name: Optional[str] = None) -> LlmHandlerChatOutput:
        """
        Core chat method for Ollama .
        """

        params = {
            "model": model_name or self.model_name,
            "messages": messages,
        }
        if self.kwargs:
            params.update(dict(self.kwargs))


        response = await self.model.chat(**params)
        self.logger.debug(f"Tokens used: {response.get('usage', {}).get('total_tokens', 0)}")


        return LlmHandlerChatOutput(
            model = response.model,
            created_at = response.created_at,
            total_duration = response.total_duration,
            message = LlmMessage(
                role = response.message.role,
                content = response.message.content
            )
        )

    def get_client(self):
        """Return the underlying Ollama client instance."""
        return self.model
            

    


@attrsx.define
class OpenAIHandlerAsync:
    """
    OpenAIHandlerAsync – Async client for OpenAI models with native function calling (tools).
    """

    connection_string: Optional[str] = attrs.field(default=None)  # Optional for Azure OpenAI
    model_name: Optional[str] = attrs.field(default="gpt-4-turbo")  # Default OpenAI model
    api_key: Optional[str] = attrs.field(default=None)  # OpenAI API Key

    model = attrs.field(default=None)
    
    kwargs: Dict[str, Any] = attrs.field(factory=dict)  # Additional passthrough options

    def __attrs_post_init__(self):
        self._initialize_openai()

    def _initialize_openai(self):

        try:
            openai = importlib.import_module("openai")
        except ImportError as e:
            raise ImportError("Failed to import openai!") from e

        self.model = openai

        if self.api_key:
            self.model.api_key = self.api_key
        if self.connection_string:
            self.model.api_base = self.connection_string  # Support for Azure endpoint

    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model_name: Optional[str] = None) -> LlmHandlerChatOutput:
        """
        Core chat method for OpenAI.
        """

        params = {
            "model": model_name or self.model_name,
            "messages": messages,
        }
        if self.kwargs:
            params.update(dict(self.kwargs))

        exec_start = datetime.now()
        response = await self.model.ChatCompletion.acreate(**params)
        self.logger.debug(f"Tokens used: {response['usage']['total_tokens']}")
        

        return LlmHandlerChatOutput(
            model = response["model"],
            created_at = response["created"],
            total_duration = datetime.now() - exec_start,
            message = LlmMessage(
                role = response["choices"][0].message.role,
                content = response["choices"][0].message.content,
            )

        )

    def get_client(self):
        """Return the underlying OpenAI client instance."""
        return self.model


@attrsx.define
class LlmHandler:
    """
    General llm handler, connects to different llm apis.
    """

    llm_h_type : str = attrs.field()
    llm_h_params: Dict[str, Any] = attrs.field(factory=dict)
    
    llm_h_class = attrs.field(default = None)
    llm_h = attrs.field(default = None)
    _id_counter = 0


    def __attrs_post_init__(self):

        if self.llm_h_type == "ollama":
            self.llm_h_class = OllamaHandlerAsync
        if self.llm_h_type == "openai":
            self.llm_h_class = OpenAIHandlerAsync

        self._initialize_llm_h()

    def _initialize_llm_h(self):

        if self.llm_h is None:
            params = dict(self.llm_h_params) if self.llm_h_params else {}
            self.llm_h = self.llm_h_class(**params)

    @classmethod
    def _gen_id(cls) -> int:
        cls._id_counter += 1
        return cls._id_counter


    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model_name: Optional[str] = None) -> LlmHandlerChatOutput:
        """
        Core chat method.
        """
        uid = self._gen_id()
        input_messages = [LlmMessage(**d) for d in messages]
        self.logger.debug(f"-> {uid}", 
            save_vars = ["input_messages"])
        try:

            response = await self.llm_h.chat(
                messages = messages,
                model_name = model_name)

        except (RuntimeError, ValueError, TypeError) as e:
            response = None
            self.logger.error(f"LLM Handler Error: {e}")

        self.logger.debug(f"<- {uid}", 
            save_vars = ["response.message"],
            actions = [
                {
                    "name" : "langfuse.log_trace",
                    "params" : {
                        "input" : input_messages,
                        "output" : response.message
                    }
                }
            ]
        )

        return response

    def get_backend(self):
        """Return the initialized LLM backend handler."""
        return self.llm_h
