import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Checkbox,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  IconButton,
  Divider
} from "@mui/material";
import { FilterList, Close } from "@mui/icons-material";
import { BCDesignTokens } from "epic.theme";
import React, { useState } from "react";
import { useProjects } from "@/hooks/useProjects";
import { useDocumentTypeMappings } from "@/hooks/useDocumentTypeMappings";
import ProjectLoadingScreen from "./ProjectLoadingScreen";
import { formatActName } from "@/utils/formatUtils";

interface FilterModalProps {
  open: boolean;
  onClose: () => void;
  selectedProjectIds: string[];
  selectedDocumentTypeIds?: string[];
  onSave: (projectIds: string[], documentTypeIds: string[]) => void;
}

const FilterModal = ({ open, onClose, selectedProjectIds, selectedDocumentTypeIds = [], onSave }: FilterModalProps) => {
  const { data: projects, isLoading, isError } = useProjects();
  const { data: docTypesData, isLoading: docTypesLoading, isError: docTypesError } = useDocumentTypeMappings(true);
  const [selectedProjects, setSelectedProjects] = useState<string[]>(selectedProjectIds);
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>(selectedDocumentTypeIds);

  // Keep modal selection in sync with parent when opening
  React.useEffect(() => {
    if (open) {
      setSelectedProjects(selectedProjectIds);
      setSelectedDocTypes(selectedDocumentTypeIds);
    }
  }, [open, selectedProjectIds, selectedDocumentTypeIds]);

  const handleToggleProject = (projectId: string) => {
    setSelectedProjects((prev) =>
      prev.includes(projectId)
        ? prev.filter((id) => id !== projectId)
        : [...prev, projectId]
    );
  };

  const handleToggleDocType = (docTypeId: string) => {
    setSelectedDocTypes((prev) =>
      prev.includes(docTypeId)
        ? prev.filter((id) => id !== docTypeId)
        : [...prev, docTypeId]
    );
  };

  const handleSave = () => {
    onSave(selectedProjects, selectedDocTypes);
    onClose();
  };

  const handleCancel = () => {
    setSelectedProjects(selectedProjectIds);
    setSelectedDocTypes(selectedDocumentTypeIds);
    onClose();
  };

  const handleClearAll = () => {
    setSelectedProjects([]);
    setSelectedDocTypes([]);
  };

return (
    <Dialog open={open} onClose={handleCancel} maxWidth="lg" fullWidth>
    <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1, pb: 1 }}>
      <FilterList sx={{ color: BCDesignTokens.themePrimaryBlue }} />
      <Typography variant="h6" component="span" sx={{ flex: 1 }}>
        Filter by Project & Document Type
      </Typography>
      <IconButton onClick={handleCancel} size="small">
        <Close />
      </IconButton>
    </DialogTitle>
    <Divider sx={{ my: 2 }} />
    <DialogContent sx={{ minHeight: 420, maxHeight: 420, p: 0, overflow: 'hidden' }}>
        <Box sx={{ display: 'flex', flexDirection: 'row', gap: 3, p: 3, height: 420, overflow: 'hidden' }}>
          {/* Projects Section */}
          <Box sx={{ width: '50%', minWidth: 0, height: '100%', maxHeight: 420, overflowY: 'auto', overflowX: 'hidden', position: 'relative' }}>
            <Box sx={{ position: 'sticky', top: 0, zIndex: 2, bgcolor: 'background.paper', pt: 0, pb: 2 }}>
              <Typography variant="body2" sx={{ color: BCDesignTokens.themeGray70 }}>
                Projects
              </Typography>
            </Box>
            {isLoading && <ProjectLoadingScreen />}
            {isError && (
              <Typography color="error">Failed to load projects. Please try again later.</Typography>
            )}
            {!isLoading && projects && (
              <List dense>
                {projects.map((project) => {
                  const isSelected = selectedProjects.includes(project.project_id);
                  return (
                    <ListItem
                      key={project.project_id}
                      button
                      onClick={() => handleToggleProject(project.project_id)}
                      selected={isSelected}
                      sx={{ borderRadius: 1, display: 'flex', alignItems: 'center' }}
                    >
                      <ListItemIcon>
                        <Checkbox
                          edge="start"
                          checked={isSelected}
                          tabIndex={-1}
                          disableRipple
                          color="primary"
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={project.project_name}
                      />
                      {isSelected && (
                        <IconButton
                          edge="end"
                          size="small"
                          aria-label={`Deselect ${project.project_name}`}
                          onClick={e => {
                            e.stopPropagation();
                            handleToggleProject(project.project_id);
                          }}
                          sx={{ ml: 1 }}
                        >
                          <Close fontSize="small" />
                        </IconButton>
                      )}
                    </ListItem>
                  );
                })}
              </List>
            )}
          </Box>
          {/* Document Types Section */}
          <Box sx={{ width: '50%', minWidth: 0, height: '100%', maxHeight: 420, overflowY: 'auto', overflowX: 'hidden', position: 'relative' }}>
            <Box sx={{ position: 'sticky', top: 0, zIndex: 2, bgcolor: 'background.paper', pt: 0, pb: 2 }}>
              <Typography variant="body2" sx={{ color: BCDesignTokens.themeGray70 }}>
                Document Types
              </Typography>
            </Box>
            {docTypesLoading && <Typography>Loading document types...</Typography>}
            {docTypesError && <Typography color="error">Failed to load document types.</Typography>}
            {!docTypesLoading && !docTypesError && (!docTypesData || !docTypesData.result || !docTypesData.result.grouped_by_act) && (
              <Typography color="warning">No document types available.</Typography>
            )}
            {!docTypesLoading && docTypesData?.result?.grouped_by_act && (
              <Box>
                {Object.entries(docTypesData.result.grouped_by_act).map(([group, types]) => (
                  <Box key={group} sx={{ mb: 1 }}>
                    <Typography variant="subtitle2" sx={{ color: BCDesignTokens.themePrimaryBlue, mb: 0.5 }}>{formatActName(group)}</Typography>
                    <List dense sx={{ pl: 2 }}>
                      {Object.entries(types).map(([typeId, typeName]) => {
                        const isSelected = selectedDocTypes.includes(typeId);
                        return (
                          <ListItem
                            key={typeId}
                            button
                            onClick={() => handleToggleDocType(typeId)}
                            selected={isSelected}
                            sx={{ borderRadius: 1, display: 'flex', alignItems: 'center' }}
                          >
                            <ListItemIcon>
                              <Checkbox
                                edge="start"
                                checked={isSelected}
                                tabIndex={-1}
                                disableRipple
                                color="primary"
                              />
                            </ListItemIcon>
                            <ListItemText
                              primary={typeName}
                            />
                            {isSelected && (
                              <IconButton
                                edge="end"
                                size="small"
                                aria-label={`Deselect ${typeName}`}
                                onClick={e => {
                                  e.stopPropagation();
                                  handleToggleDocType(typeId);
                                }}
                                sx={{ ml: 1 }}
                              >
                                <Close fontSize="small" />
                              </IconButton>
                            )}
                          </ListItem>
                        );
                      })}
                    </List>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </Box>
      </DialogContent>
      <Divider sx={{ my: 2 }} />
      <DialogActions sx={{ justifyContent: 'space-between' }}>
        <Button 
          onClick={handleClearAll} 
          variant="text"
          color="secondary"
          disabled={selectedProjects.length === 0 && selectedDocTypes.length === 0}
        >
          Clear All Filters
        </Button>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button onClick={handleCancel} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSave} variant="contained" disabled={isLoading || docTypesLoading}>
            Apply Filter
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  );
};

export default FilterModal;
