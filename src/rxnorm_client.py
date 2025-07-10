"""
RxNorm API Client
Interfaces with the RxNorm API to match NDC codes to RxNorm concepts
"""

import requests
import time
from typing import Optional, List, Dict, Any
from loguru import logger
import re
from urllib.parse import quote

from .config import settings
from .models import RxNormConcept, RxNormDrug, RxNormIngredient


class RxNormClient:
    """Client for RxNorm API interactions"""
    
    def __init__(self):
        self.base_url = settings.RXNORM_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FDA-NDC-RxNorm-Agent/1.0'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the RxNorm API with retry logic"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(settings.RXNORM_API_RETRY_ATTEMPTS):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=settings.RXNORM_API_TIMEOUT
                )
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"RxNorm API request failed (attempt {attempt + 1}): {e}")
                if attempt < settings.RXNORM_API_RETRY_ATTEMPTS - 1:
                    time.sleep(settings.RXNORM_API_RETRY_DELAY * (attempt + 1))
                else:
                    raise RuntimeError(f"Failed to make RxNorm API request after {settings.RXNORM_API_RETRY_ATTEMPTS} attempts")
        
        # This should never be reached due to the raise above, but satisfies type checker
        return {}
    
    def find_rxcui_by_ndc(self, ndc: str) -> Optional[str]:
        """
        Find RxNorm CUI by NDC code
        
        Args:
            ndc: NDC code (with or without hyphens)
            
        Returns:
            RxNorm CUI if found, None otherwise
        """
        # Clean NDC format
        ndc_clean = self._clean_ndc(ndc)
        
        try:
            # Try direct NDC lookup
            data = self._make_request("ndcstatus", {"ndc": ndc_clean})
            
            if data.get("ndcStatus") and data["ndcStatus"].get("status") == "Active":
                return data["ndcStatus"].get("rxcui")
            
            # Try alternative lookup methods
            return self._find_rxcui_alternative(ndc_clean)
            
        except Exception as e:
            logger.warning(f"Failed to find RxCUI for NDC {ndc}: {e}")
            return None
    
    def _clean_ndc(self, ndc: str) -> str:
        """Clean and standardize NDC format"""
        # Remove hyphens and spaces
        ndc_clean = re.sub(r'[-\s]', '', ndc)
        
        # Ensure 11 digits
        if len(ndc_clean) == 11:
            return ndc_clean
        elif len(ndc_clean) == 10:
            # Pad with leading zero if needed
            return "0" + ndc_clean
        else:
            return ndc_clean
    
    def _find_rxcui_alternative(self, ndc: str) -> Optional[str]:
        """Alternative methods to find RxCUI"""
        try:
            # Try ingredient-based search
            ingredient_data = self._make_request("ndcstatus", {"ndc": ndc})
            
            if ingredient_data.get("ndcStatus"):
                # Extract ingredient information
                ingredient_name = ingredient_data["ndcStatus"].get("ingredient")
                if ingredient_name:
                    return self._find_rxcui_by_ingredient(ingredient_name)
            
            return None
            
        except Exception as e:
            logger.warning(f"Alternative RxCUI lookup failed for NDC {ndc}: {e}")
            return None
    
    def _find_rxcui_by_ingredient(self, ingredient_name: str) -> Optional[str]:
        """Find RxCUI by ingredient name"""
        try:
            # Search for ingredient
            data = self._make_request("drugs", {"name": ingredient_name})
            
            if data.get("drugGroup") and data["drugGroup"].get("conceptGroup"):
                for concept_group in data["drugGroup"]["conceptGroup"]:
                    if concept_group.get("concept"):
                        # Return the first available RxCUI
                        return concept_group["concept"][0].get("rxcui")
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to find RxCUI by ingredient {ingredient_name}: {e}")
            return None
    
    def get_rxnorm_concept(self, rxcui: str) -> Optional[RxNormConcept]:
        """
        Get RxNorm concept details by RxCUI
        
        Args:
            rxcui: RxNorm concept unique identifier
            
        Returns:
            RxNormConcept object if found, None otherwise
        """
        try:
            data = self._make_request("rxcui", {"rxcui": rxcui})
            
            if data.get("idgroup") and data["idgroup"].get("rxnormId"):
                # Get concept details
                concept_data = self._make_request("rxcui", {"rxcui": rxcui, "allsrc": "1"})
                
                if concept_data.get("relatedGroup") and concept_data["relatedGroup"].get("conceptGroup"):
                    for concept_group in concept_data["relatedGroup"]["conceptGroup"]:
                        if concept_group.get("concept"):
                            concept = concept_group["concept"][0]
                            return RxNormConcept(
                                rxcui=rxcui,
                                name=concept.get("name", ""),
                                synonym=concept.get("synonym"),
                                tty=concept.get("tty", ""),
                                language=concept.get("language", "ENG"),
                                suppress=concept.get("suppress", "N"),
                                umlscui=concept.get("umlscui")
                            )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get RxNorm concept for RxCUI {rxcui}: {e}")
            return None
    
    def get_rxnorm_drug(self, rxcui: str) -> Optional[RxNormDrug]:
        """
        Get RxNorm drug details by RxCUI
        
        Args:
            rxcui: RxNorm concept unique identifier
            
        Returns:
            RxNormDrug object if found, None otherwise
        """
        try:
            # Get drug information
            data = self._make_request("rxcui", {"rxcui": rxcui, "allsrc": "1"})
            
            if data.get("relatedGroup") and data["relatedGroup"].get("conceptGroup"):
                drug_info = None
                ingredients = []
                
                for concept_group in data["relatedGroup"]["conceptGroup"]:
                    if concept_group.get("concept"):
                        concept = concept_group["concept"][0]
                        tty = concept.get("tty", "")
                        
                        # Get drug information
                        if tty in ["BN", "PIN", "IN"]:
                            drug_info = {
                                "rxcui": rxcui,
                                "name": concept.get("name", ""),
                                "synonym": concept.get("synonym"),
                                "tty": tty,
                                "base_names": concept.get("baseNames", {}).get("baseName", [])
                            }
                        
                        # Get ingredient information
                        if tty == "IN":
                            ingredient = RxNormIngredient(
                                rxcui=concept.get("rxcui", ""),
                                name=concept.get("name", ""),
                                base_names=concept.get("baseNames", {}).get("baseName", [])
                            )
                            ingredients.append(ingredient)
                
                if drug_info:
                    return RxNormDrug(
                        **drug_info,
                        ingredients=ingredients if ingredients else None
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get RxNorm drug for RxCUI {rxcui}: {e}")
            return None
    
    def search_drugs(self, query: str, max_results: int = 10) -> List[RxNormDrug]:
        """
        Search for drugs by name
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of RxNormDrug objects
        """
        try:
            data = self._make_request("drugs", {"name": query})
            
            drugs = []
            if data.get("drugGroup") and data["drugGroup"].get("conceptGroup"):
                for concept_group in data["drugGroup"]["conceptGroup"]:
                    if concept_group.get("concept"):
                        for concept in concept_group["concept"][:max_results]:
                            rxcui = concept.get("rxcui")
                            if rxcui:
                                drug = self.get_rxnorm_drug(rxcui)
                                if drug:
                                    drugs.append(drug)
            
            return drugs[:max_results]
            
        except Exception as e:
            logger.warning(f"Failed to search drugs for query '{query}': {e}")
            return []
    
    def get_drug_interactions(self, rxcui: str) -> List[Dict[str, Any]]:
        """
        Get drug interactions for a given RxCUI
        
        Args:
            rxcui: RxNorm concept unique identifier
            
        Returns:
            List of interaction information
        """
        try:
            data = self._make_request("interaction", {"rxcui": rxcui})
            
            interactions = []
            if data.get("interactionTypeGroup"):
                for group in data["interactionTypeGroup"]:
                    if group.get("interactionType"):
                        for interaction_type in group["interactionType"]:
                            if interaction_type.get("interactionPair"):
                                for pair in interaction_type["interactionPair"]:
                                    interactions.append({
                                        "severity": pair.get("severity"),
                                        "description": pair.get("description"),
                                        "interaction_type": interaction_type.get("comment"),
                                        "drugs": pair.get("interactionConcept", [])
                                    })
            
            return interactions
            
        except Exception as e:
            logger.warning(f"Failed to get drug interactions for RxCUI {rxcui}: {e}")
            return []
    
    def get_drug_classes(self, rxcui: str) -> List[Dict[str, Any]]:
        """
        Get drug classes for a given RxCUI
        
        Args:
            rxcui: RxNorm concept unique identifier
            
        Returns:
            List of drug class information
        """
        try:
            data = self._make_request("rxcui", {"rxcui": rxcui, "allsrc": "1"})
            
            classes = []
            if data.get("relatedGroup") and data["relatedGroup"].get("conceptGroup"):
                for concept_group in data["relatedGroup"]["conceptGroup"]:
                    if concept_group.get("concept"):
                        for concept in concept_group["concept"]:
                            if concept.get("tty") in ["VA", "VB", "VC", "VD", "VE", "VF", "VG", "VH", "VI", "VJ"]:
                                classes.append({
                                    "class_type": concept.get("tty"),
                                    "class_name": concept.get("name"),
                                    "class_id": concept.get("rxcui")
                                })
            
            return classes
            
        except Exception as e:
            logger.warning(f"Failed to get drug classes for RxCUI {rxcui}: {e}")
            return [] 