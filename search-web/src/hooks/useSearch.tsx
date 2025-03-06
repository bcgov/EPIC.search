import { useMutation, useQuery } from "@tanstack/react-query";
import { SearchResponse } from "@/models/Search";
import { OnErrorType, OnSuccessType, request } from "@/utils/axiosUtils";

const dummyResponse: SearchResponse = {
  result: {
    documents: [
      {
        document_id: "65f3299917680c002237d67d",
        document_type: null,
        document_name: "8870541aefa421ff1ea2e164d658d374.pdf",
        document_saved_name: "20231228-CoyoteH-SummaryOfEngagement FINAL.pdf",
        page_number: "10",
        project_id: "650b5adc5d77c20022fb59fc",
        project_name: "Coyote Hydrogen Project",
        content:
          "of additional information, project design considerations, etc.\nTable 3: Technical Advisor Input\n|Category|Technical Advisor Input|\n|---|---|\n|Effects on Agriculture|Recommendations and suggestions directing the proponent to conduct an Agricultural Impact Assessment of the Project to determine the impacts to agriculture lands. The Project partially falls within the Agricultural Land Reserve, which is land reserved for prime agriculture land that is important and scarce in British Columbia. It is important that this project minimize its impact to the immediate and surrounding Agricultural Land Reserve farmland. The Agricultural Land Reserve is a provincial zone in which agriculture is recognized as the priority use. Farming is encouraged and non-agricultural uses are restricted. Increased truck traffic on local roads associated with the construction of the project may impede access to farmland, impact farm vehicles, increase dust, and disturb livestock.|",
      },
      {
        document_id: "65130ee0381111002240b89e",
        document_type: null,
        document_name: "d6fe758b28bbec5afd071db53a2760f2.pdf",
        document_saved_name:
          "Fortescue Coyote Hydrogen Project - Early Engagement Plan.pdf",
        page_number: "48",
        project_id: "650b5adc5d77c20022fb59fc",
        project_name: "Coyote Hydrogen Project",
        content: "suggestions directing the proponent to conduct an Agricultural Impact Assessment of the Project to determine the",
      },
      {
        document_id: "65130ee0381111002240b49e",
        document_type: null,
        document_name: "d6fe758b28bbec5afd071db53a2760f2.pdf",
        document_saved_name:
          "Fortescue Coyote Hydrogen Project - Early Engagement Plan.pdf",
        page_number: "47",
        project_id: "650b5adc5d77c20022fb59fc",
        project_name: "Coyote Hydrogen Project",
        content: "Page Chunk Content suggestions directing the proponent to conduct of the Project to determine the",
      },
      {
        document_id: "65130ee0381111002140b49e",
        document_type: null,
        document_name: "d6fe758b28bbec5afd071db53a2760f2.pdf",
        document_saved_name:
          "Mount Clifford Wind Energy Plan.pdf",
        page_number: "18",
        project_id: "650b5adc5d77c20022fb67fc",
        project_name: "Mount Clifford Wind Energy",
        content: "Page Chunk Content....",
      },
      {
        document_id: "65130ee0381111001240b49e",
        document_type: null,
        document_name: "d6fe758b28bbec5afd071db53a2760f2.pdf",
        document_saved_name:
          "Fortescue Mount Clifford Wind Energy Report.pdf",
        page_number: "46",
        project_id: "650b5adc5d77c20022fb67fc",
        project_name: "Mount Clifford Wind Energy",
        content: "Page Chunk Content....",
      },
      {
        document_id: "65130ee0386111001240b49e",
        document_type: null,
        document_name: "d6fe758b28bbec5afd071db53a2760f2.pdf",
        document_saved_name:
          "Arctos Anthracite - Early Engagement Plan.pdf",
        page_number: "36",
        project_id: "650b5adc5d07c20022fb67fc",
        project_name: "Arctos Anthracite",
        content: "Page Chunk Content....",
      },
    ],
    response:
      "The Coyote Hydrogen Project may have an impact on local flora due to its potential effects on agriculture lands. According to the Technical Advisor Input, the project partially falls within the Agricultural Land Reserve, which is land reserved for prime agriculture land that is important and scarce in British Columbia. The project aims to minimize its impact on these lands by conducting an Agricultural Impact Assessment.",
  },
};

const dummySearch = (searchText: string) => {
  console.log("searchText", searchText);
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(dummyResponse);
    }, 1000);
  });
};

const doSearch = (searchText: string) => {
  return request({ url: "/search", method: "post" , data: {
    question: searchText
  }});;
};

export const useSearchData = (searchText: string) => {
  return useQuery({
    queryKey: ["search"],
    queryFn: () => dummySearch(searchText),
    enabled: !!searchText,
  });
};

export const useSearchQuery = (onSuccess: OnSuccessType, onError: OnErrorType) => {
  return useMutation({
    mutationFn: doSearch,
    onSuccess,
    onError
  })
};
