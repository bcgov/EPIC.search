import { Chip } from "@mui/material";
import { BCDesignTokens, EAOColors } from "epic.theme";

export type DocumentType =
  | "Request"
  | "Letter"
  | "Meeting Notes"
  | "Comment Period"
  | "Plan"
  | "Report/Study"
  | "Decision Materials"
  | "Order"
  | "Project Descriptions"
  | "Application Information Requirement"
  | "Application Materials"
  | "Certificate Package"
  | "Exception Package"
  | "Amendment Package"
  | "Inspection Record"
  | "Other"
  | "Comment/Submission"
  | "Tracking Table"
  | "Scientific Memo"
  | "Agreement"
  | "Project Description"
  | "Independent Memo"
  | "Management Plan"
  | "Ad/News Release"
  | "Notification"
  | "Amendment Information"
  | "Presentation"
  | "Process Order Materials";

type StyleProps = {
  label: string;
  sx: Record<string, string | number>;
  iconColor: string;
};

/**
 * Shared base style
 */
const baseChipStyles = {
  height: "22px",
  fontSize: "0.7rem",
  fontWeight: 500,
  borderRadius: "8px",
};

const defaultIconColor = BCDesignTokens.themeGray70;

/**
 * Document type → style mapping
 */
const documentTypeStyles: Record<DocumentType, StyleProps> = {
  Request: {
    label: "Request",
    iconColor: BCDesignTokens.themeBlue60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeBlue60}`,
      backgroundColor: BCDesignTokens.themeBlue20,
    },
  },
  Letter: {
    label: "Letter",
    iconColor: BCDesignTokens.themeGray60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGray60}`,
      backgroundColor: BCDesignTokens.themeGray20,
    },
  },
  "Meeting Notes": {
    label: "Meeting Notes",
    iconColor: EAOColors.DecisionDark,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${EAOColors.DecisionDark}`,
      backgroundColor: EAOColors.DecisionLight,
    },
  },
  "Comment Period": {
    label: "Comment Period",
    iconColor: BCDesignTokens.supportBorderColorWarning,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.supportBorderColorWarning}`,
      backgroundColor: BCDesignTokens.supportSurfaceColorWarning,
    },
  },
  Plan: {
    label: "Plan",
    iconColor: "#F18A15",
    sx: {
      ...baseChipStyles,
      border: `1px solid #F18A15`,
      backgroundColor: "#FFDEB8",
    },
  },
  "Report/Study": {
    label: "Report / Study",
    iconColor: BCDesignTokens.themeBlue80,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeBlue80}`,
      backgroundColor: BCDesignTokens.themeBlue10,
    },
  },
  "Decision Materials": {
    label: "Decision",
    iconColor: "#6B21A8",
    sx: {
      ...baseChipStyles,
      border: `1px solid #E9D5FF`,
      backgroundColor: "#F3E8FF",
    },
  },
  Order: {
    label: "Order",
    iconColor: BCDesignTokens.supportBorderColorDanger,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.supportBorderColorDanger}`,
      backgroundColor: BCDesignTokens.supportSurfaceColorDanger,
    },
  },
  "Project Descriptions": {
    label: "Project Description",
    iconColor: BCDesignTokens.themeBlue50,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeBlue50}`,
      backgroundColor: BCDesignTokens.themeBlue10,
    },
  },
  "Application Information Requirement": {
    label: "AIR",
    iconColor: BCDesignTokens.themeGold60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGold60}`,
      backgroundColor: BCDesignTokens.themeGold20,
    },
  },
  "Application Materials": {
    label: "Application",
    iconColor: BCDesignTokens.themeGold60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGold60}`,
      backgroundColor: BCDesignTokens.themeGold20,
    },
  },
  "Certificate Package": {
    label: "Certificate",
    iconColor: "#B45309",
    sx: {
      ...baseChipStyles,
      border: `1px solid #FDE68A`,
      backgroundColor: "#FEF3C7",
    },
  },
  "Exception Package": {
    label: "Exception",
    iconColor: BCDesignTokens.supportBorderColorWarning,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.supportBorderColorWarning}`,
      backgroundColor: BCDesignTokens.supportSurfaceColorWarning,
    },
  },
  "Amendment Package": {
    label: "Amendment",
    iconColor: "#9B6BDA",
    sx: {
      ...baseChipStyles,
      border: `1px solid #9B6BDA`,
      backgroundColor: "#F6E4FF",
    },
  },
  "Inspection Record": {
    label: "Inspection",
    iconColor: BCDesignTokens.themeGray70,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGray70}`,
      backgroundColor: BCDesignTokens.themeGray20,
    },
  },
  Other: {
    label: "Other",
    iconColor: BCDesignTokens.themeGray60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGray60}`,
      backgroundColor: BCDesignTokens.themeGray10,
    },
  },
  "Comment/Submission": {
    label: "Comment",
    iconColor: BCDesignTokens.themeBlue80,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.supportBorderColorInfo}`,
      backgroundColor: BCDesignTokens.themeBlue20,
    },
  },
  "Tracking Table": {
    label: "Tracking",
    iconColor: BCDesignTokens.themeGray70,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGray70}`,
      backgroundColor: BCDesignTokens.themeGray20,
    },
  },
  "Scientific Memo": {
    label: "Scientific Memo",
    iconColor: "#15803D",
    sx: {
      ...baseChipStyles,
      border: `1px solid #BBF7D0`,
      backgroundColor: "#DCFCE7",
    },
  },
  Agreement: {
    label: "Agreement",
    iconColor: "#4338CA",
    sx: {
      ...baseChipStyles,
      border: `1px solid #C7D2FE`,
      backgroundColor: "#E0E7FF",
    },
  },
  "Project Description": {
    label: "Project Description",
    iconColor: BCDesignTokens.themeBlue50,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeBlue50}`,
      backgroundColor: BCDesignTokens.themeBlue10,
    },
  },
  "Independent Memo": {
    label: "Independent Memo",
    iconColor: "#64748B",
    sx: {
      ...baseChipStyles,
      border: `1px solid #E2E8F0`,
      backgroundColor: "#F1F5F9",
    },
  },
  "Management Plan": {
    label: "Management Plan",
    iconColor: "#047857",
    sx: {
      ...baseChipStyles,
      border: `1px solid #A7F3D0`,
      backgroundColor: "#D1FAE5",
    },
  },
  "Ad/News Release": {
    label: "News",
    iconColor: BCDesignTokens.themeGold60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGold60}`,
      backgroundColor: BCDesignTokens.themeGold20,
    },
  },
  Notification: {
    label: "Notification",
    iconColor: BCDesignTokens.themeGold60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeGold60}`,
      backgroundColor: BCDesignTokens.themeGold20,
    },
  },
  "Amendment Information": {
    label: "Amendment Info",
    iconColor: "#06B6D4",
    sx: {
      ...baseChipStyles,
      border: `1px solid #99F6E4`,
      backgroundColor: "#CCFBF1",
    },
  },
  Presentation: {
    label: "Presentation",
    iconColor: BCDesignTokens.themeBlue60,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.themeBlue60}`,
      backgroundColor: BCDesignTokens.themeBlue20,
    },
  },
  "Process Order Materials": {
    label: "Process Order",
    iconColor: BCDesignTokens.supportBorderColorDanger,
    sx: {
      ...baseChipStyles,
      border: `1px solid ${BCDesignTokens.supportBorderColorDanger}`,
      backgroundColor: BCDesignTokens.supportSurfaceColorDanger,
    },
  },
};

/**
 * Default fallback style
 */
const defaultStyle: StyleProps = {
  label: "Unknown",
  iconColor: defaultIconColor,
  sx: {
    ...baseChipStyles,
    border: `1px solid ${BCDesignTokens.themeGray60}`,
    backgroundColor: BCDesignTokens.themeGray20,
  },
};

type DocumentTypeChipProps = {
  documentType?: string | null;
};

export default function DocumentTypeChip({
  documentType,
}: DocumentTypeChipProps) {
  const style =
    documentType &&
    documentTypeStyles[documentType as DocumentType]
      ? documentTypeStyles[documentType as DocumentType]
      : defaultStyle;

  return <Chip sx={style.sx} label={style.label} />;
}

/**
 * Helper to get icon color
 */
export function getDocumentTypeIconColor(documentType?: string | null) {
  if (!documentType) return defaultIconColor;

  return (
    documentTypeStyles[documentType as DocumentType]?.iconColor ??
    defaultIconColor
  );
}
