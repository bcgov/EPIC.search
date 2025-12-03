import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Button,
  TextField,
  Box,
  Rating,
  CircularProgress,
  Typography
} from "@mui/material";
import { useEffect, useState } from "react";
import { useFeedback, FeedbackValue, FeedbackRequest } from "@/hooks/useFeedback";

interface FeedbackModalProps {
  open: boolean;
  onClose: () => void;
  sessionId?: string;
  queryText?: string;
  projectIds?: string[];
  documentTypeIds?: string[];
  initialFeedback?: 'up' | 'down' | null;
}

export default function FeedbackModal({
  open,
  onClose,
  sessionId,
  queryText,
  projectIds,
  documentTypeIds,
  initialFeedback,
}: FeedbackModalProps) {
  const [text, setText] = useState<string>("");
  const [rating, setRating] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isSubmitted, setIsSubmitted] = useState(false); // new state

    useEffect(() => {
    if (open) {
      if (initialFeedback === 'up') setRating(5);
      else if (initialFeedback === 'down') setRating(1);
      else setRating(4); // default neutral
      setText(""); // clear comment
      setIsSubmitted(false); // reset submitted state
      setIsError(false);
      setErrorMessage("");
    }
  }, [open, initialFeedback]);

  const { mutate } = useFeedback(
    () => {
      // On success
      setIsLoading(false);
      setIsSubmitted(true); // mark as submitted
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

    const feedbackValue: FeedbackValue =
      rating === null ? "neutral" : rating >= 4 ? "useful" : "not_useful";

    const payload: FeedbackRequest = {
      sessionId,
      queryText,
      projectIds,
      documentTypeIds,
      feedback: feedbackValue,
      comments: text || undefined,
    };

    mutate(payload);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>We value your feedback</DialogTitle>

      <DialogContent>
        {!isSubmitted ? (
          <>
            <Box sx={{ mb: 2, textAlign: "center" }}>
              <Rating
                value={rating}
                onChange={(e, v) => setRating(v)}
                size="large"
                disabled={isLoading}
              />
            </Box>

            <TextField
              label="Tell us more…"
              multiline
              rows={4}
              fullWidth
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={isLoading}
            />

            {isError && (
              <Typography color="error" variant="body2" sx={{ mt: 1 }}>
                {errorMessage}
              </Typography>
            )}
          </>
        ) : (
          <Box sx={{ textAlign: "center", py: 4 }}>
            <Typography variant="h6" gutterBottom>
              Thank you for your feedback!
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Your input helps us improve the search experience.
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          {isSubmitted ? "Close" : "Cancel"}
        </Button>

        {!isSubmitted && (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={isLoading}
          >
            {isLoading ? <CircularProgress size={24} /> : "Submit Feedback"}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
