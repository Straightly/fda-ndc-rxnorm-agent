"""
Data models for FDA NDC and RxNorm entities
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class NDCProduct(BaseModel):
    """FDA NDC Product information"""
    
    product_ndc: str = Field(..., description="Product NDC code")
    product_type: str = Field(..., description="Type of product")
    proprietary_name: Optional[str] = Field(None, description="Proprietary name")
    proprietary_name_suffix: Optional[str] = Field(None, description="Proprietary name suffix")
    non_proprietary_name: Optional[str] = Field(None, description="Non-proprietary name")
    dosage_form_name: Optional[str] = Field(None, description="Dosage form")
    route_name: Optional[str] = Field(None, description="Route of administration")
    start_marketing_date: Optional[str] = Field(None, description="Start marketing date")
    end_marketing_date: Optional[str] = Field(None, description="End marketing date")
    marketing_category_name: Optional[str] = Field(None, description="Marketing category")
    application_number: Optional[str] = Field(None, description="Application number")
    labeler_name: Optional[str] = Field(None, description="Labeler name")
    substance_name: Optional[str] = Field(None, description="Active substance name")
    strength_number: Optional[str] = Field(None, description="Strength number")
    strength_unit: Optional[str] = Field(None, description="Strength unit")
    pharm_class_cs: Optional[str] = Field(None, description="Chemical structure class")
    pharm_class_pe: Optional[str] = Field(None, description="Physiologic effect class")
    pharm_class_moa: Optional[str] = Field(None, description="Mechanism of action class")
    pharm_class_cs_description: Optional[str] = Field(None, description="Chemical structure description")
    pharm_class_pe_description: Optional[str] = Field(None, description="Physiologic effect description")
    pharm_class_moa_description: Optional[str] = Field(None, description="Mechanism of action description")
    
    @validator('product_ndc')
    def validate_ndc_format(cls, v):
        """Validate NDC format"""
        if v and len(v.replace('-', '')) != 11:
            raise ValueError('NDC must be 11 digits (with or without hyphens)')
        return v


class RxNormConcept(BaseModel):
    """RxNorm concept information"""
    
    rxcui: str = Field(..., description="RxNorm concept unique identifier")
    name: str = Field(..., description="Concept name")
    synonym: Optional[str] = Field(None, description="Synonym")
    tty: str = Field(..., description="Term type")
    language: str = Field(default="ENG", description="Language")
    suppress: str = Field(default="N", description="Suppress flag")
    umlscui: Optional[str] = Field(None, description="UMLS CUI")


class RxNormIngredient(BaseModel):
    """RxNorm ingredient information"""
    
    rxcui: str = Field(..., description="Ingredient RxNorm CUI")
    name: str = Field(..., description="Ingredient name")
    base_names: Optional[List[str]] = Field(None, description="Base names")


class RxNormDrug(BaseModel):
    """RxNorm drug information"""
    
    rxcui: str = Field(..., description="Drug RxNorm CUI")
    name: str = Field(..., description="Drug name")
    synonym: Optional[str] = Field(None, description="Synonym")
    tty: str = Field(..., description="Term type")
    base_names: Optional[List[str]] = Field(None, description="Base names")
    ingredients: Optional[List[RxNormIngredient]] = Field(None, description="Ingredients")


class NDC_RxNorm_Match(BaseModel):
    """NDC to RxNorm match result"""
    
    ndc_product: NDCProduct = Field(..., description="NDC product information")
    rxnorm_concepts: List[RxNormConcept] = Field(default_factory=list, description="Matched RxNorm concepts")
    rxnorm_drugs: List[RxNormDrug] = Field(default_factory=list, description="Matched RxNorm drugs")
    match_confidence: float = Field(..., description="Match confidence score (0-1)")
    match_method: str = Field(..., description="Method used for matching")
    match_date: datetime = Field(default_factory=datetime.now, description="Match date")
    clinical_metadata: Dict[str, Any] = Field(default_factory=dict, description="Clinical metadata")
    
    @validator('match_confidence')
    def validate_confidence(cls, v):
        """Validate confidence score"""
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v


class ClinicalOutput(BaseModel):
    """Clinical application output format"""
    
    ndc_code: str = Field(..., description="NDC code")
    drug_name: str = Field(..., description="Drug name")
    generic_name: Optional[str] = Field(None, description="Generic name")
    rxnorm_cui: Optional[str] = Field(None, description="Primary RxNorm CUI")
    rxnorm_name: Optional[str] = Field(None, description="Primary RxNorm name")
    dosage_form: Optional[str] = Field(None, description="Dosage form")
    route: Optional[str] = Field(None, description="Route of administration")
    strength: Optional[str] = Field(None, description="Strength")
    ingredients: List[str] = Field(default_factory=list, description="Active ingredients")
    drug_classes: List[str] = Field(default_factory=list, description="Drug classes")
    match_confidence: float = Field(..., description="Match confidence")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last updated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BatchMatchRequest(BaseModel):
    """Batch match request"""
    
    ndc_codes: List[str] = Field(..., description="List of NDC codes to match")
    include_metadata: bool = Field(default=True, description="Include clinical metadata")
    min_confidence: float = Field(default=0.5, description="Minimum confidence threshold")


class BatchMatchResponse(BaseModel):
    """Batch match response"""
    
    matches: List[NDC_RxNorm_Match] = Field(..., description="Match results")
    total_processed: int = Field(..., description="Total NDC codes processed")
    successful_matches: int = Field(..., description="Number of successful matches")
    failed_matches: int = Field(..., description="Number of failed matches")
    processing_time: float = Field(..., description="Processing time in seconds") 