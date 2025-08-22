# Keywords package for query keyword extraction
# 
# This package provides different keyword extraction strategies:
# - simplified: Basic word frequency analysis (fastest)
# - fast: TF-IDF based extraction (fast with good quality)  
# - standard: KeyBERT semantic extraction (best quality)

from .simplified_query_keywords_extractor import getKeywords as simplified_extract
from .fast_query_keywords_extractor import getKeywords as fast_extract  
from .standard_query_keywords_extractor import getKeywords as standard_extract

__all__ = ['simplified_extract', 'fast_extract', 'standard_extract']
