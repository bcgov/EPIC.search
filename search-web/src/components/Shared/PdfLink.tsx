import { Link, CircularProgress, Box } from "@mui/material";
import { useState } from "react";
import { AppConfig } from '@/utils/config';

interface PdfLinkProps {
  s3Key: string;
  fileName: string;
  pageNumber?: number;
  children: React.ReactNode;
}

const PdfLink = ({ s3Key, fileName, pageNumber = 1, children }: PdfLinkProps) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (isLoading) return;
    
    setIsLoading(true);
    try {
      const encodedKey = encodeURIComponent(s3Key);
      const encodedFileName = encodeURIComponent(fileName);
      const response = await fetch(
        `${AppConfig.apiUrl}/document/view?key=${encodedKey}&file_name=${encodedFileName}`, 
        {
          method: 'GET',
          headers: {
            'Accept': 'application/pdf',
            'Content-Type': 'application/pdf'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      const pdfBlob = new Blob([blob], { 
        type: 'application/pdf'
      });
      
      // Create object URL without page number first
      const baseUrl = window.URL.createObjectURL(pdfBlob);
      // Add page number as hash
      const url = baseUrl + `#page=${pageNumber}`;
      
      // Create a temporary link element
      const link = window.document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
      
      // Clean up the blob URL after a delay
      setTimeout(() => {
        window.URL.revokeObjectURL(baseUrl);
      }, 1000);

    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Link 
        href="#"        
        underline="none" 
        sx={{ 
          fontWeight: "bold",
          pointerEvents: isLoading ? 'none' : 'auto',
          opacity: isLoading ? 0.7 : 1,
        }}
        onClick={handleClick}
      >
        {children}
      </Link>
      {isLoading && (
        <CircularProgress size={16} sx={{ ml: 1 }} />
      )}
    </Box>
  );
};

export default PdfLink;
