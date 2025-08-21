"""
Image Analysis Service for describing image content when OCR fails.

This service provides AI-powered image analysis to generate searchable text
for pure images (photos, graphics, etc.) that don't contain readable text.
"""

import os
import requests
import time
from typing import Dict, List, Optional, Tuple


class ImageAnalysisService:
    """Service for analyzing and describing image content using AI vision APIs."""
    
    def __init__(self):
        self.azure_vision_endpoint = os.getenv('AZURE_VISION_ENDPOINT')
        self.azure_vision_key = os.getenv('AZURE_VISION_KEY')
        self.preferred_provider = os.getenv('IMAGE_ANALYSIS_PREFERRED_PROVIDER', 'azure').lower()
        self.confidence_threshold = float(os.getenv('IMAGE_ANALYSIS_CONFIDENCE_THRESHOLD', '0.5'))
        self.enabled = os.getenv('IMAGE_ANALYSIS_ENABLED', 'true').lower() == 'true'
        
    def is_analysis_available(self) -> bool:
        """Check if Azure Computer Vision is configured and enabled."""
        if not self.enabled:
            return False
        return bool(self.azure_vision_endpoint and self.azure_vision_key)
    
    def analyze_image(self, image_path: str, s3_key: str) -> Tuple[bool, Optional[Dict]]:
        """
        Analyze an image and generate descriptive content.
        
        Args:
            image_path: Path to the image file
            s3_key: S3 key for identification
            
        Returns:
            Tuple of (success, analysis_result)
            analysis_result contains: description, tags, objects, confidence, etc.
        """
        if not self.enabled:
            return False, {"error": "Image analysis is disabled"}
            
        try:
            # Use Azure Computer Vision
            if self.azure_vision_endpoint and self.azure_vision_key:
                return self._analyze_with_azure_vision(image_path, s3_key)
            else:
                return False, {"error": "Azure Computer Vision not configured"}
                
        except Exception as e:
            return False, {"error": f"Image analysis failed: {str(e)}"}
    
    def _analyze_with_azure_vision(self, image_path: str, s3_key: str) -> Tuple[bool, Optional[Dict]]:
        """Analyze image using Azure Computer Vision."""
        try:
            print(f"[IMAGE_ANALYSIS] Using Azure Computer Vision for {s3_key}")
            
            # Check image dimensions first (Azure requires at least 50x50 pixels)
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
                    print(f"[IMAGE_ANALYSIS] Image dimensions: {width}x{height} pixels")
                    
                    if width < 50 or height < 50:
                        print(f"[SKIP] Image {s3_key} is too small ({width}x{height}) - Azure requires at least 50x50 pixels")
                        return False, {
                            "error": f"Image too small ({width}x{height}px) - minimum 50x50px required",
                            "method": "azure_computer_vision",
                            "skipped_reason": "image_too_small"
                        }
            except Exception as img_check_err:
                print(f"[WARN] Could not check image dimensions for {s3_key}: {img_check_err}")
                # Continue anyway - let Azure handle the validation
            
            # Read and prepare image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            print(f"[IMAGE_ANALYSIS] Sending {len(image_data)} bytes to Azure Computer Vision")
            
            # Azure Computer Vision API
            analyze_url = f"{self.azure_vision_endpoint.rstrip('/')}/vision/v3.2/analyze"
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.azure_vision_key,
                'Content-Type': 'application/octet-stream'
            }
            
            params = {
                'visualFeatures': 'Description,Tags',
                # Remove details parameter to avoid permission issues
            }
            
            response = requests.post(analyze_url, headers=headers, params=params, data=image_data, timeout=30)
            
            # Handle different error responses
            if response.status_code == 400:
                error_detail = response.json() if response.content else {"error": "Bad Request"}
                error_msg = error_detail.get('error', {}).get('message', 'Bad Request')
                print(f"[SKIP] Azure rejected image {s3_key}: {error_msg}")
                return False, {
                    "error": f"Azure API error: {error_msg}",
                    "method": "azure_computer_vision",
                    "skipped_reason": "azure_validation_failed",
                    "status_code": 400
                }
            elif response.status_code == 403:
                print(f"[ERROR] Azure permission denied for {s3_key} - check API key, quotas, or service configuration")
                return False, {
                    "error": "Azure permission denied - check API key, quotas, or service tier",
                    "method": "azure_computer_vision",
                    "skipped_reason": "azure_permission_denied",
                    "status_code": 403
                }
            elif response.status_code == 429:
                print(f"[ERROR] Azure rate limit exceeded for {s3_key} - too many requests")
                return False, {
                    "error": "Azure rate limit exceeded - too many requests",
                    "method": "azure_computer_vision",
                    "skipped_reason": "azure_rate_limited",
                    "status_code": 429
                }
            
            response.raise_for_status()  # Raise for any other HTTP errors
            
            result = response.json()
            
            # Extract meaningful information
            description = ""
            confidence = 0.0
            tags = []
            objects = []
            categories = []
            
            if 'description' in result and 'captions' in result['description']:
                captions = result['description']['captions']
                if captions:
                    description = captions[0]['text']
                    confidence = captions[0]['confidence']
            
            if 'tags' in result:
                tags = [tag['name'] for tag in result['tags'] 
                       if tag['confidence'] > self.confidence_threshold]
            
            if 'objects' in result:
                objects = [obj['object'] for obj in result['objects'] 
                          if obj['confidence'] > self.confidence_threshold]
            
            if 'categories' in result:
                categories = [cat['name'] for cat in result['categories'] 
                             if cat['score'] > self.confidence_threshold]
            
            # Generate searchable text
            searchable_text = self._generate_searchable_text(
                s3_key, description, tags, objects, categories, "azure"
            )
            
            # Generate comprehensive keywords for improved searchability
            image_keywords = self.generate_image_keywords(description, tags, objects, categories)
            
            analysis_result = {
                "method": "azure_computer_vision",
                "description": description,
                "tags": tags,
                "objects": objects,
                "categories": categories,
                "searchable_text": searchable_text,
                "image_keywords": image_keywords,  # Add the new keywords
                "confidence": confidence,
                "raw_result": result
            }
            
            print(f"[IMAGE_ANALYSIS] Azure analysis successful for {s3_key}: {description[:100]}...")
            return True, analysis_result
            
        except Exception as e:
            print(f"[ERROR] Azure Vision analysis failed for {s3_key}: {str(e)}")
            return False, {"error": f"Azure Vision analysis failed: {str(e)}"}
    
    def enhance_content_for_image_pdf(self, s3_key: str, analysis_result: Dict, pdf_metadata: Dict = None) -> Dict:
        """
        Enhance analysis result specifically for image PDFs to improve searchability.
        
        Args:
            s3_key: S3 key for the PDF file
            analysis_result: Original image analysis result
            pdf_metadata: PDF metadata if available
            
        Returns:
            Enhanced analysis result with additional PDF-specific context
        """
        if not analysis_result:
            return analysis_result
            
        enhanced_result = analysis_result.copy()
        
        # Add PDF-specific tags
        pdf_tags = ["PDF", "ScannedDocument", "ImageBasedPDF", "DigitalDocument"]
        
        # Analyze the creator/producer for additional context
        if pdf_metadata:
            creator = pdf_metadata.get('creator', '').lower()
            producer = pdf_metadata.get('producer', '').lower()
            
            if 'photoshop' in creator or 'photoshop' in producer:
                pdf_tags.extend(["ImageProcessing", "GraphicDesign", "ProcessedImage"])
            
            if 'scanner' in creator or 'scanner' in producer:
                pdf_tags.extend(["ScannedContent", "DigitalScanning"])
                
            # Add format information
            pdf_format = pdf_metadata.get('format', '')
            if pdf_format:
                pdf_tags.append(f"Format{pdf_format.replace(' ', '').replace('.', '')}")
        
        # Enhance existing tags
        existing_tags = enhanced_result.get("tags", [])
        enhanced_tags = list(set(existing_tags + pdf_tags))
        enhanced_result["tags"] = enhanced_tags
        
        # Enhance searchable text with PDF context
        original_searchable_text = enhanced_result.get("searchable_text", "")
        
        # Add document type and processing information
        pdf_context_parts = [
            "Document type: Image-based PDF file",
            "Content source: Scanned or image-converted PDF document",
            "Processing method: Visual content analysis of PDF-embedded image"
        ]
        
        # Add metadata context if available
        if pdf_metadata:
            creation_date = pdf_metadata.get('creationDate', '')
            if creation_date:
                pdf_context_parts.append(f"Document creation context: {creation_date}")
                
            if 'photoshop' in (pdf_metadata.get('creator', '') + pdf_metadata.get('producer', '')).lower():
                pdf_context_parts.append("Image editing software used: Adobe Photoshop processed content")
        
        # Combine original searchable text with enhanced context
        enhanced_searchable_text = f"{original_searchable_text} | {' | '.join(pdf_context_parts)}"
        enhanced_result["searchable_text"] = enhanced_searchable_text
        
        # Add PDF-specific metadata
        enhanced_result["pdf_enhancement"] = {
            "enhanced_for_pdf": True,
            "additional_tags_count": len(pdf_tags),
            "pdf_metadata_available": bool(pdf_metadata),
            "enhancement_timestamp": time.time()
        }
        
        return enhanced_result

    def _generate_searchable_text(self, s3_key: str, description: str, tags: List[str], 
                                 objects: List[str], categories: List[str], method: str) -> str:
        """Generate comprehensive searchable text from image analysis."""
        
        # Extract filename without extension for context
        filename = s3_key.split('/')[-1]
        original_ext = None
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.pdf']:
            if ext.lower() in filename.lower():
                original_ext = ext
                filename = filename.replace(ext, '').replace(ext.upper(), '')
                break
        
        # Don't include the document file hash - just use the visual content description
        searchable_parts = [
            f"Visual content description: {description}",
        ]
        
        # Add specific context for PDF files that were converted from images
        if original_ext == '.pdf':
            searchable_parts.append("PDF document containing scanned or image-based content")
            searchable_parts.append("Image-based PDF document processed with visual analysis")
        
        if tags:
            searchable_parts.append(f"Visual elements: {', '.join(tags)}")
        
        if objects:
            searchable_parts.append(f"Detected objects: {', '.join(objects)}")
        
        if categories:
            searchable_parts.append(f"Content categories: {', '.join(categories)}")
        
        # Add analysis metadata with PDF context
        if original_ext == '.pdf':
            searchable_parts.append(f"Content type: Image-based PDF analyzed with {method}")
            searchable_parts.append("Scanned document visual content analysis")
        else:
            searchable_parts.append(f"Content type: Digital image analyzed with {method}")
            searchable_parts.append("Visual content analysis")
        
        return " | ".join(searchable_parts)
    
    def generate_image_keywords(self, description: str, tags: List[str], objects: List[str], categories: List[str]) -> List[str]:
        """Generate comprehensive keywords for image content to improve searchability."""
        keywords = []
        
        # Base image keywords
        keywords.extend([
            "image", "picture", "photo", "visual", "graphic", "illustration",
            "image of", "picture of", "photo of", "visual content", "graphic content"
        ])
        
        # Add description-based keywords
        if description:
            # Extract key terms from description and create searchable variants
            desc_words = description.lower().split()
            for word in desc_words:
                if len(word) > 3:  # Skip short words
                    keywords.extend([
                        f"image of {word}",
                        f"picture of {word}",
                        f"photo of {word}",
                        f"visual {word}",
                        word
                    ])
        
        # Add tag-based keywords
        for tag in tags:
            tag_lower = tag.lower()
            keywords.extend([
                tag_lower,
                f"image of {tag_lower}",
                f"picture of {tag_lower}",
                f"photo of {tag_lower}",
                f"visual {tag_lower}",
                f"{tag_lower} image",
                f"{tag_lower} picture",
                f"{tag_lower} photo"
            ])
        
        # Add object-based keywords
        for obj in objects:
            obj_lower = obj.lower()
            keywords.extend([
                obj_lower,
                f"image containing {obj_lower}",
                f"picture containing {obj_lower}",
                f"photo containing {obj_lower}",
                f"visual {obj_lower}",
                f"{obj_lower} image",
                f"{obj_lower} picture"
            ])
        
        # Add category-based keywords
        for category in categories:
            cat_lower = category.lower()
            keywords.extend([
                cat_lower,
                f"image category {cat_lower}",
                f"picture category {cat_lower}",
                f"visual category {cat_lower}",
                f"{cat_lower} content"
            ])
        
        # Add common search patterns for outdoor/nature content
        nature_indicators = ["outdoor", "nature", "landscape", "mountain", "water", "tree", "sky", "cloud"]
        for indicator in nature_indicators:
            if any(indicator in tag.lower() or indicator in description.lower() 
                   for tag in tags) or indicator in description.lower():
                keywords.extend([
                    f"outdoor {indicator}",
                    f"nature {indicator}",
                    f"landscape {indicator}",
                    f"{indicator} scenery",
                    f"{indicator} view"
                ])
        
        # Remove duplicates and return
        return list(set(keywords))


# Global instance
_image_analysis_service = None

def get_image_analysis_service() -> ImageAnalysisService:
    """Get or create the global image analysis service instance."""
    global _image_analysis_service
    if _image_analysis_service is None:
        _image_analysis_service = ImageAnalysisService()
    return _image_analysis_service

def is_image_analysis_available() -> bool:
    """Check if image analysis is available."""
    return get_image_analysis_service().is_analysis_available()

def analyze_image_content(image_path: str, s3_key: str) -> Tuple[bool, Optional[Dict]]:
    """Analyze image content and generate description."""
    return get_image_analysis_service().analyze_image(image_path, s3_key)
