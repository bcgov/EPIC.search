import { Document } from "@/models/Search";
import SearchDocumentChunkCard from "./SearchDocumentChunkCard";
import SearchDocumentFullCard from "./SearchDocumentFullCard";

interface SearchDocumentCardProps {
  document: Document;
  searchText: string;
  isChunk?: boolean;
  onSimilarSearch?: (documentId: string, projectIds?: string[]) => void;
  showSimilarButtons?: boolean;
}

const SearchDocumentCard = ({
  document,
  searchText,
  isChunk = true,
  onSimilarSearch,
  showSimilarButtons = true,
}: SearchDocumentCardProps) => {
  if (isChunk) {
    return (
      <SearchDocumentChunkCard
        document={document}
        searchText={searchText}
      />
    );
  }

  return (
    <SearchDocumentFullCard 
      document={document} 
      onSimilarSearch={onSimilarSearch}
      showSimilarButtons={showSimilarButtons}
    />
  );
};

export default SearchDocumentCard;
