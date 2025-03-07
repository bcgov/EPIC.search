import ollama
import os
import requests


def format_llm_input(documents):
    print("###############")
    print(documents)
    print("###############")

    output = [
        {"project_name": item.get("project_name"), "text": item.get("content")}
        for item in documents
    ]

    return output


def generate_response(question: str, documents):

    skip_llm_Reponse = os.environ.get("SKIP_LLM_RESPONSE", "false")
    print("SKIP_LLM_RESPONSE:", skip_llm_Reponse)
    
    if (skip_llm_Reponse == "true"):
        return {
            "documents": documents,
            "response": "Skippped LLM Response"
        }

    context = format_llm_input(documents)
    prompt_template = f"""\
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
            {question}
            Provide the answer based on the following context:
            {context}
            """

    response = generate_ollama_response(prompt_template, {"temperature": 0})

    return {
        "documents": documents,
        "response": response.get("response")
    }    


def generate_ollama_response(prompt_template, options=None):
    """Generate a response using Ollama with fallback mechanisms"""
    if options is None:
        options = {"temperature": 0}

    # Get Ollama host from environment or use default
    host = os.environ.get("OLLAMA_HOST", "http://0.0.0.0:11434")
    requestHost = os.environ.get("OLLAMA_REQUEST_HOST", "http://localhost:11434")
    
    print("OLLAMA_HOST:", host)
    print("OLLAMA_REQUEST_HOST:", requestHost)

    # TODO - Add better error handling for requests
    try:
        response = requests.get(f"{requestHost}/api/version", timeout=5)
    except requests.exceptions.RequestException:
        return f"Ollama service not available at {requestHost})"

    try:
        response = ollama.generate(
            model="llama3.1:8b", prompt=prompt_template, options=options
        )
        return response
    except Exception as e:
        return f"Error generating with Ollama: {str(e)}"
