import { useState } from 'react';
import {
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Slider,
  Box,
  IconButton,
} from '@mui/material'
import { Close } from '@mui/icons-material';
import { useFeedback, FeedbackRequest } from "@/hooks/useFeedback";

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId?: string;
  queryText?: string;
  projectIds?: string[];
  documentTypeIds?: string[];
  feedbackType?: 'up' | 'down';
}

export default function FeedbackModal({
  isOpen,
  onClose,
  sessionId,
  queryText,
  projectIds,
  documentTypeIds,
  feedbackType,
}: FeedbackModalProps) {
  const MIN = 1;
  const MAX = 5;
  const marks = [
    { value: MIN, label: '' },
    { value: MAX, label: '' },
  ];
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const [summaryHelpful, setSummaryHelpful] = useState(3);
  const [summaryAccurate, setSummaryAccurate] = useState(3);
  const [docHelpful, setDocHelpful] = useState(3);
  const [docAccurate, setDocAccurate] = useState(3);
  const [summaryImprovement, setSummaryImprovement] = useState('');
  const [docImprovement, setDocImprovement] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const { mutate } = useFeedback(
    () => {
      // On success
      setIsLoading(false);
      setSubmitted(true); // mark as submitted
    },
    (err: any) => {
      console.error("Feedback submission failed:", err);
      setIsLoading(false);
      setIsError(true);
      setErrorMessage(err?.message || "Failed to submit feedback. Please try again.");
    }
  );

  const handleSubmit = () => {
    setIsLoading(true);
    setIsError(false);

    const payload: FeedbackRequest = {
      sessionId,
      queryText,
      projectIds,
      documentTypeIds,
      feedback: feedbackType,
      summaryHelpful,
      summaryAccurate,
      docHelpful,
      docAccurate,
      summaryImprovement,
      docImprovement,
    };

    mutate(payload);
  };

  const handleClose = () => {
    setSummaryHelpful(3);
    setSummaryAccurate(3);
    setDocHelpful(3);
    setDocAccurate(3);
    setSummaryImprovement('');
    setDocImprovement('');
    setSubmitted(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onClose={handleClose} maxWidth="md" fullWidth>
      {!submitted ? (
        <>
          <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Please provide us your feedback on this search</Typography>
            <IconButton onClick={handleClose}>
              <Close />
            </IconButton>
          </DialogTitle>

          <DialogContent dividers>
            {/* Summary Helpful */}
            <Box mb={4}>
              <Typography gutterBottom>Did you find the AI summary helpful?</Typography>
              <Slider
                marks={marks}
                step={1}
                min={MIN}
                max={MAX}
                value={summaryHelpful}
                valueLabelDisplay="auto"
                onChange={(_, newValue) => setSummaryHelpful(newValue as number)}
              />

              {/* Labels below the slider */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography
                  variant="caption"
                  onClick={() => setSummaryHelpful(MIN)}
                  sx={{ cursor: 'pointer' }}
                >
                  Not helpful at all
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ textAlign: 'center', flex: 1 }}
                >
                  Neutral
                </Typography>
                <Typography
                  variant="caption"
                  onClick={() => setSummaryHelpful(MAX)}
                  sx={{ cursor: 'pointer', textAlign: 'right' }}
                >
                  Very helpful
                </Typography>
              </Box>
            </Box>

            {/* Summary Accurate */}
            <Box mb={4}>
              <Typography gutterBottom>Did you find the AI summary accurate?</Typography>
              <Slider
                marks={marks}
                step={1}
                min={MIN}
                max={MAX}
                value={summaryAccurate}
                valueLabelDisplay="auto"
                onChange={(_, newValue) => setSummaryAccurate(newValue as number)}
              />

              {/* Labels below the slider */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography
                  variant="caption"
                  onClick={() => setSummaryAccurate(MIN)}
                  sx={{ cursor: 'pointer' }}
                >
                  Not accurate at all
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ textAlign: 'center', flex: 1 }}
                >
                  Neutral
                </Typography>
                <Typography
                  variant="caption"
                  onClick={() => setSummaryAccurate(MAX)}
                  sx={{ cursor: 'pointer', textAlign: 'right' }}
                >
                  Very accurate
                </Typography>
              </Box>
            </Box>

            {/* Document Helpful */}
            <Box mb={4}>
              <Box>
                <Typography mb={1} variant="body2">What can we do to improve this AI summary? What information would you find more helpful than what was provided?</Typography>
                <textarea
                  value={summaryImprovement}
                  onChange={(e) => setSummaryImprovement(e.target.value)}
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '8px',
                    marginTop: '4px',
                    borderRadius: '4px',
                    border: '1px solid #c4c4c4',
                    resize: 'none',
                  }}
                  placeholder="Please share your suggestions..."
                />
              </Box>
            </Box>

            {/* Result Helpful */}
            <Box mb={4}>
              <Typography gutterBottom>Did you find the AI document search results helpful?</Typography>
              <Slider
                marks={marks}
                step={1}
                min={MIN}
                max={MAX}
                value={docHelpful}
                valueLabelDisplay="auto"
                onChange={(_, newValue) => setDocHelpful(newValue as number)}
              />

              {/* Labels below the slider */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography
                  variant="caption"
                  onClick={() => setDocHelpful(MIN)}
                  sx={{ cursor: 'pointer' }}
                >
                  Not helpful at all
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ textAlign: 'center', flex: 1 }}
                >
                  Neutral
                </Typography>
                <Typography
                  variant="caption"
                  onClick={() => setDocHelpful(MAX)}
                  sx={{ cursor: 'pointer', textAlign: 'right' }}
                >
                  Very helpful
                </Typography>
              </Box>
            </Box>

            {/* Result Accurate */}
            <Box mb={4}>
              <Typography gutterBottom>Did you find the AI document search accurate?</Typography>
              <Slider
                marks={marks}
                step={1}
                min={MIN}
                max={MAX}
                value={docAccurate}
                valueLabelDisplay="auto"
                onChange={(_, newValue) => setDocAccurate(newValue as number)}
              />

              {/* Labels below the slider */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography
                  variant="caption"
                  onClick={() => setDocAccurate(MIN)}
                  sx={{ cursor: 'pointer' }}
                >
                  Not accurate at all
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ textAlign: 'center', flex: 1 }}
                >
                  Neutral
                </Typography>
                <Typography
                  variant="caption"
                  onClick={() => setDocAccurate(MAX)}
                  sx={{ cursor: 'pointer', textAlign: 'right' }}
                >
                  Very accurate
                </Typography>
              </Box>
            </Box>

            {/* Document Helpful */}
            <Box mb={4}>
              <Box>
                <Typography mb={1} variant="body2">What can we do to improve this AI document search? What documents should have been included? What documents included in the results should not have been included?</Typography>
                <textarea
                  value={docImprovement}
                  onChange={(e) => setDocImprovement(e.target.value)}
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '8px',
                    marginTop: '4px',
                    borderRadius: '4px',
                    border: '1px solid #c4c4c4',
                    resize: 'none',
                  }}
                  placeholder="Please share your suggestions..."
                />
              </Box>
            </Box>
          </DialogContent>

          <DialogActions>
            <Button onClick={handleClose} variant="text">Cancel</Button>
            {!submitted && (
              <Button
                onClick={handleSubmit}
                variant="contained"
              >
                {isLoading ? <CircularProgress size={24} /> : "Send Feedback"}
              </Button>
            )}
          </DialogActions>
          {isError && (
            <Typography color="error" variant="body2" sx={{ mt: 1 }}>
              {errorMessage}
            </Typography>
          )}
        </>
      ) : (
        <DialogContent sx={{ textAlign: 'center', py: 8 }}>
          <Box sx={{ display: 'inline-flex', p: 2, backgroundColor: '#d1fae5', borderRadius: '50%', mb: 2 }}>
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" width={32} height={32}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </Box>
          <Typography variant="h6" gutterBottom>Thank you for your feedback!</Typography>
          <Typography variant="body2" color="text.secondary">
            Your input helps us improve the AI summary experience for everyone.
          </Typography>
        </DialogContent>
      )}
    </Dialog>
  );
}
