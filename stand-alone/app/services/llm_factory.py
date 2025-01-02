from typing import Any
import ollama
from app.config.settings import get_settings


class LLMFactory:
    def __init__(self, provider: str):
        self.provider = provider
        self.settings = get_settings()


    def generate(
        self, prompt, **kwargs
    ) -> Any:
       
        return ollama.generate(model = self.provider,prompt = prompt, options =  { "temperature" :self.settings.llm_settings.temperature})