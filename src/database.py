"""
Database Manager
Handles database operations for storing and retrieving NDC to RxNorm matches
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from .config import settings
from .models import NDC_RxNorm_Match


Base = declarative_base()


class NDC_RxNorm_Match_Record(Base):
    """Database model for NDC to RxNorm matches"""
    __tablename__ = 'ndc_rxnorm_matches'
    
    id = Column(Integer, primary_key=True)
    ndc_code = Column(String(20), nullable=False, index=True)
    rxcui = Column(String(20), nullable=True, index=True)
    rxnorm_name = Column(String(500), nullable=True)
    match_confidence = Column(Float, nullable=False)
    match_method = Column(String(100), nullable=False)
    match_date = Column(DateTime, nullable=False, default=datetime.now)
    clinical_metadata = Column(Text, nullable=True)  # JSON string
    ndc_product_data = Column(Text, nullable=True)  # JSON string
    rxnorm_concepts_data = Column(Text, nullable=True)  # JSON string
    rxnorm_drugs_data = Column(Text, nullable=True)  # JSON string


class DatabaseManager:
    """Manages database operations for NDC to RxNorm matches"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize database engine"""
        try:
            self.engine = create_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO,
                connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info(f"Database engine initialized: {settings.DATABASE_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def save_matches(self, matches: List[NDC_RxNorm_Match]):
        """Save NDC to RxNorm matches to database"""
        if not matches:
            return
        
        try:
            with self.get_session() as session:
                for match in matches:
                    # Extract primary RxCUI and name
                    primary_rxcui = None
                    primary_rxnorm_name = None
                    
                    if match.rxnorm_concepts:
                        primary_rxcui = match.rxnorm_concepts[0].rxcui
                        primary_rxnorm_name = match.rxnorm_concepts[0].name
                    
                    # Create database record
                    record = NDC_RxNorm_Match_Record(
                        ndc_code=match.ndc_product.product_ndc,
                        rxcui=primary_rxcui,
                        rxnorm_name=primary_rxnorm_name,
                        match_confidence=match.match_confidence,
                        match_method=match.match_method,
                        match_date=match.match_date,
                        clinical_metadata=json.dumps(match.clinical_metadata) if match.clinical_metadata else None,
                        ndc_product_data=json.dumps(match.ndc_product.dict()) if match.ndc_product else None,
                        rxnorm_concepts_data=json.dumps([c.dict() for c in match.rxnorm_concepts]) if match.rxnorm_concepts else None,
                        rxnorm_drugs_data=json.dumps([d.dict() for d in match.rxnorm_drugs]) if match.rxnorm_drugs else None
                    )
                    
                    session.add(record)
                
                session.commit()
                logger.info(f"Saved {len(matches)} matches to database")
                
        except Exception as e:
            logger.error(f"Failed to save matches to database: {e}")
            raise
    
    def get_match_by_ndc(self, ndc_code: str) -> Optional[NDC_RxNorm_Match]:
        """Get match by NDC code"""
        try:
            with self.get_session() as session:
                record = session.query(NDC_RxNorm_Match_Record).filter(
                    NDC_RxNorm_Match_Record.ndc_code == ndc_code
                ).first()
                
                if record:
                    return self._record_to_match(record)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get match for NDC {ndc_code}: {e}")
            return None
    
    def get_matches_by_rxcui(self, rxcui: str) -> List[NDC_RxNorm_Match]:
        """Get all matches for a specific RxCUI"""
        try:
            with self.get_session() as session:
                records = session.query(NDC_RxNorm_Match_Record).filter(
                    NDC_RxNorm_Match_Record.rxcui == rxcui
                ).all()
                
                return [self._record_to_match(record) for record in records]
                
        except Exception as e:
            logger.error(f"Failed to get matches for RxCUI {rxcui}: {e}")
            return []
    
    def search_matches(self, query: str, limit: int = 100) -> List[NDC_RxNorm_Match]:
        """Search matches by drug name"""
        try:
            with self.get_session() as session:
                records = session.query(NDC_RxNorm_Match_Record).filter(
                    NDC_RxNorm_Match_Record.rxnorm_name.contains(query)
                ).limit(limit).all()
                
                return [self._record_to_match(record) for record in records]
                
        except Exception as e:
            logger.error(f"Failed to search matches for query '{query}': {e}")
            return []
    
    def get_high_confidence_matches(self, min_confidence: float = 0.8, limit: int = 1000) -> List[NDC_RxNorm_Match]:
        """Get matches with high confidence scores"""
        try:
            with self.get_session() as session:
                records = session.query(NDC_RxNorm_Match_Record).filter(
                    NDC_RxNorm_Match_Record.match_confidence >= min_confidence
                ).order_by(NDC_RxNorm_Match_Record.match_confidence.desc()).limit(limit).all()
                
                return [self._record_to_match(record) for record in records]
                
        except Exception as e:
            logger.error(f"Failed to get high confidence matches: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_session() as session:
                total_matches = session.query(NDC_RxNorm_Match_Record).count()
                unique_ndcs = session.query(NDC_RxNorm_Match_Record.ndc_code).distinct().count()
                unique_rxcuis = session.query(NDC_RxNorm_Match_Record.rxcui).distinct().count()
                
                # Average confidence
                avg_confidence = session.query(NDC_RxNorm_Match_Record.match_confidence).all()
                avg_confidence = sum([r[0] for r in avg_confidence]) / len(avg_confidence) if avg_confidence else 0
                
                # Recent matches (last 24 hours)
                from datetime import timedelta
                yesterday = datetime.now() - timedelta(days=1)
                recent_matches = session.query(NDC_RxNorm_Match_Record).filter(
                    NDC_RxNorm_Match_Record.match_date >= yesterday
                ).count()
                
                return {
                    'total_matches': total_matches,
                    'unique_ndcs': unique_ndcs,
                    'unique_rxcuis': unique_rxcuis,
                    'average_confidence': round(avg_confidence, 3),
                    'recent_matches_24h': recent_matches
                }
                
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {
                'total_matches': 0,
                'unique_ndcs': 0,
                'unique_rxcuis': 0,
                'average_confidence': 0.0,
                'recent_matches_24h': 0
            }
    
    def _record_to_match(self, record: NDC_RxNorm_Match_Record) -> NDC_RxNorm_Match:
        """Convert database record to NDC_RxNorm_Match object"""
        try:
            # Parse JSON data
            ndc_product_data = json.loads(record.ndc_product_data) if record.ndc_product_data else {}
            rxnorm_concepts_data = json.loads(record.rxnorm_concepts_data) if record.rxnorm_concepts_data else []
            rxnorm_drugs_data = json.loads(record.rxnorm_drugs_data) if record.rxnorm_drugs_data else []
            clinical_metadata = json.loads(record.clinical_metadata) if record.clinical_metadata else {}
            
            # Import models here to avoid circular imports
            from .models import NDCProduct, RxNormConcept, RxNormDrug
            
            # Create objects
            ndc_product = NDCProduct(**ndc_product_data) if ndc_product_data else None
            rxnorm_concepts = [RxNormConcept(**c) for c in rxnorm_concepts_data]
            rxnorm_drugs = [RxNormDrug(**d) for d in rxnorm_drugs_data]
            
            # Create match object
            match = NDC_RxNorm_Match(
                ndc_product=ndc_product,
                rxnorm_concepts=rxnorm_concepts,
                rxnorm_drugs=rxnorm_drugs,
                match_confidence=record.match_confidence,
                match_method=record.match_method,
                match_date=record.match_date,
                clinical_metadata=clinical_metadata
            )
            
            return match
            
        except Exception as e:
            logger.error(f"Failed to convert database record to match: {e}")
            raise
    
    def cleanup_old_matches(self, days_old: int = 30):
        """Clean up old matches from database"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with self.get_session() as session:
                deleted_count = session.query(NDC_RxNorm_Match_Record).filter(
                    NDC_RxNorm_Match_Record.match_date < cutoff_date
                ).delete()
                
                session.commit()
                logger.info(f"Cleaned up {deleted_count} old matches from database")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old matches: {e}")
            raise
    
    def export_matches(self, output_file: str, format: str = 'json'):
        """Export all matches to file"""
        try:
            with self.get_session() as session:
                records = session.query(NDC_RxNorm_Match_Record).all()
                matches = [self._record_to_match(record) for record in records]
            
            if format.lower() == 'json':
                import json
                with open(output_file, 'w') as f:
                    json.dump([match.dict() for match in matches], f, indent=2, default=str)
            elif format.lower() == 'csv':
                import pandas as pd
                df = pd.DataFrame([match.dict() for match in matches])
                df.to_csv(output_file, index=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Exported {len(matches)} matches to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export matches: {e}")
            raise 