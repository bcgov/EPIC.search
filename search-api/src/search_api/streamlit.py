import streamlit as st
import requests
import numpy as np
import pandas as pd
import ollama

def format_llm_input(documents):
    print("###############")
    print(documents)
    
    # Ensure we're accessing the list within the 'documents' key
    doc_list = documents.get("documents", [])

    output = [
        {
            "project_name": item.get("project_name"),
            "text": item.get("content")
        }
        for item in doc_list
    ]

    return output

def generate_response(question: str, documents):
        
        context= format_llm_input(documents)
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
            Provide the answer based on the following context
            {context}
            """

     
        response =ollama.generate(model = "llama3.1",prompt = prompt_template, options =  { "temperature" :0})
        return response

def search_api(query):
    """Function to call an external API for document search."""
    url = "http://localhost:3200/api/search"  # Replace with the actual API endpoint
    payload = {
        "question": query
    }
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Failed to fetch data", "status_code": response.status_code}

def main():
    st.title("EPIC.search")
    query = st.text_input("Ask a question about your documents:")
    if st.button("Search"):
        if query:
            results = search_api(query)
            if "error" in results:
                st.write("Error:", results["error"], "(Status Code:", results["status_code"], ")")
                return
            
            data = np.array(results.get("documents", [])) 
            response = generate_response(question=query, documents=results)
            
            st.subheader("Response:")
            st.write(response.response)
            
            st.subheader("References:")
            result = []

            for row in data:
               
                
                result.append({
                    "document_name": row.get("document_saved_name"),
                    "page_number": row.get("page_number"),
                })
            
            df = pd.DataFrame(result)
            st.table(df)
        else:
            st.write("Please enter a query.")

if __name__ == '__main__':
    main()
