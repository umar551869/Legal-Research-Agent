from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from app.models import DocumentUploadResponse, AdminStatsResponse
from app.dependencies import get_current_admin, UserProfile
from app.services.global_kb import global_kb

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/ingest", response_model=DocumentUploadResponse)
async def ingest_document(
    http_request: Request,
    file: UploadFile = File(...),
    admin: UserProfile = Depends(get_current_admin)
):
    """Upload a document to the knowledge base.
    
    NOTE: Ingestion is currently disabled (read-only mode).
    The Pinecone index is pre-populated via offline scripts.
    """
    limiter = http_request.app.state.limiter
    
    @limiter.limit("5/minute")
    async def limited_ingest(request: Request):
        try:
            content = await file.read()
            text = content.decode("utf-8", errors="ignore")
            
            result = await global_kb.ingest_document(file.filename, text)
            
            if result["status"] == "disabled":
                raise HTTPException(status_code=503, detail=result["reason"])
            if result["status"] == "failed":
                raise HTTPException(status_code=400, detail=result["reason"])
                
            return DocumentUploadResponse(
                filename=result["filename"],
                status="success",
                chunks_processed=result["chunks"]
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    return await limited_ingest(request=http_request)

@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(admin: UserProfile = Depends(get_current_admin)):
    """Return knowledge base statistics."""
    raw_stats = global_kb.get_stats()
    return AdminStatsResponse(
        total_vectors=raw_stats.get("total_vectors", 0),
        ingestion_enabled=True,
    )
