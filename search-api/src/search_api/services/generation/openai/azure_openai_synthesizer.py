import os
import logging
from typing import Dict, Any, List
from openai import AzureOpenAI
from openai import APIError, APIConnectionError, APITimeoutError, RateLimitError
from ..llm_synthesizer import LLMSynthesizer

# Set up logging
logger = logging.getLogger(__name__)

class AzureOpenAISynthesizer(LLMSynthesizer):
    @classmethod
    def format_documents_for_context(cls, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return super().format_documents_for_context(documents)

    @classmethod
    def create_prompt(cls, query: str, formatted_documents: List[Dict[str, Any]]) -> str:
        return super().create_prompt(query, formatted_documents)
    
    @staticmethod    
    def query_llm(prompt: str) -> Dict[str, Any]:
        """Query Azure OpenAI with the given prompt.
        
        Args:
            prompt (str): The formatted prompt to send to the model
            
        Returns:
            Dict[str, Any]: The model's response containing the generated text
            
        Note:
            This method uses environment variables for configuration:
            - AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
            - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL
            - AZURE_OPENAI_DEPLOYMENT: The model deployment name
            - AZURE_OPENAI_API_VERSION: API version (default: 2024-02-15-preview)
            - LLM_TEMPERATURE: Temperature setting (default: 0.3)
            - LLM_MAX_TOKENS: Maximum tokens in response (default: 150)
        """
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")

        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")        
        if not deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable is required")
        
        temperature = float(os.environ.get("LLM_TEMPERATURE", 0.3))        
        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", 150))
        
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        try:
            client = AzureOpenAI(
                api_version=api_version,
                api_key=api_key,
                azure_endpoint=endpoint               
            )

            messages = [
                {"role": "system", "content": "You are an AI assistant for employees in FAQ system. Your task is to synthesize coherent and helpful answers based on the given question and relevant context from a knowledge database."},
                {"role": "user", "content": prompt}
            ]            

            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens                
            )
            
            return {"response": response.choices[0].message.content}
        
        except APIConnectionError as e:
            error_msg = (
                f"Connection Error: Unable to connect to Azure OpenAI.\n"
                f"Endpoint: {endpoint}\n"
                f"Details: {str(e)}\n"
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

        except APITimeoutError as e:
            error_msg = f"Timeout Error: Request to Azure OpenAI timed out. Details: {str(e)}"
            logger.error(error_msg)
            raise TimeoutError(error_msg) from e

        except RateLimitError as e:
            error_msg = f"Rate Limit Error: Azure OpenAI quota exceeded. Details: {str(e)}"
            logger.error(error_msg)
            raise RateLimitError(error_msg) from e

        except APIError as e:
            error_msg = (
                f"Azure OpenAI API Error:\n"
                f"Status: {e.status_code if hasattr(e, 'status_code') else 'Unknown'}\n"
                f"Details: {str(e)}"
            )
            logger.error(error_msg)
            raise APIError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error in Azure OpenAI request: {str(e)}"
            logger.error(error_msg, exc_info=True)  # Include stack trace
            raise

    @staticmethod
    def format_llm_response(documents: List[Dict[str, Any]], response: Dict[str, Any]) -> Dict[str, Any]:
        return {"documents": documents, "response": response.get("response")}
