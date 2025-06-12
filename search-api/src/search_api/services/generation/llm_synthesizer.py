from abc import ABC, abstractmethod


class LLMSynthesizer(ABC):
    @abstractmethod
    def format_documents_for_context(documents):
        return [
            {
                "project_name": item.get("project_name"),
                "proponent_name": item.get("proponent_name"),
                "text": item.get("content"),
                "page_number": item.get("page_number"),
                "document_name": item.get("document_name")
            }
            for item in documents
        ]

    @abstractmethod
    def create_prompt(query: str, formatted_documents):
        return f"""\
            # Role and Purpose
            You are an AI assistant for employees in FAQ system. Your task is to synthesize a coherent and helpful answer 
            based on the given question and relevant context retrieved from a knowledge database.

            # Guidelines:
            1. Provide a clear and concise answer to the question. Provide answer for only asked question, do not include any additional informations
            2. Use only the information from the relevant context to support your answer.
            3. The context is retrieved based on cosine similarity, so some information might be missing or irrelevant.
            4. Be transparent when there is insufficient information to fully answer the question.
            5. Do not make up or infer information not present in the provided context.
            6. If you cannot answer the question based on the given context, clearly state that.
            7. Maintain a helpful and professional tone appropriate for customer service.
            8. Adhere strictly to company guidelines and policies by using only the provided knowledge base.
            
            Review the question from the user:
            {query}
            Provide the answer based on the following context
            {formatted_documents}
            """

    @abstractmethod
    def query_llm(query: str, context: str):
        pass

    @abstractmethod
    def format_llm_response(response):
        pass

