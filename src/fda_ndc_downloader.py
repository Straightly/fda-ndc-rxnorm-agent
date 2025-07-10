"""
FDA NDC Data Downloader
Downloads and processes FDA National Drug Code (NDC) data
"""

import requests
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger
import time
from urllib.parse import urljoin
import zipfile
import io

from .config import settings
from .models import NDCProduct


class FDANDCDownloader:
    """Downloads and processes FDA NDC data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FDA-NDC-RxNorm-Agent/1.0'
        })
    
    def download_ndc_data(self, force: bool = False) -> Path:
        """
        Download FDA NDC data from official sources
        
        Args:
            force: Force re-download even if data exists
            
        Returns:
            Path to downloaded data file
        """
        output_file = settings.NDC_DATA_DIR / "ndc_products.csv"
        
        if output_file.exists() and not force:
            logger.info(f"NDC data already exists at {output_file}")
            return output_file
        
        logger.info("Downloading FDA NDC data...")
        
        # Try primary FDA source first
        try:
            return self._download_from_fda_primary(output_file)
        except Exception as e:
            logger.warning(f"Failed to download from primary FDA source: {e}")
            
            # Try alternative FDA source
            try:
                return self._download_from_fda_alternative(output_file)
            except Exception as e:
                logger.error(f"Failed to download from alternative FDA source: {e}")
                raise RuntimeError("Failed to download FDA NDC data from all sources")
    
    def _download_from_fda_primary(self, output_file: Path) -> Path:
        """Download from primary FDA source"""
        logger.info("Downloading from primary FDA source...")
        
        # Download the file
        response = self.session.get(
            settings.FDA_NDC_BASE_URL,
            timeout=300,
            stream=True
        )
        response.raise_for_status()
        
        # Save to temporary file
        temp_file = settings.NDC_DATA_DIR / "ndc_temp.zip"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract and process
        self._extract_and_process_zip(temp_file, output_file)
        temp_file.unlink()  # Clean up
        
        logger.info(f"Successfully downloaded NDC data to {output_file}")
        return output_file
    
    def _download_from_fda_alternative(self, output_file: Path) -> Path:
        """Download from alternative FDA source"""
        logger.info("Downloading from alternative FDA source...")
        
        response = self.session.get(
            settings.FDA_NDC_ALTERNATIVE_URL,
            timeout=300
        )
        response.raise_for_status()
        
        # Process the text data
        self._process_text_data(response.text, output_file)
        
        logger.info(f"Successfully downloaded NDC data to {output_file}")
        return output_file
    
    def _extract_and_process_zip(self, zip_file: Path, output_file: Path):
        """Extract and process ZIP file"""
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # Find the CSV file in the ZIP
            csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
            if not csv_files:
                raise ValueError("No CSV file found in ZIP archive")
            
            csv_file = csv_files[0]
            with zip_ref.open(csv_file) as f:
                df = pd.read_csv(f)
            
            # Process and save
            self._process_dataframe(df, output_file)
    
    def _process_text_data(self, text_data: str, output_file: Path):
        """Process text data from alternative source"""
        # Split into lines and process
        lines = text_data.strip().split('\n')
        headers = lines[0].split('\t')
        
        data = []
        for line in lines[1:]:
            if line.strip():
                values = line.split('\t')
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))
        
        df = pd.DataFrame(data)
        self._process_dataframe(df, output_file)
    
    def _process_dataframe(self, df: pd.DataFrame, output_file: Path):
        """Process and clean the dataframe"""
        logger.info(f"Processing {len(df)} NDC records...")
        
        # Standardize column names
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Clean and validate NDC codes
        df['product_ndc'] = df['product_ndc'].astype(str).str.strip()
        df = df[df['product_ndc'].str.len() > 0]
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['product_ndc'])
        
        # Clean text fields
        text_columns = ['proprietary_name', 'non_proprietary_name', 'substance_name']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('nan', '')
        
        # Save processed data
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(df)} processed NDC records to {output_file}")
    
    def load_ndc_data(self) -> pd.DataFrame:
        """Load processed NDC data"""
        data_file = settings.NDC_DATA_DIR / "ndc_products.csv"
        
        if not data_file.exists():
            raise FileNotFoundError(f"NDC data file not found: {data_file}")
        
        logger.info(f"Loading NDC data from {data_file}")
        df = pd.read_csv(data_file)
        logger.info(f"Loaded {len(df)} NDC records")
        
        return df
    
    def get_ndc_products(self, limit: Optional[int] = None) -> List[NDCProduct]:
        """Get NDC products as model objects"""
        df = self.load_ndc_data()
        
        if limit:
            df = df.head(limit)
        
        products = []
        for _, row in df.iterrows():
            try:
                product = NDCProduct(**row.to_dict())
                products.append(product)
            except Exception as e:
                logger.warning(f"Failed to create NDCProduct from row: {e}")
                continue
        
        logger.info(f"Created {len(products)} NDCProduct objects")
        return products
    
    def search_ndc_by_name(self, drug_name: str, limit: int = 10) -> List[NDCProduct]:
        """Search NDC products by drug name"""
        df = self.load_ndc_data()
        
        # Search in proprietary and non-proprietary names
        mask = (
            df['proprietary_name'].str.contains(drug_name, case=False, na=False) |
            df['non_proprietary_name'].str.contains(drug_name, case=False, na=False) |
            df['substance_name'].str.contains(drug_name, case=False, na=False)
        )
        
        results_df = df[mask].head(limit)
        
        products = []
        for _, row in results_df.iterrows():
            try:
                product = NDCProduct(**row.to_dict())
                products.append(product)
            except Exception as e:
                logger.warning(f"Failed to create NDCProduct from search result: {e}")
                continue
        
        return products
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """Get statistics about the NDC data"""
        df = self.load_ndc_data()
        
        stats = {
            'total_records': len(df),
            'unique_ndcs': df['product_ndc'].nunique(),
            'unique_manufacturers': df['labeler_name'].nunique() if 'labeler_name' in df.columns else 0,
            'unique_dosage_forms': df['dosage_form_name'].nunique() if 'dosage_form_name' in df.columns else 0,
            'unique_routes': df['route_name'].nunique() if 'route_name' in df.columns else 0,
            'marketing_categories': df['marketing_category_name'].value_counts().to_dict() if 'marketing_category_name' in df.columns else {},
            'data_columns': list(df.columns)
        }
        
        return stats 