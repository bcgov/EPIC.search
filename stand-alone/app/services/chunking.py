import re
import numpy as np
import ollama
from app.config.settings import get_settings
from langchain.text_splitter import MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter


def chunk_text(text):
    # Split the input text into individual sentences.
    single_sentences_list = _split_sentences(text)

    # If there's only one sentence, just return it as a single chunk.
    if len(single_sentences_list) <= 1:
        return [text.strip()]
    
    # Combine adjacent sentences to form a context window around each sentence.
    combined_sentences = _combine_sentences(single_sentences_list)

    # Convert the combined sentences into vector representations using a neural network model.
    embeddings = convert_to_vector(combined_sentences)
    #If embeddings are empty or have fewer than 2 vectors, just return the text as is.
    if embeddings.size == 0 or len(embeddings) < 2:
        return [text.strip()]

    # Calculate the cosine distances between consecutive combined sentence embeddings to measure similarity.
    distances = _calculate_cosine_distances(embeddings)
    	
    # If no distances could be computed, return the entire text as a single chunk.
    if len(distances) == 0:
        return [text.strip()]
    # Determine the threshold distance for identifying breakpoints based on the 80th percentile of all distances.
    breakpoint_percentile_threshold = 80
    breakpoint_distance_threshold = np.percentile(distances, breakpoint_percentile_threshold)

    # Find all indices where the distance exceeds the calculated threshold, indicating a potential chunk breakpoint.
    indices_above_thresh = [i for i, distance in enumerate(distances) if distance > breakpoint_distance_threshold]

    # Initialize the list of chunks and a variable to track the start of the next chunk.
    chunks = []
    start_index = 0

    # Loop through the identified breakpoints and create chunks accordingly.
    for index in indices_above_thresh:
        chunk = ' '.join(single_sentences_list[start_index:index+1])
        chunks.append(chunk)
        start_index = index + 1

    # If there are any sentences left after the last breakpoint, add them as the final chunk.
    if start_index < len(single_sentences_list):
        chunk = ' '.join(single_sentences_list[start_index:])
        chunks.append(chunk)

    # Return the list of text chunks.
    return chunks

def _split_sentences(text):
    # Use regular expressions to split the text into sentences based on punctuation followed by whitespace.
    sentences = re.split(r'(?<=[.?!])\s+', text)
    return sentences

def _combine_sentences(sentences):
    # Create a buffer by combining each sentence with its previous and next sentence to provide a wider context.
    combined_sentences = []
    for i in range(len(sentences)):
        combined_sentence = sentences[i]
        if i > 0:
            combined_sentence = sentences[i-1] + ' ' + combined_sentence
        if i < len(sentences) - 1:
            combined_sentence += ' ' + sentences[i+1]
        combined_sentences.append(combined_sentence)
    return combined_sentences

def convert_to_vector(texts):
    # Try to generate embeddings for a list of texts using a pre-trained model and handle any exceptions.
    try:
        settings = get_settings()
        response = ollama.embed(
            input=texts,
            model= settings.embedding_model.model_name
        )
        embeddings = np.array([item for item in response.embeddings])
        return embeddings
    except Exception as e:
        print("An error occurred:", e)
        return np.array([])  # Return an empty array in case of an error

def _calculate_cosine_distances(embeddings):
    # Calculate the cosine distance (1 - cosine similarity) between consecutive embeddings.
    distances = []
    for i in range(len(embeddings) - 1):
        similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])
        distance = 1 - similarity
        distances.append(distance)
    return distances

def cosine_similarity(embedding_one, embedding_two):
    dot_product = np.dot(embedding_one[0], embedding_two[0])
    magnitude_one = np.linalg.norm(embedding_one[0])
    magnitude_two = np.linalg.norm(embedding_two[0])
    return dot_product / (magnitude_one * magnitude_two)


def chunk_markdown_text(text):
    headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
    ("#####", "Header 5"),
    ("######", "Header 6"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,strip_headers = False)
    text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )
    docs = splitter.split_text(text); 
    split_docs = text_splitter.split_documents(docs)
    return split_docs