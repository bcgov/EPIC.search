import { useState } from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Box,
} from "@mui/material";
import {
  ForestTwoTone,
  FolderOpenTwoTone,
  ExpandMore,
} from "@mui/icons-material";
import AssuredWorkloadOutlinedIcon from '@mui/icons-material/AssuredWorkloadOutlined';
import { BCDesignTokens } from "epic.theme";

const sections = [
  {
    id: "environmental",
    title: "Environmental Impacts",
    icon: <ForestTwoTone sx={{ color: BCDesignTokens.iconsColorSuccess }} />,
    content: [
      {
        heading: "Here are some examples of questions you can ask our AI document search:",
        text: `How will [project name] affect local water quality and aquatic ecosystems?\n\nWhat are the projected greenhouse gas emissions for [project name]?\n\nWhat mitigation measures are required for protecting wildlife habitats in the [project name] certificate?`,
      },
    ],
  },
  {
    id: "regulatory",
    title: "Regulatory Compliance",
    icon: <AssuredWorkloadOutlinedIcon sx={{ color: BCDesignTokens.iconsColorWarning }} />,
    content: [
      {
        heading: "Compliance Requirements",
        text: "Certificate holders must comply with all conditions outlined in their Environmental Assessment Certificate. Compliance reports document how projects meet these requirements over time.",
      },
      {
        heading: "Finding Compliance Documents",
        text: 'Search for "compliance reports," "certificate conditions," or "annual reports" to track how projects are meeting their regulatory obligations. These are typically published annually.',
      },
      {
        heading: "Understanding Amendments",
        text: "Amendment documents detail changes to original project approvals. These may include modifications to project scope, mitigation measures, or monitoring requirements.",
      },
    ],
  },
  {
    id: "project",
    title: "Project Information",
    icon: <FolderOpenTwoTone sx={{ color: BCDesignTokens.iconsColorInfo }} />,
    content: [
      {
        heading: "Project Descriptions",
        text: "Project description documents provide detailed information about proposed developments, including location, scope, timeline, and key components. These are typically the first documents filed in the assessment process.",
      },
      {
        heading: "Assessment Reports",
        text: "Assessment reports synthesize information from the EA process, including technical studies, public input, and Indigenous consultation. They form the basis for certificate decisions.",
      },
      {
        heading: "Public Participation",
        text: "Public comment period summaries capture stakeholder feedback on proposed projects. These documents provide insight into community concerns and how they were addressed in the assessment.",
      },
    ],
  },
];

const SearchLandingAccordion = () => {
  const [openSections, setOpenSections] = useState<string[]>([]);

  const toggleSection = (id: string) => {
    setOpenSections((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  return (
    <Box
      sx={{
        mt: 2,
        width: "100%",
        border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
        borderRadius: 2,
        bgcolor: "white",
        overflow: "hidden",
      }}
    >
      <Box sx={{ p: 4 }}>
        <Typography variant="h5" sx={{ mb: 2, fontWeight: 600 }}>
          Help & Tips
        </Typography>
        <Typography
          variant="body2"
          color={BCDesignTokens.themeGray80}
          sx={{ mb: 3 }}
        >
          Learn more about environmental assessment documents and how to find the
          information you need.
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {sections.map((section) => (
            <Accordion
              key={section.id}
              expanded={openSections.includes(section.id)}
              onChange={() => toggleSection(section.id)}
              sx={{
                border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
                borderRadius: 2,
                "&:before": { display: "none" },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMore />}
                sx={{
                  px: 3,
                  py: 2,
                  "& .MuiAccordionSummary-content": { gap: 2, alignItems: "center" },
                }}
              >
                {section.icon}
                <Typography sx={{ fontWeight: 500, color: BCDesignTokens.themeGray90 }}>
                  {section.title}
                </Typography>
              </AccordionSummary>

              <AccordionDetails sx={{ px: 3, pb: 3, pt: 1, bgcolor: BCDesignTokens.themeGray10 }}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {section.content.map((item, idx) => (
                    <Box key={idx}>
                      <Typography sx={{ fontSize: "0.875rem", fontWeight: 500, mb: 0.5 }}>
                        {item.heading}
                      </Typography>
                      <Typography
                        sx={{
                          fontSize: "0.875rem",
                          color: BCDesignTokens.themeGray70,
                          whiteSpace: "pre-line",
                        }}
                      >
                        {item.text}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default SearchLandingAccordion;
