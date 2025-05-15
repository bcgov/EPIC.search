from sentence_transformers import util
import multiprocessing

from concurrent.futures import ThreadPoolExecutor
from .embedding import get_embedding

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
    "WorkforceDev",
]


def get_tag_embeddings():
    embeddings = get_embedding(tags)
    return embeddings


def process_chunk(chunk_tuple, tag_embeddings, threshold=0.6):
    record_id, chunk_metadata, chunk_text, chunk_embedding = chunk_tuple
    text_lower = chunk_text.lower()
    explicit_matches = [tag for tag in tags if tag.lower() in text_lower]
    similarities = util.cos_sim(tag_embeddings, chunk_embedding)

    semantic_matches = []
    for i, score in enumerate(similarities):
        if score.item() > threshold:
            semantic_matches.append(tags[i])

    all_matches = list(set(explicit_matches + semantic_matches))

    return (
        record_id,
        chunk_metadata,
        chunk_text,
        chunk_embedding,
        explicit_matches,
        semantic_matches,
        all_matches,
    )


def process_document_chunked(document_chunks, tag_embeddings):
    results = {
        "explicit_matches": {},
        "semantic_matches": {},
        "all_matches": {},
        "tags_and_chunks": [],
    }

    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = []
        for idx, chunk_tuple in enumerate(document_chunks):
            futures.append(executor.submit(process_chunk, chunk_tuple, tag_embeddings))

        for idx, future in enumerate(futures):
            (
                record_id,
                chunk_metadata,
                chunk_text,
                chunk_embedding,
                explicit_matches,
                semantic_matches,
                all_matches,
            ) = future.result()

            chunk_key = f"Chunk_{idx + 1}"

            results["explicit_matches"][chunk_key] = explicit_matches
            results["semantic_matches"][chunk_key] = semantic_matches
            results["all_matches"][chunk_key] = all_matches

            for tag in all_matches:
                results["tags_and_chunks"].append(
                    {
                        "tag": tag,
                        "chunk_id": record_id,
                        "chunk_metadata": chunk_metadata,
                        "chunk_text": chunk_text,
                        "chunk_embedding": chunk_embedding,
                    }
                )

    return results


def explicit_and_semantic_search_large_document(document_chunks):
    tag_embeddings = get_tag_embeddings()
    results = process_document_chunked(document_chunks, tag_embeddings)
    return results


def get_tags(query: str, threshold=0.6):
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
