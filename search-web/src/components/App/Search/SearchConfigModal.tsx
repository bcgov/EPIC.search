import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  RadioGroup,
  FormControlLabel,
  Radio,
  Typography,
  Box,
  IconButton,
  Tooltip,
  Divider,
} from "@mui/material";
import { Close, HelpOutline } from "@mui/icons-material";
import { BCDesignTokens } from "epic.theme";
import { useState } from "react";
import { SearchStrategy } from "@/hooks/useSearch";
import { searchStrategyOptions } from "@/utils/searchConfig";

interface SearchConfigModalProps {
  open: boolean;
  onClose: () => void;
  currentStrategy: SearchStrategy | undefined;
  onSave: (strategy: SearchStrategy | undefined) => void;
}

const SearchConfigModal = ({ 
  open, 
  onClose, 
  currentStrategy, 
  onSave 
}: SearchConfigModalProps) => {
  const [selectedStrategy, setSelectedStrategy] = useState<SearchStrategy | undefined>(currentStrategy);
  const [showHelp, setShowHelp] = useState<string | null>(null);

  const handleSave = () => {
    onSave(selectedStrategy);
    onClose();
  };

  const handleCancel = () => {
    setSelectedStrategy(currentStrategy);
    setShowHelp(null);
    onClose();
  };

  const toggleHelp = (value: string) => {
    setShowHelp(showHelp === value ? null : value);
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          maxHeight: "80vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
          pb: 2,
        }}
      >
        <Typography variant="h5" color={BCDesignTokens.themePrimaryBlue}>
          Search Configuration
        </Typography>
        <IconButton onClick={handleCancel} size="small">
          <Close />
        </IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ py: 3 }}>
        <Typography variant="body1" sx={{ mb: 3, color: BCDesignTokens.themeGray80 }}>
          Configure your search strategy to optimize results for different types of queries.
        </Typography>

        <Typography variant="h6" sx={{ mb: 2, color: BCDesignTokens.themePrimaryBlue }}>
          Search Strategy
        </Typography>

        <RadioGroup
          value={selectedStrategy || ""}
          onChange={(e) => setSelectedStrategy(e.target.value as SearchStrategy || undefined)}
        >
          {searchStrategyOptions.map((option) => (
            <Box key={option.value || "default"} sx={{ mb: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <FormControlLabel
                  value={option.value || ""}
                  control={<Radio />}
                  label={option.label}
                  sx={{ flex: 1 }}
                />
                <Tooltip title="Click for more information">
                  <IconButton
                    size="small"
                    onClick={() => toggleHelp(option.value || "default")}
                    sx={{ 
                      color: BCDesignTokens.themeBlue70,
                      "&:hover": { color: BCDesignTokens.themeBlue90 }
                    }}
                  >
                    <HelpOutline fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              {showHelp === (option.value || "default") && (
                <Box
                  sx={{
                    ml: 4,
                    p: 2,
                    mt: 1,
                    backgroundColor: BCDesignTokens.themeBlue10,
                    borderRadius: 1,
                    border: `1px solid ${BCDesignTokens.themeBlue30}`,
                  }}
                >
                  <Typography variant="body2" color={BCDesignTokens.themeGray80}>
                    {option.description}
                  </Typography>
                </Box>
              )}
            </Box>
          ))}
        </RadioGroup>

        <Divider sx={{ my: 3 }} />

        <Typography variant="body2" sx={{ color: BCDesignTokens.themeGray70, fontStyle: "italic" }}>
          Your search strategy preference will be saved locally and applied to all future searches.
        </Typography>
      </DialogContent>

      <DialogActions
        sx={{
          borderTop: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
          p: 2,
          gap: 1,
        }}
      >
        <Button
          onClick={handleCancel}
          variant="outlined"
          sx={{
            borderColor: BCDesignTokens.themeGray40,
            color: BCDesignTokens.themeGray80,
            "&:hover": {
              borderColor: BCDesignTokens.themeGray60,
              backgroundColor: BCDesignTokens.themeGray10,
            },
          }}
        >
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          sx={{
            backgroundColor: BCDesignTokens.themePrimaryBlue,
            "&:hover": {
              backgroundColor: BCDesignTokens.themeBlue80,
            },
          }}
        >
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SearchConfigModal;
