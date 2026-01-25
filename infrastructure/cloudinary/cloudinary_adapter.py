import cloudinary
import cloudinary.uploader
from config.settings import settings
from shared.logger import get_logger

logger = get_logger(__name__, "CLOUDINARY")

class CloudinaryAdapter:
    def __init__(self):
        if settings.CLOUDINARY_CLOUD_NAME:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
            logger.info("Cloudinary configured")
        else:
            logger.warning("Cloudinary credentials missing")

    def upload(self, file_path: str, public_id: str = None) -> dict:
        """
        Upload file to Cloudinary.
        Returns the upload result dict.
        """
        try:
            # Determine resource type automatically (image, video, raw)
            # 'auto' works for most, but raw is needed for non-media files if we want them stored
            
            response = cloudinary.uploader.upload(
                file_path,
                public_id=public_id,
                resource_type="auto",
                folder=settings.CLOUDINARY_FOLDER
            )
            return response
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise e

cloudinary_adapter = CloudinaryAdapter()
