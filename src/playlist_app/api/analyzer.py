from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel

from ..models.database import get_db
from ..services.analyzer_manager import analyzer_manager

router = APIRouter(prefix="/api/analyzer", tags=["analyzer"])

class AnalyzeBatchesRequest(BaseModel):
    batch_size: int = 50
    category: Optional[str] = None

@router.get("/categorize")
async def categorize_files(db: Session = Depends(get_db)):
    """Categorize files by length"""
    try:
        # Include all files for categorization, not just unanalyzed ones
        categories = analyzer_manager.categorize_files_by_length(db, include_analyzed=True)
        return {
            "status": "success",
            "categories": categories,
            "total_files": sum(len(files) for files in categories.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")

@router.post("/analyze-batches")
async def analyze_batches(
    request: AnalyzeBatchesRequest,
    db: Session = Depends(get_db)
):
    """Create batches of files by category for later processing"""
    try:
        # Get batches - include all files for categorization
        batches = analyzer_manager.get_analysis_batches(db, request.batch_size, include_analyzed=True)
        
        # Filter by category if specified
        if request.category:
            if request.category not in batches:
                raise HTTPException(status_code=400, detail=f"Category '{request.category}' not found")
            batches = {request.category: batches[request.category]}
        
        # Process each batch
        batch_results = []
        total_files = 0
        total_batches = 0
        
        for category, category_batches in batches.items():
            for batch in category_batches:
                if batch:  # Only process non-empty batches
                    result = analyzer_manager.analyze_category_batch(batch, db)
                    batch_results.append({
                        'category': category,
                        'batch_size': len(batch),
                        'file_paths': batch,
                        'result': result
                    })
                    
                    total_files += result['total_files']
                    total_batches += 1
        
        return {
            "status": "success",
            "results": {
                "batch_results": batch_results,
                "total_files": total_files,
                "total_batches": total_batches,
                "message": "Batches created successfully. Metadata analysis will be handled separately."
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@router.get("/length-stats")
async def get_length_statistics(db: Session = Depends(get_db)):
    """Get length statistics"""
    try:
        stats = analyzer_manager.get_length_statistics(db)
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get length statistics: {str(e)}")

@router.get("/categories")
async def get_length_categories():
    """Get configured length categories"""
    try:
        categories = analyzer_manager.length_categories
        return {
            "status": "success",
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")
