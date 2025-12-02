export interface FeedbackRequest {
  sessionId: string;           // Required: the search session ID
  feedback: "useful" | "not_useful"; // User feedback status
  comments?: string;           // Optional comments from the user
}

export interface FeedbackResponse {
  sessionId: string;           // Echoed session ID
  message: string;             // Status message from backend
}

// Optional helper type for UI
export interface FeedbackUI {
  rating: number;              // Numeric rating for display (1-5)
  comments: string;            // Text comments
  submittedAt?: string;        // Optional timestamp
}
