
import os
import shutil
from fastapi import UploadFile
from config.settings import settings

class LocalStorageAdapter:
    def upload(self, source_path: str, filename: str) -> dict:
        """
        Upload file to local storage.
        source_path: path to temporary file
        filename: original filename
        """
        # Ensure upload directory exists
        upload_dir = os.path.join(os.getcwd(), settings.UPLOAD_DIR)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate valid filename (basic sanitization could be added)
        # For simplicity, we use unique name if needed or overwrite?
        # Cloudinary uses public_id. Here we might want timestamp or uuid prefix.
        import uuid
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        destination_path = os.path.join(upload_dir, unique_filename)
        
        # Move file
        shutil.copy2(source_path, destination_path)
        
        # Generate URL
        # Assuming static mount at /static/uploads
        relative_path = f"/{settings.UPLOAD_DIR}/{unique_filename}".replace("\\", "/")
        full_url = f"{settings.BASE_URL}{relative_path}"
        
        return {
            "secure_url": full_url,
            "public_id": unique_filename,
            "bytes": os.path.getsize(destination_path),
            "format": ext.lstrip('.'),
            "resource_type": "raw" # Generic
        }

local_storage_adapter = LocalStorageAdapter()
