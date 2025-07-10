"""
FDA NDC to RxNorm Matching Agent
Main agent class that orchestrates the entire matching pipeline
"""

import time
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from tqdm import tqdm

from .config import settings
from .models import NDCProduct, NDC_RxNorm_Match, ClinicalOutput
from .fda_ndc_downloader import FDANDCDownloader
from .rxnorm_client import RxNormClient
from .database import DatabaseManager


class FDA_NDC_RxNorm_Agent:
    """Main agent for FDA NDC to RxNorm matching"""
    
    def __init__(self):
        self.ndc_downloader = FDANDCDownloader()
        self.rxnorm_client = RxNormClient()
        self.db_manager = DatabaseManager()
        
        # Initialize database
        self.db_manager.initialize_database()
    
    def download_ndc_data(self, force: bool = False) -> Path:
        """
        Download FDA NDC data
        
        Args:
            force: Force re-download even if data exists
            
        Returns:
            Path to downloaded data file
        """
        logger.info("Starting FDA NDC data download...")
        return self.ndc_downloader.download_ndc_data(force=force)
    
    def match_ndc_to_rxnorm(self, batch_size: int = 1000, max_workers: int = 4) -> List[NDC_RxNorm_Match]:
        """
        Match NDC codes to RxNorm concepts
        
        Args:
            batch_size: Number of NDC codes to process in each batch
            max_workers: Maximum number of worker threads
            
        Returns:
            List of NDC to RxNorm matches
        """
        logger.info("Starting NDC to RxNorm matching...")
        
        # Load NDC data
        ndc_products = self.ndc_downloader.get_ndc_products()
        logger.info(f"Loaded {len(ndc_products)} NDC products for matching")
        
        # Process in batches
        all_matches = []
        total_batches = (len(ndc_products) + batch_size - 1) // batch_size
        
        with tqdm(total=len(ndc_products), desc="Matching NDC to RxNorm") as pbar:
            for i in range(0, len(ndc_products), batch_size):
                batch = ndc_products[i:i + batch_size]
                batch_matches = self._process_batch(batch, max_workers)
                all_matches.extend(batch_matches)
                
                # Save batch results
                self._save_batch_results(batch_matches, i // batch_size)
                
                pbar.update(len(batch))
                
                # Rate limiting to be respectful to APIs
                time.sleep(0.1)
        
        logger.info(f"Completed matching. Found {len(all_matches)} matches")
        return all_matches
    
    def _process_batch(self, ndc_products: List[NDCProduct], max_workers: int) -> List[NDC_RxNorm_Match]:
        """Process a batch of NDC products"""
        matches = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all NDC products for processing
            future_to_product = {
                executor.submit(self._match_single_ndc, product): product 
                for product in ndc_products
            }
            
            # Collect results
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    match = future.result()
                    if match:
                        matches.append(match)
                except Exception as e:
                    logger.warning(f"Failed to match NDC {product.product_ndc}: {e}")
        
        return matches
    
    def _match_single_ndc(self, ndc_product: NDCProduct) -> Optional[NDC_RxNorm_Match]:
        """Match a single NDC product to RxNorm concepts"""
        try:
            # Find RxCUI for NDC
            rxcui = self.rxnorm_client.find_rxcui_by_ndc(ndc_product.product_ndc)
            
            if not rxcui:
                return None
            
            # Get RxNorm concepts and drugs
            rxnorm_concepts = []
            rxnorm_drugs = []
            
            # Get primary concept
            concept = self.rxnorm_client.get_rxnorm_concept(rxcui)
            if concept:
                rxnorm_concepts.append(concept)
            
            # Get drug information
            drug = self.rxnorm_client.get_rxnorm_drug(rxcui)
            if drug:
                rxnorm_drugs.append(drug)
            
            # Calculate match confidence
            confidence = self._calculate_match_confidence(ndc_product, rxnorm_concepts, rxnorm_drugs)
            
            # Get clinical metadata
            clinical_metadata = self._get_clinical_metadata(rxcui)
            
            # Create match result
            match = NDC_RxNorm_Match(
                ndc_product=ndc_product,
                rxnorm_concepts=rxnorm_concepts,
                rxnorm_drugs=rxnorm_drugs,
                match_confidence=confidence,
                match_method="direct_ndc_lookup",
                clinical_metadata=clinical_metadata
            )
            
            return match
            
        except Exception as e:
            logger.warning(f"Error matching NDC {ndc_product.product_ndc}: {e}")
            return None
    
    def _calculate_match_confidence(self, ndc_product: NDCProduct, 
                                  rxnorm_concepts: List, rxnorm_drugs: List) -> float:
        """Calculate confidence score for the match"""
        confidence = 0.0
        
        # Base confidence for finding RxCUI
        if rxnorm_concepts or rxnorm_drugs:
            confidence += 0.5
        
        # Additional confidence for name matching
        if ndc_product.proprietary_name and rxnorm_concepts:
            ndc_name = ndc_product.proprietary_name.lower()
            for concept in rxnorm_concepts:
                if concept.name.lower() in ndc_name or ndc_name in concept.name.lower():
                    confidence += 0.3
                    break
        
        # Additional confidence for ingredient matching
        if ndc_product.substance_name and rxnorm_drugs:
            ndc_ingredient = ndc_product.substance_name.lower()
            for drug in rxnorm_drugs:
                if drug.ingredients:
                    for ingredient in drug.ingredients:
                        if ingredient.name.lower() in ndc_ingredient or ndc_ingredient in ingredient.name.lower():
                            confidence += 0.2
                            break
        
        return min(confidence, 1.0)
    
    def _get_clinical_metadata(self, rxcui: str) -> Dict[str, Any]:
        """Get clinical metadata for RxCUI"""
        metadata = {}
        
        try:
            # Get drug interactions
            interactions = self.rxnorm_client.get_drug_interactions(rxcui)
            if interactions:
                metadata['interactions'] = interactions
            
            # Get drug classes
            drug_classes = self.rxnorm_client.get_drug_classes(rxcui)
            if drug_classes:
                metadata['drug_classes'] = drug_classes
                
        except Exception as e:
            logger.warning(f"Failed to get clinical metadata for RxCUI {rxcui}: {e}")
        
        return metadata
    
    def _save_batch_results(self, matches: List[NDC_RxNorm_Match], batch_num: int):
        """Save batch results to database and file"""
        if not matches:
            return
        
        # Save to database
        self.db_manager.save_matches(matches)
        
        # Save to file
        output_file = settings.OUTPUT_DIR / f"batch_{batch_num:04d}_matches.json"
        with open(output_file, 'w') as f:
            json.dump([match.dict() for match in matches], f, indent=2, default=str)
    
    def run_complete_pipeline(self, force_download: bool = False, 
                            batch_size: int = 1000, max_workers: int = 4) -> Dict[str, Any]:
        """
        Run the complete pipeline: download NDC data and match to RxNorm
        
        Args:
            force_download: Force re-download of NDC data
            batch_size: Batch size for processing
            max_workers: Maximum number of workers
            
        Returns:
            Pipeline results summary
        """
        start_time = time.time()
        logger.info("Starting complete FDA NDC to RxNorm matching pipeline...")
        
        # Step 1: Download NDC data
        logger.info("Step 1: Downloading FDA NDC data...")
        ndc_file = self.download_ndc_data(force=force_download)
        
        # Step 2: Match NDC to RxNorm
        logger.info("Step 2: Matching NDC codes to RxNorm concepts...")
        matches = self.match_ndc_to_rxnorm(batch_size=batch_size, max_workers=max_workers)
        
        # Step 3: Generate clinical output
        logger.info("Step 3: Generating clinical output...")
        clinical_outputs = self.generate_clinical_output(matches)
        
        # Step 4: Save final results
        logger.info("Step 4: Saving final results...")
        self.save_final_results(matches, clinical_outputs)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Generate summary
        summary = {
            'total_ndc_products': len(self.ndc_downloader.get_ndc_products()),
            'successful_matches': len(matches),
            'clinical_outputs': len(clinical_outputs),
            'processing_time_seconds': processing_time,
            'match_rate': len(matches) / len(self.ndc_downloader.get_ndc_products()) * 100 if self.ndc_downloader.get_ndc_products() else 0,
            'output_files': self._get_output_files()
        }
        
        logger.info("Pipeline completed successfully!")
        logger.info(f"Summary: {summary}")
        
        return summary
    
    def generate_clinical_output(self, matches: List[NDC_RxNorm_Match]) -> List[ClinicalOutput]:
        """Generate clinical output format from matches"""
        clinical_outputs = []
        
        for match in matches:
            try:
                # Extract primary RxNorm information
                primary_rxcui = None
                primary_rxnorm_name = None
                
                if match.rxnorm_concepts:
                    primary_rxcui = match.rxnorm_concepts[0].rxcui
                    primary_rxnorm_name = match.rxnorm_concepts[0].name
                
                # Extract ingredients
                ingredients = []
                if match.rxnorm_drugs and match.rxnorm_drugs[0].ingredients:
                    ingredients = [ing.name for ing in match.rxnorm_drugs[0].ingredients]
                
                # Extract drug classes
                drug_classes = []
                if match.clinical_metadata.get('drug_classes'):
                    drug_classes = [cls['class_name'] for cls in match.clinical_metadata['drug_classes']]
                
                # Create clinical output
                clinical_output = ClinicalOutput(
                    ndc_code=match.ndc_product.product_ndc,
                    drug_name=match.ndc_product.proprietary_name or match.ndc_product.non_proprietary_name or "Unknown",
                    generic_name=match.ndc_product.non_proprietary_name,
                    rxnorm_cui=primary_rxcui,
                    rxnorm_name=primary_rxnorm_name,
                    dosage_form=match.ndc_product.dosage_form_name,
                    route=match.ndc_product.route_name,
                    strength=f"{match.ndc_product.strength_number} {match.ndc_product.strength_unit}" if match.ndc_product.strength_number and match.ndc_product.strength_unit else None,
                    ingredients=ingredients,
                    drug_classes=drug_classes,
                    match_confidence=match.match_confidence
                )
                
                clinical_outputs.append(clinical_output)
                
            except Exception as e:
                logger.warning(f"Failed to generate clinical output for NDC {match.ndc_product.product_ndc}: {e}")
                continue
        
        return clinical_outputs
    
    def save_final_results(self, matches: List[NDC_RxNorm_Match], 
                          clinical_outputs: List[ClinicalOutput]):
        """Save final results in various formats"""
        
        # Save matches in JSON format
        matches_file = settings.OUTPUT_DIR / "final_matches.json"
        with open(matches_file, 'w') as f:
            json.dump([match.dict() for match in matches], f, indent=2, default=str)
        
        # Save clinical outputs in JSON format
        clinical_file = settings.OUTPUT_DIR / "clinical_outputs.json"
        with open(clinical_file, 'w') as f:
            json.dump([output.dict() for output in clinical_outputs], f, indent=2, default=str)
        
        # Save clinical outputs in CSV format
        clinical_csv_file = settings.OUTPUT_DIR / "clinical_outputs.csv"
        clinical_df = pd.DataFrame([output.dict() for output in clinical_outputs])
        clinical_df.to_csv(clinical_csv_file, index=False)
        
        logger.info(f"Saved {len(matches)} matches and {len(clinical_outputs)} clinical outputs")
    
    def _get_output_files(self) -> List[str]:
        """Get list of output files"""
        output_files = []
        for file_path in settings.OUTPUT_DIR.glob("*"):
            if file_path.is_file():
                output_files.append(str(file_path))
        return output_files
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent"""
        try:
            ndc_stats = self.ndc_downloader.get_data_statistics()
            db_stats = self.db_manager.get_statistics()
            
            total_ndc = ndc_stats.get('total_records', 0)
            rxnorm_matches = db_stats.get('total_matches', 0)
            match_rate = (rxnorm_matches / total_ndc * 100) if total_ndc > 0 else 0
            
            return {
                'ndc_downloaded': settings.NDC_DATA_DIR.exists(),
                'total_ndc_records': total_ndc,
                'rxnorm_matches': rxnorm_matches,
                'match_rate': match_rate,
                'database_status': 'connected' if self.db_manager.is_connected() else 'disconnected',
                'output_files_count': len(self._get_output_files())
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'ndc_downloaded': False,
                'total_ndc_records': 0,
                'rxnorm_matches': 0,
                'match_rate': 0.0,
                'database_status': 'error',
                'output_files_count': 0
            } 