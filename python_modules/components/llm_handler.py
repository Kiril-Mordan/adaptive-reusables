import logging
import attrsx
import attrs

from typing import Optional, List, Dict

#! import openai
#! import ollama

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
                   model_name: Optional[str] = None,
                   tools: Optional[List[Dict]] = None, 
                   tool_choice: Optional[str] = None) -> Dict:
        """
        Core chat method for Ollama with native function calling (tools).
        - Supports passing tools to the model for function calling.
        - Falls back to prompt-based simulation if tools are not provided.
        """

        params = {
            "model": model_name or self.model_name,
            "messages": messages
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools

            if tool_choice:
                params["tool_choice"] = tool_choice  # Optional specific tool selection


        response = await self.model.chat(**params)
        self.logger.debug(f"Tokens used: {response.get('usage', {}).get('total_tokens', 0)}")
        
        # Convert response to dict
        response_dict = {
            "model": response.model,
            "created_at": response.created_at,
            "done": response.done,
            "done_reason": response.done_reason,
            "total_duration": response.total_duration,
            "load_duration": response.load_duration,
            "prompt_eval_count": response.prompt_eval_count,
            "prompt_eval_duration": response.prompt_eval_duration,
            "eval_count": response.eval_count,
            "eval_duration": response.eval_duration,
            "message": {
                "role": response.message.role,
                "content": response.message.content,
                "tool_calls": []
            }
        }

        if response.message.tool_calls:
            response_dict["message"]["tool_calls"] = [
                    {
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments
                        }
                    } for call in response.message.tool_calls
                ]

        return response_dict
            

    


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
                   model_name: Optional[str] = None,
                   tools: Optional[List[Dict]] = None, 
                   tool_choice: Optional[str] = None) -> Dict:
        """
        Core chat method for OpenAI with native function calling (tools).
        """

        params = {
            "model": model_name or self.model_name,
            "messages": messages,
            **self.kwargs
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools

            if tool_choice:
                params["tool_choice"] = tool_choice  # Optional: Force specific tool selection

        
        response = await self.model.ChatCompletion.acreate(**params)
        self.logger.debug(f"Tokens used: {response['usage']['total_tokens']}")
        
        # Convert response to dict
        response_dict = {
            "model": response["model"],
            "created_at": response["created"],
            "choices": response["choices"],
            "usage": response["usage"]
        }
        
        return response_dict


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
                   model_name: Optional[str] = None,
                   tool_descriptions : Optional[List[Dict]] = None, 
                   tools: Optional[List[Dict]] = None, 
                   tool_choice: Optional[str] = None) -> Dict:
        """
        Core chat method with native function calling (tools).
        """
        
        try:

            # Inject system message with tool descriptions if provided
            if tool_descriptions:
                tool_description_text = "\n".join(
                    [f"{tool['name']}: {tool['description']}" for tool in tool_descriptions]
                )
                system_message = {
                    "role": "system",
                    "content": f"The following tools are available for function calling:\n{tool_description_text}"
                }
                # Prepend system message to the beginning of the chat
                messages.insert(0, system_message)

            response = await self.llm_h.chat(
                messages = messages,
                model_name = model_name,
                tools = tools,
                tool_choice = tool_choice)

        except Exception as e:
            response = None
            self.logger.error(f"LLM Handler Error: {e}")

        return response



