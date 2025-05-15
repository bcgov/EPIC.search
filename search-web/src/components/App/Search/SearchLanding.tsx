import {
  ForestTwoTone,
  ImportContactsTwoTone,
  WorkspacePremiumTwoTone,
} from "@mui/icons-material";
import { Typography } from "@mui/material";
import { Box } from "@mui/material";
import { BCDesignTokens } from "epic.theme";

const innerBoxStyle = {
  display: "flex",
  flexDirection: "row",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 1,
  py: 4,
  px: 6,
  borderRadius: "16px",
  border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
};

const iconStyle = {
  fontSize: 100,
  color: BCDesignTokens.iconsColorPrimary,
  px: 8,
};

const staticPoints = [
  {
    title: "Environmental Impacts",
    descriptions: [
      "How will this project affect local water quality and aquatic ecosystems?",
      "What are the projected greenhouse gas emissions for this project?",
      "What mitigation measures are required for protecting wildlife habitats?",
    ],
    icon: (
      <ForestTwoTone
        sx={{ ...iconStyle, color: BCDesignTokens.iconsColorSuccess }}
      />
    ),
    background: BCDesignTokens.supportSurfaceColorSuccess,
  },
  {
    title: "Regulatory Compliance & Permitting",
    descriptions: [
      "What conditions must the proponent meet before project construction?",
      "What are the key compliance requirements under the Environmental Assessment Certificate?",
      "What are the documents proponents must submit like environmental management plan?",
    ],
    icon: (
      <WorkspacePremiumTwoTone
        sx={{ ...iconStyle, color: BCDesignTokens.iconsColorWarning }}
      />
    ),
    background: BCDesignTokens.themeGold10,
  },
  {
    title: "Project Information",
    descriptions: [
      "Who is the proponent of the project?",
      "When was the project approved?",
      "What is the Environmental Assessment Certificate number for project?",
    ],
    icon: (
      <ImportContactsTwoTone
        sx={{ ...iconStyle, color: BCDesignTokens.iconsColorInfo }}
      />
    ),
    background: BCDesignTokens.themeBlue10,
  },
];

const SearchLanding = () => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        mt: 2,
        width: "100%",
      }}
    >
      {staticPoints.map((point, index) => (
        <Box
          sx={{
            ...innerBoxStyle,
            flexDirection: index % 2 === 0 ? "row" : "row-reverse",
            textAlign: index % 2 === 0 ? "start" : "end",
            background: point.background,
          }}
          key={index}
        >
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
            <Typography variant="h4" color={BCDesignTokens.themePrimaryBlue}>
              {point.title}
            </Typography>
            {point.descriptions.map((description, index) => (
              <Typography variant="body1" key={index}>
                {description}
              </Typography>
            ))}
          </Box>
          {point.icon}
        </Box>
      ))}
    </Box>
  );
};

export default SearchLanding;
