from app.services.llm_factory import LLMFactory

class Synthesizer:
   
    @staticmethod
    def generate_response(question: str, context):
        prompt_template = f"""\
            # Role and Purpose
            You are an AI assistant for employees in FAQ system. Your task is to synthesize a coherent and helpful answer 
            based on the given question and relevant context retrieved from a knowledge database.

            # Guidelines:
            1. Provide a clear and concise answer to the question.
            2. Use only the information from the relevant context to support your answer.
            3. The context is retrieved based on cosine similarity, so some information might be missing or irrelevant.
            4. Be transparent when there is insufficient information to fully answer the question.
            5. Do not make up or infer information not present in the provided context.
            6. If you cannot answer the question based on the given context, clearly state that.
            7. Maintain a helpful and professional tone appropriate for customer service.
            8. Adhere strictly to company guidelines and policies by using only the provided knowledge base.
            
            Review the question from the user:
            {question}
            Provide the answer based on the following context
            {context}
            """

        llm = LLMFactory('llama3.1')
        response =llm.generate(
            prompt=prompt_template,
        )
        return response
        

    