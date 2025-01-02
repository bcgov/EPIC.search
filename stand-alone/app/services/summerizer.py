from app.services.llm_factory import LLMFactory
from transformers import pipeline
class Summerizer:
   
    @staticmethod
    def generate_summary(context :str):
        prompt_template = f"""\
            # Role and Purpose
            Summarize the following environmental assessment-related documents received by the Environmental Assessment Office (EAO) of British Columbia. The summary should provide a **detailed** and comprehensive overview of all potentially significant environmental effects or considerations noted in the materials. The final summary must not exclude any details that could impact the environment. Include all relevant points under each category provided below. Ensure the summary is **accurate**, **neutral**, and **complete**.

            Details to be Included:

            Air Quality

            - Air Quality Impacts: Increase in criteria air contaminants, VOCs, other pollutants, and potential changes in acidification, eutrophication, and odour levels.

            Noise and Vibration

            - Noise Impacts: Changes in audible and low-frequency noise levels due to project activities.
            - Vibration Impacts: Increase in vibration due to project activities.

            Surface Water

            - Surface Water Quality: Changes in acidification, eutrophication, metals, acid rock drainage, nutrients, and sedimentation.
            - Surface Water Quantity (Hydrology): Alterations to in-stream flows, runoff dynamics, and patterns.

            Groundwater

            - Groundwater Quality: Potential contamination (e.g., drilling fluids, seepage, acid mine drainage).
            - Groundwater Quantity: Changes in groundwater flow, quantity, and interactions with surface water. Consider climate change factors influencing water use.

            Marine Water and Sediment Quality

            - Marine Water Quality: Changes from existing conditions, contamination, suspended solids, turbidity, nutrients.
            - Marine Sediment Quality: Sediment disturbance and contamination from existing conditions.

            Soil

            - Soil Quality: Acidification, eutrophication, contamination, erosion, and dust accumulation.
            - Soil Quantity: Loss due to erosion, disturbance, alteration, or removal.

            Unique Geologic Landforms

            - Changes in the areal extent or condition of geologic landforms (karst, sand dunes, lava beds, caves, cliffs, outcrops, talus slopes, hot springs).

            Vegetation

            - Plant Species: Effects on provincially/federally listed plants, species of conservation concern, First Nations importance, and invasive species.
            - Plant Communities: Effects on ecological communities of conservation concern, provincially listed communities, and traditionally valued communities.
            - Wetland Functions: Effects on area and functions (hydrological, biogeochemical, habitat).

            Ecosystems

            - Effects on old forests, grasslands, alpine/subalpine, and riparian ecosystems.

            Wildlife

            - Birds: Effects on individual species, Species at Risk, species important to First Nations.
            - Mammals/Reptiles/Amphibians: Effects on habitat, habitat functionality, fragmentation, disturbance, mortality, movement, and health.

            Aquatic Resources and Freshwater Fish

            - Fish Habitat: Effects on riparian ecosystems, spawning locations, and in-stream flow.
            - Aquatic Resources: Effects on benthic invertebrates, periphyton, bioaccumulation, phytoplankton, zooplankton.
            - Fish: Effects on tissue quality, behavior, migration, health, development, Species at Risk, and traditionally important aquatic species.

            Marine Resources

            - Fish Habitat: Effects on eelgrass, kelp, and marine plants.
            - Marine Mammals: Effects on Species at Risk, behavior, underwater noise, and traditional use species.
            - Fish: Effects on species at risk, underwater noise, behavior, and species of management or traditional concern.
            - Marine Invertebrates: Effects on Species at Risk, management concern species, and traditional use species.

            Employment and Economy

            - Employment: Effects on jobs, training, labor income, and equitable access to opportunities.
            - Economy: Effects on tax revenues, government expenditures, GDP, business revenue, land and resource valuations, tourism, and cost of living.

            Land and Resource Use

            - Private Property: Effects on use and enjoyment of private properties.
            - Tenured Land and Resource Use: Effects on industrial land uses and other permitted/licensed land uses.
            - Public Land and Resource Use: Effects on hunting, fishing, trapping, gathering, recreation (camping, hiking, skiing, boating, etc.), agriculture, tourism.
            - Parks and Protected Areas: Effects on protected areas and recreation sites/trails.

            Visual Resources

            - Visual Impacts: Effects on visual landscapes and aesthetics.

            Marine Use

            - Navigation: Effects on marine navigation.
            - Tenured Marine Use: Effects on aquaculture, moorage, commercial fishing.
            - Public Marine Use: Effects on consumptive (hunting/fishing/gathering) and non-consumptive uses (boating, kayaking), tourism, and marine protected areas.

            Infrastructure and Services

            - Community Infrastructure and Services: Effects on health care, social services, emergency response, domestic water supply, sewage/water treatment, landfills, recycling, recreation facilities, education/day care, and other services.
            - Transportation Infrastructure: Effects on roads, traffic volumes.
            - Housing and Accommodation: Effects on housing availability and affordability.

            Human Health

            - Human Health Risk Assessment: Effects related to air quality, drinking/recreational water quality, noise, soil quality, quantity and quality of country foods, population health, social determinants of health.

            Archaeological and Heritage Resources

            - Historical Resources: Effects on historical/archaeological sites, cultural modified trees (CMTs), paleontological resources.
            - Cultural Health: Effects on governance, stewardship systems, customs, beliefs, values, language, knowledge transfer, and community/cultural cohesion.

            Instructions:
            Please produce a **detailed** and **comprehensive** summary integrating the points above as extracted from the provided documents. Do not omit or diminish the significance of any details related to environmental impacts. Present the information in a clear, organized manner that is suitable for review by the EAO BC and other stakeholders.

            Review the content of the documents below:
            {context}
            """
        prompt_template2 = f"""\
            # Role and Purpose
            You are an expert summarizer. Your task is to read the provided text and create a concise, comprehensive summary of its main points. You must only use information from the text itself, without adding any external knowledge or assumptions. 

            # Guidelines:
            1. Summarize the text in a clear, organized manner.
            2. Include any environmental details mentioned (e.g., impact on ecosystems, sustainability efforts, climate-related aspects).
            3. Include any significant data, events, or findings within the text.
            4.Include any personal data and all dates that appear in the text.
            5. Do not include opinions, interpretations, or information that does not appear in the text.
            6. Do not make up or infer information not present in the provided context.
            7. Do not include personal notes, disclaimers, or statements about following instructions.
            8. Do not begin with phrases like "Here is a concise summary..."—simply provide the summary.
            9. Present only the facts from the text without references to external sources or guidelines.
            
            [Text to Summarize]
            {context}
            """
        # summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        # return summarizer(context, min_length=30, do_sample=False)
        llm = LLMFactory('llama3.1')
        response =llm.generate(
            prompt=prompt_template2,
        )
        return response