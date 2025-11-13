import logging
import attrsx
import attrs
from datetime import datetime
from typing import Optional, List, Dict

#! import openai
#! import ollama

  

class LlmHandlerBaseResponse(BaseModel):
    """
    Follows Ollama BaseGenerateResponse model
    """

    model: Optional[str] = Field(default = None, description ='Model used to generate response.')
    created_at: Optional[str] = Field(default = None, description ='Time when the request was created.')
    total_duration: Optional[int] = Field(default = None, description ='Total duration in nanoseconds.')


class LlmMessage(BaseModel):
  """
  Chat message based on Ollama.
  """

  role: str = Field(description ="Assumed role of the message. Response messages has role 'assistant' or 'tool'.")  
  content: Optional[str] = Field(default = None, description ="Content of the message. Response messages contains message fragments when streaming.")
  thinking: Optional[str] = Field(default = None, description ="Thinking content. Only present when thinking is enabled.")


class LlmHandlerChatOutput(LlmHandlerBaseResponse):

    """
    Follows Ollama ChatResponse model
    """

    message: Optional[LlmMessage] = Field(default = None, description ='Response message.')
    


@attrsx.define
class OllamaHandlerAsync():
    """
    Extended OllamaHandlerAsync supporting chat with optional function calling.
    """

    connection_string: Optional[str] = attrs.field(default=None)
    model_name: Optional[str] = attrs.field(default=None)

    model = attrs.field(default=None)

    kwargs: dict = attrs.field(factory=dict)

    def __attrs_post_init__(self):

       self._initialize_ollama()

    def _initialize_ollama(self):

        try:
            from ollama import AsyncClient
        except ImportError as e:
            raise ImportError("Failed to import ollama!")

        if self.model is None:
            self.model = AsyncClient(
                host = self.connection_string, 
                **self.kwargs)


    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model_name: Optional[str] = None) -> LlmHandlerChatOutput:
        """
        Core chat method for Ollama .
        """

        params = {
            "model": model_name or self.model_name,
            "messages": messages
        }


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
            

    


@attrsx.define
class OpenAIHandlerAsync:
    """
    OpenAIHandlerAsync – Async client for OpenAI models with native function calling (tools).
    """

    connection_string: Optional[str] = attrs.field(default=None)  # Optional for Azure OpenAI
    model_name: Optional[str] = attrs.field(default="gpt-4-turbo")  # Default OpenAI model
    api_key: Optional[str] = attrs.field(default=None)  # OpenAI API Key

    model = attrs.field(default=None)
    
    kwargs: dict = attrs.field(factory=dict)  # Additional passthrough options

    def __attrs_post_init__(self):
        self._initialize_openai()

    def _initialize_openai(self):

        try:
            import openai
        except ImportError as e:
            raise ImportError("Failed to import openai!")

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
            **self.kwargs
        }

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


@attrsx.define
class LlmHandler:
    """
    General llm handler, connects to different llm apis.
    """

    llm_h_type : str = attrs.field()
    llm_h_params : dict = attrs.field(default = {})
    
    llm_h_class = attrs.field(default = None)
    llm_h = attrs.field(default = None)

    def __attrs_post_init__(self):

        if self.llm_h_type == "ollama":
            self.llm_h_class = OllamaHandlerAsync
        if self.llm_h_type == "openai":
            self.llm_h_class = OpenAIHandlerAsync

        self._initialize_llm_h()

    def _initialize_llm_h(self):

        if self.llm_h is None:
            self.llm_h = self.llm_h_class(**self.llm_h_params)

    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   model_name: Optional[str] = None) -> LlmHandlerChatOutput:
        """
        Core chat method.
        """
        
        try:

            response = await self.llm_h.chat(
                messages = messages,
                model_name = model_name)

        except Exception as e:
            response = None
            self.logger.error(f"LLM Handler Error: {e}")

        return response



