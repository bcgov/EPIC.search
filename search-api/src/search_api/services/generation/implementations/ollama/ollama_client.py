"""Ollama LLM client implementation."""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from ...abstractions.llm_client import LLMClient

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """Ollama implementation of the LLM client."""
    
    def __init__(self):
        """Initialize the Ollama client."""
        self.base_url = os.environ.get("LLM_HOST", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.model_name = os.environ.get("LLM_MODEL", os.environ.get("OLLAMA_MODEL", "llama3.1"))
        
    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **kwargs
    ) -> Any:
        """Create a chat completion using Ollama.
        
        Args:
            model: The model name (will use configured model).
            messages: List of message dictionaries with 'role' and 'content'.
            temperature: Sampling temperature (0.0 to 2.0).
            **kwargs: Additional parameters (max_tokens, tools, tool_choice, etc.).
            
        Returns:
            Chat completion response object.
            
        Raises:
            Exception: If the API request fails.
        """
        return self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=kwargs.get('max_tokens'),
            tools=kwargs.get('tools'),
            tool_choice=kwargs.get('tool_choice')
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            tools: List of tool definitions (not supported in basic Ollama).
            tool_choice: Tool choice strategy (not supported in basic Ollama).
            
        Returns:
            Dict containing the response data.
            
        Raises:
            Exception: If the API request fails.
        """
        try:
            # Build the request payload
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens
            
            # Handle tools/function calling for Ollama
            if tools:
                logger.warning("Function calling not fully supported in basic Ollama, using prompt engineering")
                # Convert function calling to prompt engineering
                messages = self._convert_tools_to_prompt(messages, tools, tool_choice)
                payload["messages"] = messages
            
            logger.info(f"Sending chat completion request to Ollama with {len(messages)} messages")
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            ollama_response = response.json()
            
            # Convert Ollama response to OpenAI-compatible format
            result = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": ollama_response["message"]["content"]
                    },
                    "finish_reason": "stop"
                }]
            }
            
            # Handle structured output if tools were used
            if tools:
                result = self._handle_structured_output(result, tools)
            
            logger.info("Chat completion request completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Ollama chat completion failed: {str(e)}")
            raise
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "ollama"
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name
    
    def _convert_tools_to_prompt(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_choice: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Convert OpenAI-style function calling to prompt engineering for Ollama."""
        if not tools:
            return messages
        
        # Extract function schemas
        functions_desc = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                functions_desc.append(f"Function: {func['name']}\nDescription: {func['description']}\nParameters: {json.dumps(func['parameters'], indent=2)}")
        
        # Add function calling instructions to system message
        function_prompt = f"""
You have access to the following functions:

{chr(10).join(functions_desc)}

When you need to call a function, respond with a JSON object in this exact format:
{{
  "function_call": {{
    "name": "function_name",
    "arguments": {{
      "param1": "value1",
      "param2": "value2"
    }}
  }}
}}

Always respond with valid JSON when calling functions. Do not include any other text or formatting.
"""
        
        # Modify system message or add new one
        modified_messages = []
        has_system = False
        
        for msg in messages:
            if msg["role"] == "system":
                msg["content"] = msg["content"] + function_prompt
                has_system = True
            modified_messages.append(msg)
        
        if not has_system:
            modified_messages.insert(0, {"role": "system", "content": function_prompt})
        
        return modified_messages
    
    def _handle_structured_output(
        self,
        result: Dict[str, Any],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle structured output from Ollama when function calling was requested."""
        content = result["choices"][0]["message"]["content"]
        
        try:
            # Try to parse as JSON function call
            if content.strip().startswith("{") and "function_call" in content:
                parsed = json.loads(content)
                if "function_call" in parsed:
                    func_call = parsed["function_call"]
                    
                    # Convert to OpenAI-style tool call format
                    tool_call = {
                        "id": "call_ollama_1",
                        "type": "function",
                        "function": {
                            "name": func_call["name"],
                            "arguments": json.dumps(func_call["arguments"])
                        }
                    }
                    
                    result["choices"][0]["message"]["tool_calls"] = [tool_call]
                    result["choices"][0]["message"]["content"] = None
                    
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse function call from Ollama response: {e}")
            # Keep original content as-is
        
        return result