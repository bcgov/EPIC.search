from datetime import datetime
from app.database.vector_store import VectorStore
from app.services.synthesizer import Synthesizer
from timescale_vector import client
import numpy as np
from app.config.settings import get_settings
# Initialize VectorStore

def main():

    vec = VectorStore()

    # --------------------------------------------------------------
    # question
    # --------------------------------------------------------------

    #search on tag embeddings
    relevant_question = "project names that affects Fish Habitat?"
    settings =  get_settings()
    results = vec.hybrid_search(settings.vector_store.table_name,relevant_question,  keyword_k=50, semantic_k=50, rerank=True, top_n=10)
    data = np.array(results) 

    combined_text = " ".join(data[:, 1])
    response = Synthesizer.generate_response(question=relevant_question, context=combined_text)
    print(f"\n{response.response}")
    result = []

    for row in data:
        # row[4] contains the metadata dictionary
        metadata = row[4]
        
        # Extract values from the metadata dictionary
        document_name = metadata.get("document_name")
        page_number = metadata.get("page_number")
        
        # Append to a list or process as needed
        result.append({
            "document_name": document_name,
            "page_number": page_number
        })

    # Print or otherwise use the results
    for item in result:
        print(f"Document: {item['document_name']}, Page: {item['page_number']}")
   

if __name__ == "__main__":
    main()
