import numpy as np
def format_llm_input(documents):
    data = np.array(documents) 
    output = [
                {
                    "project_name": row[4].get("project_name", ""),
                    "text": row[1]
                }
                for row in data
            ]
    return output