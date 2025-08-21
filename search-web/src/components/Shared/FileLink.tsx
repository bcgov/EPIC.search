import { Link, CircularProgress, Box } from "@mui/material";
import { useState } from "react";
import { AppConfig } from '@/utils/config';

interface FileLinkProps {
  s3Key: string | null;
  fileName: string;
  fileType?: string | null; // MIME type or file extension
  pageNumber?: number; // Only used for PDFs
  children: React.ReactNode;
  projectId?: string;
  documentName?: string;
}

// File types that can be opened in browser
const BROWSER_VIEWABLE_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/jpg', 
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml',
  'text/plain',
  'text/html',
  'text/csv',
];

const getFileTypeFromExtension = (fileName: string): string | null => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'pdf':
      return 'application/pdf';
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg';
    case 'png':
      return 'image/png';
    case 'gif':
      return 'image/gif';
    case 'webp':
      return 'image/webp';
    case 'svg':
      return 'image/svg+xml';
    case 'txt':
      return 'text/plain';
    case 'html':
    case 'htm':
      return 'text/html';
    case 'csv':
      return 'text/csv';
    case 'docx':
      return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    case 'xlsx':
      return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    case 'pptx':
      return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
    case 'doc':
      return 'application/msword';
    case 'xls':
      return 'application/vnd.ms-excel';
    case 'ppt':
      return 'application/vnd.ms-powerpoint';
    case 'zip':
      return 'application/zip';
    default:
      return null;
  }
};

const shouldOpenInBrowser = (fileType: string | null): boolean => {
  if (!fileType) return false;
  return BROWSER_VIEWABLE_TYPES.includes(fileType.toLowerCase());
};

const FileLink = ({
  s3Key,
  fileName,
  fileType,
  pageNumber = 1,
  children,
  projectId,
  documentName
}: FileLinkProps) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    try {
      // Fallback logic for s3Key
      let keyToUse = s3Key;
      if (!keyToUse && projectId && documentName) {
        keyToUse = `${projectId}/${documentName}`;
      }
      if (!keyToUse) {
        throw new Error("No valid S3 key or fallback key available.");
      }

      // Determine file type if not provided
      let resolvedFileType = fileType;
      if (!resolvedFileType) {
        resolvedFileType = getFileTypeFromExtension(fileName);
      }

      const encodedKey = encodeURIComponent(keyToUse);
      const encodedFileName = encodeURIComponent(fileName);
      
      // Fetch the file
      const response = await fetch(
        `${AppConfig.apiUrl}/document/view?key=${encodedKey}&file_name=${encodedFileName}`,
        {
          method: 'GET',
          headers: {
            'Accept': '*/*',
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      
      // Determine how to handle the file based on its type
      if (shouldOpenInBrowser(resolvedFileType)) {
        // Create blob with correct MIME type
        const typedBlob = new Blob([blob], {
          type: resolvedFileType || 'application/octet-stream'
        });

        // Create object URL
        const baseUrl = window.URL.createObjectURL(typedBlob);
        
        // For PDFs, add page number as hash
        const url = resolvedFileType === 'application/pdf' 
          ? baseUrl + `#page=${pageNumber}` 
          : baseUrl;

        // Open in new tab
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

      } else {
        // Trigger download for other file types
        const downloadBlob = new Blob([blob], {
          type: resolvedFileType || 'application/octet-stream'
        });

        const downloadUrl = window.URL.createObjectURL(downloadBlob);
        const link = window.document.createElement('a');
        link.href = downloadUrl;
        link.download = fileName; // This triggers download instead of navigation
        window.document.body.appendChild(link);
        link.click();
        window.document.body.removeChild(link);

        // Clean up
        setTimeout(() => {
          window.URL.revokeObjectURL(downloadUrl);
        }, 1000);
      }

    } catch (error) {
      console.error('Error opening/downloading file:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <Link
        href="#"
        underline="none"
        sx={{
          fontWeight: "bold",
          pointerEvents: isLoading ? 'none' : 'auto',
          opacity: isLoading ? 0.7 : 1,
          display: 'flex',
          alignItems: 'center',
        }}
        onClick={handleClick}
      >
        {children}
      </Link>
      {isLoading && (
        <CircularProgress 
          size={16} 
          sx={{ 
            position: 'absolute',
            left: -28,
            top: '20%',
            transform: 'translateY(-50%)',
          }} 
        />
      )}
    </Box>
  );
};

export default FileLink;
