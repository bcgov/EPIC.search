import os
from ..llm_synthesizer import LLMSynthesizer
from .ollama_factory import OllamaFactory


class OllamaSynthesizer(LLMSynthesizer):
    @classmethod
    def format_documents_for_context(cls, documents):
        return super().format_documents_for_context(documents)

    @classmethod
    def create_prompt(cls, query, formatted_documents):
        return super().create_prompt(query, formatted_documents)

    @staticmethod
    def query_llm(prompt: str):

        llm_temperature = float(os.environ.get("LLM_TEMPERATURE", 0.3))
        llm_max_tokens = int(os.environ.get("LLM_MAX_TOKENS", 150))
        llm_max_context_length = int(os.environ.get("LLM_MAX_CONTEXT_LENGTH", 4096))
        llm_model = os.environ.get("LLM_MODEL", "llama3.1:8b")

        print("LLM_TEMPERATURE:", llm_temperature)
        print("LLM_MODEL:", llm_model)
        print("LLM_MAX_TOKENS:", llm_max_tokens)
        print("LLM_MAX_CONTEXT_LENGTH:", llm_max_context_length)

        options = {
            "temperature": llm_temperature,
            "num_predict": llm_max_tokens,
            "num_ctx": llm_max_context_length,
        }

        response = OllamaFactory(llm_model).generate(prompt=prompt, options=options)
        return response

    @staticmethod
    def format_llm_response(documents, response):
        return {"documents": documents, "response": response.get("response")}
