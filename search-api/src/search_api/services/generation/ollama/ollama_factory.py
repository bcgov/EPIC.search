import os
from typing import Any
import ollama
from flask import current_app


class OllamaFactory:
    def __init__(self, provider: str):
        self.provider = provider
        # Get host from environment variable or use default
        self.host = os.environ.get("LLM_HOST", "http://localhost:11434")
        self.client = ollama.Client(host=self.host)
        print(f"Initializing Ollama client with host: {self.host}")

    def generate(self, prompt, options) -> Any:
        try:
            return self.client.generate(model=self.provider, prompt=prompt, options=options)
        except Exception as e:
            current_app.logger.error(f"Error generating with Ollama: {str(e)}")
            return {"response": "An internal error occurred while processing the request."}            
