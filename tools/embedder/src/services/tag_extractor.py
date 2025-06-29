from sentence_transformers import util
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from .embedding import get_embedding

"""
Tag Extractor module for identifying relevant tags from document content.

- Extracts tags from document chunks using explicit text matching and semantic similarity
- Aggregates tags at the chunk and document level
- Uses a predefined list of tags relevant to environmental assessments and projects
- Parallelized for speed and robust for production use
"""

tags = [
    "AboriginalInterests",
    "AccessRoute",
    "AccidentsMalfunctions",
    "Acoustics",
    "AirQuality",
    "Amphibians",
    "AquaticResources",
    "AquaticUse",
    "Address",
    "BenthicInvertebrates",
    "Birds",
    "BorderDistance",
    "ClimateChange",
    "Coaxial",
    "Communities",
    "CommunityWellbeing",
    "Conditions",
    "ContactDetails",
    "Corridors",
    "Culture",
    "CulturalEffects",
    "CulturalSites",
    "Dates",
    "DisturbanceArea",
    "Diversity",
    "DrinkingWater",
    "EconEffects",
    "Economy",
    "Ecosystems",
    "EmployeePrograms",
    "Employment",
    "EmploymentIncome",
    "EnvEffects",
    "EnvOnProject",
    "FNAgreements",
    "FNCommunities",
    "FNInterests",
    "FNTerritories",
    "Finance",
    "FishHabitat",
    "FreshwaterFish",
    "GHG",
    "Geologic",
    "GovEngagement",
    "GreenhouseGas",
    "GWQuality",
    "GWQuantity",
    "Harvesting",
    "Health",
    "HealthEffects",
    "Heritage",
    "HeritageResources",
    "HousingAccommodation",
    "HumanHealth",
    "Income",
    "Infrastructure",
    "L&RUTradPurposes",
    "Labour",
    "LabourForce",
    "LandResourceUse",
    "LandUse",
    "Landmarks",
    "Licenses",
    "Location",
    "Mammals",
    "MarineMammals",
    "MarineResources",
    "MarineSediment",
    "MarineTransportUse",
    "MarineUse",
    "MarineWater",
    "Noise",
    "Objective",
    "OverheadCable",
    "Parks",
    "PersonalInfo",
    "PowerLine",
    "ProjectType",
    "ProponentAddress",
    "ProponentContact",
    "ProponentName",
    "PropertyValues",
    "ProtectedAreas",
    "PublicEngagement",
    "RarePlants",
    "Recreation",
    "RecreationSites",
    "ReserveLands",
    "ResourceUse",
    "Risks",
    "Roads",
    "SensitiveAreas",
    "ServicesInfrastructure",
    "SocialEffects",
    "SoilQuality",
    "SoilQuantity",
    "SurfWaterQuality",
    "SurfWaterQuantity",
    "Telecommunication",
    "TelephoneLine",
    "Terrain",
    "TransmissionLine",
    "TransmissionTower",
    "TransportationAccess",
    "TreatyLands",
    "Vegetation",
    "Vibration",
    "VisualQuality",
    "Waterbodies",
    "Wildlife",
    "WildlifeHabitat",
    "WorkforceDev"
]


def get_tag_embeddings():
    """
    Generate embeddings for the predefined list of tags.
    
    Creates vector embeddings for all tags in the predefined tag list,
    which can then be used for semantic similarity comparisons.
    
    Returns:
        list: A list of vector embeddings corresponding to each tag in the tags list
    """
    embeddings = get_embedding(tags)
    return embeddings


def process_chunk(chunk_dict, tag_embeddings, threshold=0.6):
    """
    Process a single document chunk to find matching tags.
    
    This function identifies tags that match the chunk content using two methods:
    1. Explicit matching - finding tags that appear as substrings in the text
    2. Semantic matching - finding tags with embeddings similar to the chunk embedding
    
    Args:
        chunk_dict (dict): Dictionary containing chunk data (id, metadata, content, embedding)
        tag_embeddings (list): List of vector embeddings for predefined tags
        threshold (float, optional): Similarity threshold for semantic matching. Defaults to 0.6.
        
    Returns:
        tuple: A tuple containing:
            - record_id: ID of the chunk
            - chunk_metadata: Metadata associated with the chunk
            - chunk_text: Text content of the chunk
            - chunk_embedding: Vector embedding of the chunk
            - explicit_matches: List of tags found through explicit text matching
            - semantic_matches: List of tags found through semantic similarity
            - all_matches: Combined list of unique tags from both matching methods
    """
    # Extract data from dictionary
    record_id = chunk_dict.get('id')
    chunk_metadata = chunk_dict.get('metadata', {})
    chunk_text = chunk_dict.get('content', '')
    chunk_embedding = chunk_dict.get('embedding')
    
    # Ensure embedding is in the proper format for cosine similarity
    if isinstance(chunk_embedding, str):
        print(f"Warning: Embedding is a string for record {record_id}. Skipping.")
        return (record_id, chunk_metadata, chunk_text, None, [], [], [])
    
    text_lower = chunk_text.lower()
    explicit_matches = [tag for tag in tags if tag.lower() in text_lower]
    
    # Only compute semantic matches if we have a valid embedding
    semantic_matches = []
    if chunk_embedding is not None:
        try:
            similarities = util.cos_sim(tag_embeddings, chunk_embedding)
            
            for i, score in enumerate(similarities):
                if score.item() > threshold:
                    semantic_matches.append(tags[i])
        except Exception as e:
            print(f"Error computing similarities for record {record_id}: {str(e)}")
    
    all_matches = list(set(explicit_matches + semantic_matches))

    return (
        record_id,
        all_matches
    )


def process_document_chunked(document_chunks, tag_embeddings):
    """
    Process multiple document chunks in parallel to extract tags.
    
    This function distributes the processing of document chunks across multiple threads
    to efficiently identify relevant tags for each chunk.
    
    Args:
        document_chunks (list): List of document chunk dictionaries
        tag_embeddings (list): List of vector embeddings for the predefined tags
        
    Returns:
        dict: A dictionary containing:
            - explicit_matches: Dictionary mapping chunk keys to explicit tag matches
            - semantic_matches: Dictionary mapping chunk keys to semantic tag matches
            - all_matches: Dictionary mapping chunk keys to all tag matches
            - tags_and_chunks: List of dictionaries, each containing a tag and its associated chunk data
    """
    results = {
        "all_matches": {},
        "chunks": []
    }

    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = []
        for chunk in document_chunks:
            futures.append(executor.submit(process_chunk, chunk, tag_embeddings))

        for idx, future in enumerate(futures):
            try:
                (
                    record_id,
                    all_matches,
                ) = future.result()

                # Add per-chunk info to the chunks array
                results["chunks"].append({
                    "chunk_id": record_id,
                    "all_matches": all_matches
                })
            except Exception as e:
                print(f"Error processing chunk {idx}: {str(e)}")

    # Build root-level all_matches: unique keywords across all chunks
    all_matches = set()
    for chunk in results["chunks"]:
        all_matches.update(chunk["all_matches"])
    results["all_matches"] = list(all_matches)
    
    return results


def extract_tags_from_chunks(document_chunks):
    """
    Find relevant tags in a large document using both explicit and semantic matching.
    
    This is the main entry point for extracting tags from document chunks. It first
    generates embeddings for the predefined tags, then processes each document chunk
    to find matching tags.
    
    Args:
        document_chunks (list): List of document chunk dictionaries
        
    Returns:
        dict: A dictionary of results containing tag matches and associated chunk data
    """
    tag_embeddings = get_tag_embeddings()
    return process_document_chunked(document_chunks, tag_embeddings)    


def get_tags(query: str, threshold=0.6):
    """
    Find relevant tags for a query string.
    
    This function identifies tags relevant to a query string using both
    explicit text matching and semantic similarity.
    
    Args:
        query (str): The query text to find tags for
        threshold (float, optional): Similarity threshold for semantic matching. Defaults to 0.6.
        
    Returns:
        list: A list of unique tags relevant to the query
    """
    tag_embeddings = get_embedding(tags)
    query_embedding = get_embedding([query])
    text_lower = query.lower()
    explicit_matches = [tag for tag in tags if tag.lower() in text_lower]

    similarities = util.cos_sim(tag_embeddings, query_embedding)

    semantic_matches = []
    for i, score in enumerate(similarities):
        if score.item() > threshold:
            semantic_matches.append(tags[i])

    all_matches = list(set(explicit_matches + semantic_matches))
    return all_matches
