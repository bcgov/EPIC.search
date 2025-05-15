import streamlit as st
import requests
import numpy as np
import pandas as pd

from search_api.services.synthesizer import generate_response


def search_api(query):
    """Function to call an external API for document search."""
    url = "http://localhost:3200/api/search"  # Replace with the actual API endpoint
    payload = {"question": query}
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
                st.write(
                    "Error:",
                    results["error"],
                    "(Status Code:",
                    results["status_code"],
                    ")",
                )
                return

            data = np.array(results.get("documents", []))
            response = generate_response(question=query, documents=results)

            st.subheader("Response:")
            st.write(response.response)

            st.subheader("References:")
            result = []

            for row in data:
                result.append(
                    {
                        "document_name": row.get("document_saved_name"),
                        "page_number": row.get("page_number"),
                    }
                )

            df = pd.DataFrame(result)
            st.table(df)
        else:
            st.write("Please enter a query.")


if __name__ == "__main__":
    main()
