from typing import Any
import ollama
from flask import current_app


class LLMFactory:
    def __init__(self, provider: str):
        self.provider = provider

    def generate(
        self, prompt, **kwargs
    ) -> Any:
       
        return ollama.generate(model = self.provider,prompt = prompt, options =  { "temperature" :current_app.config['LLM_TEMPERATURE']})