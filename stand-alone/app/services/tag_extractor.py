from sentence_transformers import SentenceTransformer, util
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from app.services.embedding import get_embedding
tags = [
"AboriginalInterests",
"AccessRoute",
"AccidentsMalfunctions",
"Acoustics",
"AirQuality",
"Amphibians",
"AquaticResources",
"AquaticUse",
"BenthicInvertebrates",
"Birds",
"BorderDistance",
"ClimateChange",
"Coaxial",
"Communities",
"CommunityWellbeing",
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

def load_model():
    """Load the Sentence Transformer model."""
    return SentenceTransformer('all-MiniLM-L6-v2')

def get_tag_embeddings():
    """Precompute tag embeddings to avoid redundant computation."""

    embeddings = get_embedding(tags)
    return embeddings

def process_chunk(chunk_tuple, tag_embeddings, threshold=0.6):
    """
    Process a single document chunk (which is a tuple) to find explicit 
    and semantic matches.

    chunk_tuple structure:
        (record_id, chunk_metadata, text, text_embedding)
    """
    # Unpack the tuple
    record_id, chunk_metadata, chunk_text, chunk_embedding = chunk_tuple

    # --- 1. Explicit search ------------------------------------
    #    Match tags that literally appear in the text (case-insensitive).
    text_lower = chunk_text.lower()
    explicit_matches = [tag for tag in tags if tag.lower() in text_lower]

    # --- 2. Semantic search ------------------------------------
    #    If chunk_embedding is already computed and compatible with your model,
    #    you can use it directly. Otherwise, re-encode chunk_text:
    #
    #        chunk_embedding = model.encode(chunk_text, convert_to_tensor=True)
    #
    #    Below assumes chunk_embedding is valid for cos_sim with tag_embeddings.
    similarities = util.cos_sim(tag_embeddings, chunk_embedding)

    # Identify semantic matches above the threshold
    semantic_matches = []
    for i, score in enumerate(similarities):
        if score.item() > threshold:
            semantic_matches.append(tags[i])

    # Combine explicit and semantic matches
    all_matches = list(set(explicit_matches + semantic_matches))

    return (record_id, chunk_metadata, chunk_text, chunk_embedding,
            explicit_matches, semantic_matches, all_matches)

def process_document_chunked(document_chunks, model, tag_embeddings):
    """
    Process the document by iterating over each chunk (tuple).
    Returns a dictionary that includes explicit, semantic, and combined 
    matches per chunk, as well as a list of (tag, chunk_id, text, embedding).
    """
    results = {
        "explicit_matches": {},
        "semantic_matches": {},
        "all_matches": {},
        "tags_and_chunks": []  # to store (tag, chunk_id, text, embedding)
    }

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = []
        for idx, chunk_tuple in enumerate(document_chunks):
            futures.append(
                executor.submit(process_chunk, chunk_tuple, tag_embeddings)
            )
        
        for idx, future in enumerate(futures):
            (record_id,
             chunk_metadata,
             chunk_text,
             chunk_embedding,
             explicit_matches,
             semantic_matches,
             all_matches) = future.result()

            chunk_key = f"Chunk_{idx + 1}"

            # Store matches by chunk in results
            results["explicit_matches"][chunk_key] = explicit_matches
            results["semantic_matches"][chunk_key] = semantic_matches
            results["all_matches"][chunk_key] = all_matches

            # Also record each (tag, chunk_id, text, embedding) in tags_and_chunks
            for tag in all_matches:
                results["tags_and_chunks"].append({
                    "tag": tag,
                    "chunk_id": record_id,
                    "chunk_metadata" : chunk_metadata,
                    "chunk_text": chunk_text,
                    "chunk_embedding": chunk_embedding
                })

    return results

def explicit_and_semantic_search_large_document(document_chunks):
    """Main function to perform explicit and semantic similarity search."""

    model = load_model()
    tag_embeddings = get_tag_embeddings()
    
    # If your chunks don't already have embeddings in the tuple, you
    # might generate them here before calling process_document_chunked:
    #
    # augmented_chunks = []
    # for (record_id, metadata, text) in original_chunks:
    #     text_embedding = model.encode(text, convert_to_tensor=True)
    #     augmented_chunks.append((record_id, metadata, text, text_embedding))
    #
    # results = process_document_chunked(augmented_chunks, model, tag_embeddings)

    # Assuming document_chunks already has the structure 
    # (record_id, metadata, text, text_embedding):
    results = process_document_chunked(document_chunks, model, tag_embeddings)
    return results


def get_tags(query: str, threshold=0.6): 


    tag_embeddings = get_embedding(tags)
    query_embedding = get_embedding([query])
    text_lower = query.lower()
    explicit_matches = [tag for tag in tags if tag.lower() in text_lower]

    similarities = util.cos_sim(tag_embeddings, query_embedding)

    # Identify semantic matches above the threshold
    semantic_matches = []
    for i, score in enumerate(similarities):
        if score.item() > threshold:
            semantic_matches.append(tags[i])

    all_matches = list(set(explicit_matches + semantic_matches))
    return all_matches
