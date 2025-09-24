/**
 * Utility functions for formatting data for display
 */

/**
 * Formats act keys to user-friendly display names
 * @param actKey The act key from the API (e.g., "2002_act_terms")
 * @returns Formatted display name (e.g., "2002 Act Terms")
 */
export const formatActName = (actKey: string): string => {
  switch (actKey) {
    case '2002_act_terms':
      return '2002 Act Terms';
    case '2018_act_terms':
      return '2018 Act Terms';
    default:
      return actKey; // Fallback to original key if unknown
  }
};