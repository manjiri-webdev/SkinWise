from typing import Dict, Optional
import re

# Trusted source patterns and their priorities (lower = higher priority)
TRUSTED_SOURCES = {
    r"openbeautyfacts\.org": 1,
    r"world\.openbeautyfacts\.org": 1,
    r"incidecoder\.com": 2,
    r"incidecoder\.co": 2,
    r"incidecoder\.in": 2,
    r"skinvasion\.com": 3,
    r"cosdna\.com": 4,
    r"cosmeticingredientreview\.com": 5,
    r"ewg\.org": 6,
    r"ewg\.org/skindeep": 6,
}

# Retailer patterns to filter out
RETAILER_PATTERNS = [
    r"amazon\.com",
    r"amazon\.in",
    r"amazon\.",
    r"nykaa\.com",
    r"ulta\.com",
    r"sephora\.com",
    r"cult\.beauty",
    r"lookfantastic\.com",
    r"beautybay\.com",
    r"flipkart\.com",
]

def get_source_priority(url: str) -> int:
    """
    Get priority score for a URL based on trusted sources.
    Lower score = higher priority.
    
    Args:
        url: The URL to evaluate
        
    Returns:
        Priority score (lower is better)
    """
    url_lower = url.lower()
    
    # Check if it's a retailer (lower priority)
    for pattern in RETAILER_PATTERNS:
        if re.search(pattern, url_lower):
            return 50  # Low priority for retailers
    
    # Check trusted sources
    for pattern, priority in TRUSTED_SOURCES.items():
        if re.search(pattern, url_lower):
            return priority
    
    # Default priority for unknown sources
    return 20

def get_source_name(url: str) -> str:
    """
    Extract a readable source name from URL.
    
    Args:
        url: The URL to extract name from
        
    Returns:
        Human-readable source name
    """
    url_lower = url.lower()
    
    # Check trusted sources first
    for pattern in TRUSTED_SOURCES.keys():
        match = re.search(pattern, url_lower)
        if match:
            domain = match.group(0)
            return domain.replace("www.", "").split(".")[0].capitalize()
    
    # Extract domain for unknown sources
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain.split(".")[0].capitalize()
    except:
        return "Unknown"

def is_retailer_source(url: str) -> bool:
    """
    Check if URL is from a known retailer.
    
    Args:
        url: The URL to check
        
    Returns:
        True if retailer, False otherwise
    """
    url_lower = url.lower()
    for pattern in RETAILER_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    
    return False

def is_official_brand_site(url: str, brand: str) -> bool:
    """
    Check if URL appears to be an official brand website.
    
    Args:
        url: The URL to check
        brand: The brand name to match against
        
    Returns:
        True if likely official brand site
    """
    if not brand:
        return False
    
    url_lower = url.lower()
    brand_variations = [
        brand.lower().replace(" ", "").replace("&", "").replace(".", ""),
        brand.lower().replace(" ", "").replace("&", "and").replace(".", ""),
        brand.lower().replace(" ", "-").replace("&", "").replace(".", ""),
    ]
    
    # Check if brand name appears in domain
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        domain_clean = domain.replace(".", "").replace("-", "")
        
        for brand_var in brand_variations:
            if brand_var in domain_clean:
                return True
    except:
        return False
    
    return False
