import ollama
import os
import requests

def validate_question(question: str):
    """Generate response based on question."""

    pre_prompt_template = f"""\
            # Role and Purpose:
            This is a pre query before providing the actual context and main query to determine if the question is relevant to the context.
            Your task is to determine if the user's question is related to the context that will be provided later.

            # Guidelines:
            1. The context that will be proved later is a collection of documents related to environmental impact assessments.          
            2. Base on the question from the user, all I would like to know is wheter or not the the question is related to point 1.
            4. As an example, if the user asks "Who won the World Cup in 2018?", the answer should be "Not Relevant".
            5. As an example, if the user asks "What is the current weather in Japan?", the answer should be Not Relevant".
            6. If you think that the question may be of relevance to the context, please respond with "Relevant".
            7. The only two possible responses are "Relevant" and "Not Relevant".
           
            Review the question from the user:
            {question} 
            """

    response = generate_ollama_response(pre_prompt_template)    
    return response


def extract_document_fields(documents):
    print("###############")
    print(documents)
    print("###############")

    output = [
        {
            "project_name": item.get("project_name"),
            "proponent_name": item.get("proponent_name"),
            "text": item.get("content"),
            "page_number": item.get("page_number"),
            "document_name": item.get("document_saved_name"),
        }
        for item in documents
    ]

    return output

def refine_document_context(context):
    """Refine the document context into the required format."""
    refined_context = []
    for idx, doc in enumerate(context, start=1):
        doc_name = doc.get('document_name')
        page_number = doc.get('page_number')        
    
        doc_name_line = f"i.) Document Name: {doc_name}"
        doc_page_line = f"ii.) Page Number: {page_number}"
        doc_prop_line = f"iii.) Proponent Name: {doc.get('proponent_name')}"
        doc_proj_line = f"iv.) Project Name: {doc.get('project_name')}"
        doc_text_line = f"v.) Document Text: {doc.get('text')}"      
        
        refined_context.append(doc_name_line)
        refined_context.append(doc_page_line)
        refined_context.append(doc_prop_line)
        refined_context.append(doc_proj_line)
        refined_context.append(doc_text_line)        
    return "\n".join(refined_context)

def generate_response(question: str, documents):
    skip_llm_response = os.environ.get("SKIP_LLM_RESPONSE", "false")
    print("SKIP_LLM_RESPONSE:", skip_llm_response)

    if skip_llm_response == "true":
        return {"documents": documents, "response": "Skipped LLM Response"}

    field_array = extract_document_fields(documents)
    context = refine_document_context(field_array)

    prompt_template = f"""\
            # Role and purpose:
            Document chunks will be provided as the context.

            # Guidelines:            
            1. The context will contain multiple documents.
            2. The context will contain multiple sequences of i.) document name, ii.) page number, iii.) proponent name, iv.) project name, and v.) text representing the document chunk and information about that chunk.
            3. The user question will be provided after the context.
            4. Use only the information from the relevant context to support your answer.
            5. Never refer to "documents," "passages," "excerpts", "snippets", "provided text", "chunk" or "dataset" in your response.               
            6. Always try refer directly to the document name, proponent name, project name and page numbers directly where applicable.
            
            # Context:
            {context}
            # User question:
            {question}
            """

    response = generate_ollama_response(prompt_template)    
    processed_response = post_process_response(response.get("response"))

    return {"documents": documents, "response": processed_response}

def post_process_response(response: str) -> str:
    # Remove or cleanup any explicit in the response here
    return response.strip()
    
def generate_ollama_response(prompt_template, options=None):
    """Generate a response using Ollama with fallback mechanisms"""
    if options is None:
        options = {"temperature": 0.3, "max_tokens": 150}

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
