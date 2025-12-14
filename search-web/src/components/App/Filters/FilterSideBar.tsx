import { useState, useMemo } from "react";
import {
  Box,
  Divider,
  IconButton,
  InputBase,
  Typography,
  Collapse,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  Paper,
  Button,
} from "@mui/material";
import FilterListIcon from '@mui/icons-material/FilterList';
import CloseIcon from '@mui/icons-material/Close';
import {
  Search as SearchIcon,
  ExpandLess,
  ExpandMore,
  ChevronLeft,
} from "@mui/icons-material";
import { useDocumentTypeMappings } from "@/hooks/useDocumentTypeMappings";
import { useProjects } from "@/hooks/useProjects";

interface FilterSidebarProps {
  selectedProjects: string[];
  selectedDocTypes: string[];
  onProjectToggle: (projectId: string) => void;
  onDocTypeToggle: (docTypeId: string) => void;
  onClearAll: () => void;
  collapsed?: boolean;
  onCollapseToggle?: () => void;
}

interface NormalizedProject {
  id: string;
  name: string;
}

export function FilterSidebar({
  selectedProjects,
  selectedDocTypes,
  onProjectToggle,
  onDocTypeToggle,
  onClearAll,
  collapsed = false,
  onCollapseToggle,
}: FilterSidebarProps) {
  const { data: rawProjects, isLoading: loadingProjects, isError: projectError } = useProjects();
  const {
    data: rawDocTypes,
    isLoading: loadingDocTypes,
    isError: docTypeError,
  } = useDocumentTypeMappings();
  const [projectSearch, setProjectSearch] = useState("");
  const [docTypeSearch, setDocTypeSearch] = useState("");
  const [expandedActs, setExpandedActs] = useState<string[]>(["2018", "2002"]);
  const isCollapsed = collapsed;

  const projectList: NormalizedProject[] = useMemo(() => {
    return (rawProjects ?? []).map((p: any) => ({
      id: p.project_id,
      name: p.project_name,
    }));
  }, [rawProjects]);

  const docTypes = useMemo(() => {
    const root = (rawDocTypes as any)?.result?.document_types;

    if (!root) return [];

    return Object.entries(root).map(([id, value]: any) => ({
      id,
      name: value.name,
      act: value.act.includes("2018") ? "2018" : "2002",
      aliases: value.aliases ?? [],
    }));
  }, [rawDocTypes]);

  // Filtered projects
  const filteredProjects = projectList.filter((p) =>
    p.name.toLowerCase().includes(projectSearch.toLowerCase())
  );

  // Filtered document types
  const docTypes2018 = docTypes.filter((d) => d.act === "2018");
  const docTypes2002 = docTypes.filter((d) => d.act === "2002");
  const filteredDocTypes2018 = docTypes2018.filter((d) =>
    d.name.toLowerCase().includes(docTypeSearch.toLowerCase())
  );
  const filteredDocTypes2002 = docTypes2002.filter((d) =>
    d.name.toLowerCase().includes(docTypeSearch.toLowerCase())
  );

  const toggleAct = (act: string) => {
    setExpandedActs((prev) =>
      prev.includes(act) ? prev.filter((a) => a !== act) : [...prev, act]
    );
  };

  const activeFilters = [
    ...selectedProjects.map((id) => ({
      id,
      label: projectList.find((p) => p.id === id)?.name || "",
      type: "project" as const,
    })),
    ...selectedDocTypes.map((id) => ({
      id,
      label: docTypes.find((d) => d.id === id)?.name || "",
      type: "docType" as const,
    })),
  ];

  return (
    <>
      {/* Overlay for mobile */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingTop: "20px",
          height: "100%",
        }}
      >
        {!isCollapsed && (
          <Typography variant="subtitle2" sx={{ ml: 2, fontWeight: 600 }}>
            PROJECTS
          </Typography>
        )}
        <IconButton
            onClick={() => onCollapseToggle?.()}
            size="small"
            sx={isCollapsed ? { ml: 1 } : undefined}
            >
            {isCollapsed ? <FilterListIcon /> : <ChevronLeft />}
        </IconButton>
      </Box>
        {!isCollapsed && (
          <Box sx={{ p: 2 }}>
            <Paper
              elevation={0}
              sx={{
                p: "2px 8px",
                mb: 1,
                display: "flex",
                alignItems: "center",
                backgroundColor: "#fff",
                border: "1px solid #d1d5db",
                borderRadius: "0.25rem",
                transition: "border 0.2s",
                "&:hover": {
                  border: "1px solid #013366",
                },
              }}
            >
              <SearchIcon fontSize="small" sx={{ mr: 1 }} />
              <InputBase
                placeholder="Search projects..."
                value={projectSearch}
                onChange={(e) => setProjectSearch(e.target.value)}
                sx={{
                  flex: 1,
                  typography: "body2",
                }}
              />
            </Paper>

            <List sx={{ maxHeight: 48 * 4, overflowY: "auto", typography: "body2" }}>
              {filteredProjects.map((p) => (
                <ListItem key={p.id} dense button onClick={() => onProjectToggle(p.id)}>
                  <Checkbox
                    checked={selectedProjects.includes(p.id)}
                    tabIndex={-1}
                    disableRipple
                  />
                  <ListItemText primary={p.name} />
                </ListItem>
              ))}
            </List>

            {/* Document Types */}
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1, fontWeight: 600 }}>
              DOCUMENT TYPES
            </Typography>
            <Paper
              elevation={0}
              sx={{
                p: "2px 8px",
                mb: 1.5,
                display: "flex",
                alignItems: "center",
                backgroundColor: "#fff",
                border: "1px solid #d1d5db",
                borderRadius: "0.25rem",
                transition: "border 0.2s",
                "&:hover": {
                  border: "1px solid #013366",
                },
              }}
            >
              <SearchIcon fontSize="small" sx={{ mr: 1 }} />
              <InputBase
                placeholder="Search document types..."
                value={docTypeSearch}
                onChange={(e) => setDocTypeSearch(e.target.value)}
                sx={{ flex: 1, typography: "body2" }}
              />
            </Paper>

            {/* 2002 Act */}
            <Paper
              elevation={0}
              sx={{
                mb: 1.5,
                backgroundColor: "#fff",
                border: "1px solid #d1d5db",
                borderRadius: "0.25rem",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  p: 1,
                  cursor: "pointer",
                }}
                onClick={() => toggleAct("2002")}
              >
                <Typography variant="body2">2002 Act</Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    ({filteredDocTypes2002.length})
                  </Typography>
                  {expandedActs.includes("2002") ? <ExpandLess /> : <ExpandMore />}
                </Box>
              </Box>
              <Divider/>
              <Collapse in={expandedActs.includes("2002")}>
                <List sx={{ maxHeight: 48 * 6, overflowY: "auto", px: 1 }}>
                  {filteredDocTypes2002.map((d) => (
                    <ListItem
                      key={d.id}
                      button
                      onClick={() => onDocTypeToggle(d.id)}
                    >
                      <Checkbox
                        checked={selectedDocTypes.includes(d.id)}
                        tabIndex={-1}
                        disableRipple
                      />
                      <ListItemText primary={d.name} primaryTypographyProps={{ variant: "body2" }} />
                    </ListItem>
                  ))}
                  {filteredDocTypes2002.length === 0 && (
                    <Typography variant="caption" sx={{ px: 1, py: 0.5 }}>
                      No matches
                    </Typography>
                  )}
                </List>
              </Collapse>
            </Paper>

            {/* 2018 Act */}
            <Paper
              elevation={0}
              sx={{
                mb: 1,
                backgroundColor: "#fff",
                border: "1px solid #d1d5db",
                borderRadius: "0.25rem",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  p: 1,
                  cursor: "pointer",
                }}
                onClick={() => toggleAct("2018")}
              >
                <Typography variant="body2">2018 Act</Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    ({filteredDocTypes2018.length})
                  </Typography>
                  {expandedActs.includes("2018") ? <ExpandLess /> : <ExpandMore />}
                </Box>
              </Box>
              <Divider/>
              <Collapse in={expandedActs.includes("2018")}>
                <List sx={{ maxHeight: 48 * 6, overflowY: "auto", px: 1 }}>
                  {filteredDocTypes2018.map((d) => (
                    <ListItem
                      key={d.id}
                      button
                      onClick={() => onDocTypeToggle(d.id)}
                    >
                      <Checkbox
                        checked={selectedDocTypes.includes(d.id)}
                        tabIndex={-1}
                        disableRipple
                      />
                      <ListItemText primary={d.name} primaryTypographyProps={{ variant: "body2" }} />
                    </ListItem>
                  ))}
                  {filteredDocTypes2018.length === 0 && (
                    <Typography variant="caption" sx={{ px: 1, py: 0.5 }}>
                      No matches
                    </Typography>
                  )}
                </List>
              </Collapse>
            </Paper>

            {/* Active Filters */}
            {activeFilters.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  ACTIVE FILTERS
                </Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1 }}>
                  {activeFilters.map((f) => (
                    <Paper
                      key={`${f.type}-${f.id}`}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        px: 1.5,
                        py: 0.5,
                        bgcolor: "#D6E9FB",
                        borderRadius: "16px",
                        gap: 0.5,
                      }}
                    >
                      <Typography variant="caption">{f.label}</Typography>
                      <IconButton
                        size="small"
                        onClick={() =>
                          f.type === "project"
                            ? onProjectToggle(f.id)
                            : onDocTypeToggle(f.id)
                        }
                      >
                        <CloseIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                    </Paper>
                  ))}
                </Box>
                <Box sx={{ ml: -1.5 }}>
                  <Button
                    variant="text"
                    size="small"
                    onClick={onClearAll}
                    sx={{ textDecoration: "underline", color: "#013366" }}
                  >
                    Clear All Filters
                  </Button>
                </Box>
              </Box>
            )}
          </Box>
        )}
    </>
  );
}
