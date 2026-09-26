from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class IngredientType(str, Enum):
    """Types of cosmetic ingredients"""
    ACTIVE = "active"
    EMOLLIENT = "emollient"
    HUMECTANT = "humectant"
    SURFACTANT = "surfactant"
    PRESERVATIVE = "preservative"
    FRAGRANCE = "fragrance"
    SOLVENT = "solvent"
    THICKENER = "thickener"
    ANTIOXIDANT = "antioxidant"
    SUNSCREEN = "sunscreen"
    COLORANT = "colorant"
    BUFFERING_AGENT = "buffering_agent"
    CHELATING_AGENT = "chelating_agent"
    OTHER = "other"

class IrritationRisk(str, Enum):
    """Risk levels for skin irritation"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"

class PregnancySafety(str, Enum):
    """Safety levels during pregnancy"""
    SAFE = "safe"
    CAUTION = "caution"
    AVOID = "avoid"
    UNKNOWN = "unknown"

class IngredientResearchResult(BaseModel):
    """Structured result for ingredient research"""
    
    # Basic identification
    ingredient: str = Field(..., description="The original ingredient name as provided")
    ingredient_type: Optional[str] = Field(None, description="Type of ingredient (e.g., active, humectant, preservative)")
    function: Optional[str] = Field(None, description="Primary function in cosmetic formulations")
    
    # Benefits and uses
    benefits: Optional[str] = Field(None, description="Key benefits for skin")
    suitable_skin_types: Optional[List[str]] = Field(None, description="Skin types this ingredient is suitable for")
    skin_concerns: Optional[List[str]] = Field(None, description="Skin concerns this ingredient addresses")
    
    # Safety information
    irritation_risk: Optional[str] = Field(None, description="Risk level for skin irritation (low, moderate, high, unknown)")
    irritation_notes: Optional[str] = Field(None, description="Additional notes about irritation potential")
    allergy_sensitization: Optional[str] = Field(None, description="Allergy or sensitization potential")
    who_should_avoid: Optional[List[str]] = Field(None, description="Groups who should avoid this ingredient")
    
    # Pregnancy safety
    pregnancy_safety: Optional[str] = Field(None, description="Safety during pregnancy (safe, caution, avoid, unknown)")
    pregnancy_notes: Optional[str] = Field(None, description="Additional notes about pregnancy safety")
    
    # Interactions
    interactions_with_other_ingredients: Optional[List[str]] = Field(None, description="Known interactions with other ingredients")
    
    # Research metadata
    evidence_source: Optional[str] = Field(None, description="Source of information (e.g., scientific study, cosmetic database)")
    
    # Canonical information
    canonical_name: Optional[str] = Field(None, description="Standardized/canonical name for the ingredient")
    aliases: Optional[List[str]] = Field(None, description="Alternative names for the ingredient")

class IngredientResearchRequest(BaseModel):
    """Request model for ingredient research"""
    ingredient_list: List[str] = Field(..., description="List of ingredient names to research")

class IngredientResearchResponse(BaseModel):
    """Response model for ingredient research"""
    success: bool = Field(..., description="Whether the research was successful")
    total_ingredients: int = Field(..., description="Total number of ingredients processed")
    successfully_researched: int = Field(..., description="Number of ingredients successfully researched")
    failed_research: int = Field(..., description="Number of ingredients that failed research")
    ingredients: List[IngredientResearchResult] = Field(..., description="Research results for each ingredient")
    errors: Optional[List[dict]] = Field(None, description="Errors encountered during research")
