"""
Environmental Assessment Tags List

This module contains the predefined list of tags used for document classification
and tag extraction in the EPIC search system. These tags represent various
environmental, social, and economic aspects commonly found in environmental
assessment documents.

Tags are organized alphabetically and cover domains including:
- Environmental effects (air quality, water quality, wildlife, etc.)
- Social and cultural impacts (communities, health, employment, etc.)
- Project specifics (location, type, infrastructure, etc.)
- First Nations interests and agreements
- Regulatory and compliance aspects
"""

# Complete list of environmental assessment tags
TAGS = [
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

# Legacy alias for backward compatibility
tags = TAGS

def get_tags_list():
    """
    Returns the complete list of environmental assessment tags.
    
    Returns:
        list: List of tag strings used for document classification
    """
    return TAGS.copy()

def get_tags_count():
    """
    Returns the total number of available tags.
    
    Returns:
        int: Number of tags in the list
    """
    return len(TAGS)
