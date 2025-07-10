"""
FastAPI Interface
RESTful API for the FDA NDC to RxNorm Matching Agent
"""

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import time
import logging

from .agent import FDA_NDC_RxNorm_Agent
from .models import BatchMatchRequest, BatchMatchResponse, ClinicalOutput
from .config import settings


# Create FastAPI app
app = FastAPI(
    title="FDA NDC to RxNorm Matching Agent API",
    description="API for matching FDA National Drug Codes (NDC) to RxNorm concepts",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = None


def get_agent() -> FDA_NDC_RxNorm_Agent:
    """Get or create agent instance"""
    global agent
    if agent is None:
        agent = FDA_NDC_RxNorm_Agent()
    return agent


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    try:
        get_agent()
        print("FDA NDC to RxNorm Agent initialized successfully")
    except Exception as e:
        print(f"Failed to initialize agent: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        agent = get_agent()
        status = agent.get_status()
        return {
            "status": "healthy",
            "agent_status": status,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/ndc/{ndc_code}")
async def get_ndc_match(ndc_code: str):
    """Get RxNorm match for a specific NDC code"""
    try:
        agent = get_agent()
        match = agent.db_manager.get_match_by_ndc(ndc_code)
        
        if not match:
            raise HTTPException(status_code=404, detail=f"No match found for NDC: {ndc_code}")
        
        return match.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving NDC match: {str(e)}")


@app.get("/ndc-info/{ndc_code}")
async def get_ndc_info(ndc_code: str):
    """Get NDC product information directly from downloaded data"""
    try:
        agent = get_agent()
        df = agent.ndc_downloader.load_ndc_data()
        
        # Search for NDC in both product_ndc and package_ndc columns
        mask = (df['product_ndc'] == ndc_code) | (df['package_ndc'] == ndc_code)
        matching_rows = df[mask]
        
        if matching_rows.empty:
            raise HTTPException(status_code=404, detail=f"NDC not found: {ndc_code}")
        
        # Return the first match
        row = matching_rows.iloc[0]
        
        # Convert numpy types to native Python types
        def convert_value(val):
            if pd.isna(val):
                return None
            elif hasattr(val, 'item'):  # numpy scalar
                return val.item()
            else:
                return str(val)
        
        return {
            "ndc_code": ndc_code,
            "product_ndc": convert_value(row.get('product_ndc')),
            "package_ndc": convert_value(row.get('package_ndc')),
            "package_description": convert_value(row.get('package_description')),
            "start_marketing_date": convert_value(row.get('start_marketing_date')),
            "end_marketing_date": convert_value(row.get('end_marketing_date')),
            "exclude_flag": convert_value(row.get('exclude_flag')),
            "sample_package": convert_value(row.get('sample_package')),
            "source": "NBER FDA NDC Package Data"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving NDC info: {str(e)}")


@app.get("/drugs/search")
async def search_drugs(
    query: str = Query(..., description="Drug name to search for"),
    limit: int = Query(10, description="Maximum number of results")
):
    """Search for drugs by name"""
    try:
        agent = get_agent()
        matches = agent.db_manager.search_matches(query, limit=limit)
        
        results = []
        for match in matches:
            if match.rxnorm_concepts:
                results.append({
                    "ndc_code": match.ndc_product.product_ndc,
                    "drug_name": match.ndc_product.proprietary_name or match.ndc_product.non_proprietary_name,
                    "rxnorm_cui": match.rxnorm_concepts[0].rxcui,
                    "rxnorm_name": match.rxnorm_concepts[0].name,
                    "match_confidence": match.match_confidence
                })
        
        return {"results": results, "total": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching drugs: {str(e)}")


@app.post("/batch-match")
async def batch_match(request: BatchMatchRequest, background_tasks: BackgroundTasks):
    """Batch match multiple NDC codes"""
    try:
        agent = get_agent()
        start_time = time.time()
        
        # Process NDC codes
        matches = []
        failed_ndcs = []
        
        for ndc_code in request.ndc_codes:
            try:
                # Check if already in database
                existing_match = agent.db_manager.get_match_by_ndc(ndc_code)
                if existing_match:
                    matches.append(existing_match)
                    continue
                
                # Find NDC product
                ndc_products = agent.ndc_downloader.search_ndc_by_name(ndc_code, limit=1)
                if not ndc_products:
                    failed_ndcs.append(ndc_code)
                    continue
                
                # Match to RxNorm
                match = agent._match_single_ndc(ndc_products[0])
                if match and match.match_confidence >= request.min_confidence:
                    matches.append(match)
                    # Save to database
                    agent.db_manager.save_matches([match])
                else:
                    failed_ndcs.append(ndc_code)
                    
            except Exception as e:
                failed_ndcs.append(ndc_code)
                continue
        
        processing_time = time.time() - start_time
        
        response = BatchMatchResponse(
            matches=matches,
            total_processed=len(request.ndc_codes),
            successful_matches=len(matches),
            failed_matches=len(failed_ndcs),
            processing_time=processing_time
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch matching: {str(e)}")


@app.get("/statistics")
async def get_statistics():
    """Get agent and database statistics"""
    try:
        agent = get_agent()
        agent_status = agent.get_status()
        db_stats = agent.db_manager.get_statistics()
        ndc_stats = agent.ndc_downloader.get_data_statistics()
        
        return {
            "agent_status": agent_status,
            "database_statistics": db_stats,
            "ndc_statistics": ndc_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@app.get("/clinical-outputs")
async def get_clinical_outputs(
    min_confidence: float = Query(0.5, description="Minimum confidence threshold"),
    limit: int = Query(100, description="Maximum number of results")
):
    """Get clinical outputs with confidence filtering"""
    try:
        agent = get_agent()
        high_confidence_matches = agent.db_manager.get_high_confidence_matches(
            min_confidence=min_confidence, 
            limit=limit
        )
        
        clinical_outputs = agent.generate_clinical_output(high_confidence_matches)
        
        return {
            "clinical_outputs": [output.dict() for output in clinical_outputs],
            "total": len(clinical_outputs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving clinical outputs: {str(e)}")


@app.post("/download-ndc")
async def download_ndc_data(force: bool = False):
    """Download FDA NDC data"""
    try:
        agent = get_agent()
        file_path = agent.download_ndc_data(force=force)
        
        return {
            "message": "NDC data downloaded successfully",
            "file_path": str(file_path)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading NDC data: {str(e)}")


@app.post("/run-pipeline")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    force_download: bool = False,
    batch_size: int = 1000,
    max_workers: int = 4
):
    """Run the complete matching pipeline"""
    try:
        agent = get_agent()
        
        # Run pipeline in background
        def run_pipeline_task():
            try:
                return agent.run_complete_pipeline(
                    force_download=force_download,
                    batch_size=batch_size,
                    max_workers=max_workers
                )
            except Exception as e:
                print(f"Pipeline failed: {e}")
                return None
        
        background_tasks.add_task(run_pipeline_task)
        
        return {
            "message": "Pipeline started in background",
            "parameters": {
                "force_download": force_download,
                "batch_size": batch_size,
                "max_workers": max_workers
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting pipeline: {str(e)}")


@app.get("/output-files")
async def list_output_files():
    """List available output files"""
    try:
        agent = get_agent()
        output_files = agent._get_output_files()
        
        return {
            "output_files": output_files,
            "total_files": len(output_files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing output files: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    ) 