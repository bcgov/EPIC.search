import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Collapse,
} from "@mui/material";
import {
  Assessment,
  CheckCircle,
  Error,
  Refresh,
  Visibility,
  ExpandMore,
  ExpandLess,
  Analytics,
  SkipNext,
} from "@mui/icons-material";
import { BCDesignTokens } from "epic.theme";
import { useStatsQuery, useProcessingStatsQuery, useProjectDetailsQuery } from "@/hooks/useStats";
import { ProjectStats } from "@/models/Stats";

const StatsMetricsInterface = () => {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [showProjectDetails, setShowProjectDetails] = useState<Record<string, boolean>>({});

  const {
    data: summaryData,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useStatsQuery();

  const {
    data: processingData,
    isLoading: processingLoading,
    error: processingError,
    refetch: refetchProcessing,
  } = useProcessingStatsQuery();

  const {
    data: projectDetailsData,
    isLoading: projectDetailsLoading,
  } = useProjectDetailsQuery(selectedProjectId || "", !!selectedProjectId);

  const handleRefresh = () => {
    refetchSummary();
    refetchProcessing();
  };

  const toggleProjectDetails = (projectId: string) => {
    setShowProjectDetails(prev => ({
      ...prev,
      [projectId]: !prev[projectId]
    }));
    if (!showProjectDetails[projectId]) {
      setSelectedProjectId(projectId);
    }
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 80) return "#4caf50"; // Green
    if (rate >= 60) return BCDesignTokens.themeGold60;
    return "#f44336"; // Red
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatProcessingTime = (seconds: number) => {
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${(seconds / 60).toFixed(1)}min`;
  };

  if (summaryLoading || processingLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 6 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading system statistics...</Typography>
      </Box>
    );
  }

  if (summaryError || processingError) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Error loading statistics: {summaryError?.message || processingError?.message}
      </Alert>
    );
  }

  // Check if data is still loading
  if (!summaryData || !processingData) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  const summary = summaryData?.result.processing_summary;
  const projects = processingData?.result.processing_stats?.projects || [];

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Analytics color="primary" sx={{ fontSize: 32 }} />
          <Typography variant="h4" color={BCDesignTokens.themeBlue80}>
            System Statistics & Metrics
          </Typography>
        </Box>
        <Tooltip title="Refresh data">
          <IconButton onClick={handleRefresh} color="primary">
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={6} sm={4} md={2.4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Assessment color="primary" sx={{ fontSize: 28 }} />
                <Box>
                  <Typography variant="h5">{summary?.total_projects || 0}</Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.75rem' }}>
                    Total Projects
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={4} md={2.4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CheckCircle sx={{ color: "#4caf50", fontSize: 28 }} />
                <Box>
                  <Typography variant="h5">{summary?.total_successful_files || 0}</Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.75rem' }}>
                    Successful Files
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={4} md={2.4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Error sx={{ color: "#f44336", fontSize: 28 }} />
                <Box>
                  <Typography variant="h5">{summary?.total_failed_files || 0}</Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.75rem' }}>
                    Failed Files
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={4} md={2.4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <SkipNext sx={{ color: "#ff9800", fontSize: 28 }} />
                <Box>
                  <Typography variant="h5">{summary?.total_skipped_files || 0}</Typography>
                  <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.75rem' }}>
                    Skipped Files
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={8} md={2.4}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box>
                <Typography variant="h5" sx={{ color: getSuccessRateColor(summary?.overall_success_rate || 0) }}>
                  {summary?.overall_success_rate?.toFixed(1) || 0}%
                </Typography>
                <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.75rem', mb: 1 }}>
                  Overall Success Rate
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={summary?.overall_success_rate || 0}
                  sx={{
                    height: 6,
                    backgroundColor: BCDesignTokens.themeGray20,
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: getSuccessRateColor(summary?.overall_success_rate || 0),
                    },
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Projects Table */}
      <Card>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
            <Assessment color="primary" />
            Project Processing Status
          </Typography>
          
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ minWidth: 200 }}><strong>Project</strong></TableCell>
                  <TableCell align="center" sx={{ width: 100 }}><strong>Total Files</strong></TableCell>
                  <TableCell align="center" sx={{ width: 100 }}><strong>Successful</strong></TableCell>
                  <TableCell align="center" sx={{ width: 100 }}><strong>Failed</strong></TableCell>
                  <TableCell align="center" sx={{ width: 100 }}><strong>Skipped</strong></TableCell>
                  <TableCell align="center" sx={{ width: 150 }}><strong>Success Rate</strong></TableCell>
                  <TableCell align="center" sx={{ width: 150 }}><strong>Actions</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.map((project: ProjectStats) => (
                  <React.Fragment key={project.project_id}>
                    <TableRow key={project.project_id} hover>
                      <TableCell>
                        <Typography variant="body1" fontWeight={600}>
                          {project.project_name}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          ID: {project.project_id}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip label={project.total_files} size="small" />
                      </TableCell>
                      <TableCell align="center">
                        <Chip 
                          label={project.successful_files} 
                          size="small" 
                          color="success"
                          icon={<CheckCircle />}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip 
                          label={project.failed_files} 
                          size="small" 
                          color="error"
                          icon={<Error />}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip 
                          label={project.skipped_files || 0} 
                          size="small" 
                          sx={{ 
                            backgroundColor: "#fff3e0", 
                            color: "#f57c00",
                            '& .MuiChip-icon': { color: "#f57c00" }
                          }}
                          icon={<SkipNext />}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 1 }}>
                          <Typography 
                            variant="body2" 
                            fontWeight={600}
                            sx={{ color: getSuccessRateColor(project.success_rate) }}
                          >
                            {project.success_rate.toFixed(1)}%
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={project.success_rate}
                            sx={{
                              width: 60,
                              backgroundColor: BCDesignTokens.themeGray20,
                              '& .MuiLinearProgress-bar': {
                                backgroundColor: getSuccessRateColor(project.success_rate),
                              },
                            }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Button
                          size="small"
                          startIcon={showProjectDetails[project.project_id] ? <ExpandLess /> : <ExpandMore />}
                          onClick={() => toggleProjectDetails(project.project_id)}
                          endIcon={<Visibility />}
                          sx={{ py: 1 }}
                        >
                          {showProjectDetails[project.project_id] ? "Hide" : "View"} Details
                        </Button>
                      </TableCell>
                    </TableRow>

                    {/* Project Details Collapse */}
                    <TableRow>
                      <TableCell colSpan={7} sx={{ py: 0 }}>
                        <Collapse in={showProjectDetails[project.project_id]} timeout="auto" unmountOnExit>
                          <Box sx={{ py: 2 }}>
                            {selectedProjectId === project.project_id && projectDetailsLoading && (
                              <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                                <CircularProgress size={24} />
                                <Typography sx={{ ml: 1 }}>Loading project details...</Typography>
                              </Box>
                            )}
                            
                            {selectedProjectId === project.project_id && projectDetailsData && (
                              <Box>
                                <Typography variant="h6" sx={{ mb: 2 }}>
                                  Processing Logs for {project.project_name}
                                </Typography>
                                
                                <Box sx={{ maxHeight: 400, overflow: "auto" }}>
                                  <Table size="small">
                                    <TableHead>
                                      <TableRow>
                                        <TableCell>Document</TableCell>
                                        <TableCell align="center">Status</TableCell>
                                        <TableCell align="center">Pages</TableCell>
                                        <TableCell align="center">File Size</TableCell>
                                        <TableCell align="center">Processing Time</TableCell>
                                        <TableCell align="center">Processed At</TableCell>
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {projectDetailsData.result.project_details.processing_logs.map((log: any) => (
                                        <TableRow key={log.log_id}>
                                          <TableCell sx={{ maxWidth: 300, minWidth: 200 }}>
                                            <Typography variant="body2" sx={{ wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
                                              {log.metrics?.document_info.display_name || 
                                               log.metrics?.document_info.document_name || 
                                               'UNKNOWN'}
                                            </Typography>
                                          </TableCell>
                                          <TableCell align="center">
                                            <Chip
                                              label={log.status}
                                              size="small"
                                              color={
                                                log.status === "success" ? "success" : 
                                                log.status === "failure" ? "error" : 
                                                "default"
                                              }
                                              icon={
                                                log.status === "success" ? <CheckCircle /> : 
                                                log.status === "failure" ? <Error /> : 
                                                <SkipNext />
                                              }
                                              sx={
                                                log.status === "skipped" ? {
                                                  backgroundColor: "#fff3e0", 
                                                  color: "#f57c00",
                                                  '& .MuiChip-icon': { color: "#f57c00" }
                                                } : {}
                                              }
                                            />
                                          </TableCell>
                                          <TableCell align="center">
                                            {log.metrics?.document_info.page_count || 'N/A'}
                                          </TableCell>
                                          <TableCell align="center">
                                            {log.metrics?.document_info.file_size_bytes 
                                              ? formatFileSize(log.metrics.document_info.file_size_bytes)
                                              : 'N/A'
                                            }
                                          </TableCell>
                                          <TableCell align="center">
                                            {log.metrics?.chunk_and_embed_pages_time 
                                              ? formatProcessingTime(log.metrics.chunk_and_embed_pages_time)
                                              : 'N/A'
                                            }
                                          </TableCell>
                                          <TableCell align="center">
                                            <Typography variant="caption">
                                              {new Date(log.processed_at).toLocaleString()}
                                            </Typography>
                                          </TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </Box>
                              </Box>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default StatsMetricsInterface;
