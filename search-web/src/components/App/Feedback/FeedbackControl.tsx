import React from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import { ThumbUp, ThumbDown } from '@mui/icons-material';

interface FeedbackControlProps {
  onFeedbackClick?: (type: 'positive' | 'negative') => void;
}

const FeedbackControl: React.FC<FeedbackControlProps> = ({ onFeedbackClick }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: 2,
        py: 1.5,
        borderRadius: "8px",
        backgroundColor: '#FEF8E8',
        flex: 1,
        minHeight: "42px",
      }}
    >
      {/* Feedback Text */}
      <Typography
        sx={{
          fontSize: '0.875rem', // text-sm
          color: '#374151', // gray-700
          fontWeight: 400,
          flex: 1,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        Please provide us your feedback on this search.
      </Typography>

      {/* Positive Feedback */}
      <IconButton
        size="small"
        onClick={() => onFeedbackClick?.('positive')}
        sx={{
          p: 1,
          '&:hover': { backgroundColor: '#F3F4F6' }, // gray-100 hover
          flexShrink: 0,
        }}
      >
        <ThumbUp sx={{ fontSize: 20, color: '#4B5563' }} /> {/* gray-600 */}
      </IconButton>

      {/* Negative Feedback */}
      <IconButton
        size="small"
        onClick={() => onFeedbackClick?.('negative')}
        sx={{
          p: 1,
          '&:hover': { backgroundColor: '#F3F4F6' },
          flexShrink: 0,
        }}
      >
        <ThumbDown sx={{ fontSize: 20, color: '#4B5563' }} />
      </IconButton>
    </Box>
  );
};

export default FeedbackControl;
