"""
Image Analysis Service for describing image content when OCR fails.

This service provides AI-powered image analysis to generate searchable text
for pure images (photos, graphics, etc.) that don't contain readable text.
"""

import os
import requests
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
            
            # Read and prepare image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Azure Computer Vision API
            analyze_url = f"{self.azure_vision_endpoint.rstrip('/')}/vision/v3.2/analyze"
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.azure_vision_key,
                'Content-Type': 'application/octet-stream'
            }
            
            params = {
                'visualFeatures': 'Categories,Description,Tags,Objects,Faces,ImageType,Color',
                'details': 'Landmarks,Celebrities'
            }
            
            response = requests.post(analyze_url, headers=headers, params=params, data=image_data, timeout=30)
            response.raise_for_status()
            
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
            
            analysis_result = {
                "method": "azure_computer_vision",
                "description": description,
                "tags": tags,
                "objects": objects,
                "categories": categories,
                "searchable_text": searchable_text,
                "confidence": confidence,
                "raw_result": result
            }
            
            print(f"[IMAGE_ANALYSIS] Azure analysis successful for {s3_key}: {description[:100]}...")
            return True, analysis_result
            
        except Exception as e:
            print(f"[ERROR] Azure Vision analysis failed for {s3_key}: {str(e)}")
            return False, {"error": f"Azure Vision analysis failed: {str(e)}"}
    
    def _generate_searchable_text(self, s3_key: str, description: str, tags: List[str], 
                                 objects: List[str], categories: List[str], method: str) -> str:
        """Generate comprehensive searchable text from image analysis."""
        
        # Extract filename without extension for context
        filename = s3_key.split('/')[-1]
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
            filename = filename.replace(ext, '').replace(ext.upper(), '')
        filename_words = filename.replace('_', ' ').replace('-', ' ')
        
        searchable_parts = [
            f"Image file: {filename_words}",
            f"Image description: {description}",
        ]
        
        if tags:
            searchable_parts.append(f"Image contains: {', '.join(tags)}")
        
        if objects:
            searchable_parts.append(f"Objects detected: {', '.join(objects)}")
        
        if categories:
            searchable_parts.append(f"Categories: {', '.join(categories)}")
        
        # Add analysis metadata
        searchable_parts.append(f"Content type: Digital image analyzed with {method}")
        searchable_parts.append("Visual content analysis")
        
        return " | ".join(searchable_parts)


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
