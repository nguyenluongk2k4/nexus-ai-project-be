from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modules.upload.services.upload_service import upload_service
from app.modules.upload.models.upload_response import UploadResponse
from shared.logger import get_logger

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

logger = get_logger(__name__, "UPLOAD_ROUTE")

@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to Gemini.
    Accepts all document formats supported by Gemini (PDF, Images, Audio, Video, Code, Text).
    """
    logger.info(f"Received upload request: {file.filename} ({file.content_type})")
    
    try:
        response = await upload_service.upload_file(file)
        return response
    except Exception as e:
        logger.error(f"Error in upload route: {e}")
        raise HTTPException(status_code=500, detail=str(e))
