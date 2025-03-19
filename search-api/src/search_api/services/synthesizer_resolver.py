from search_api.services.generation.llm_synthesizer import LLMSynthesizer
from search_api.services.generation.ollama.ollama_synthesizer import OllamaSynthesizer


def get_synthesizer() -> LLMSynthesizer:
    return OllamaSynthesizer()

# Extend this class to return a different type of synthesizer if needed