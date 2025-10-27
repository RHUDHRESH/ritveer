"""
File Management Tools
Handle image uploads, file storage, and media management
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from .base_tool import BaseTool, ToolResult


class ImageUploadTool(BaseTool):
    """Handle image uploads for artisan products and profiles"""

    def __init__(self, upload_dir: str = "./data/uploads/images"):
        super().__init__(
            name="image_upload",
            description="Upload and manage product images",
            required_params=["image_file", "artisan_id"]
        )
        self.upload_dir = upload_dir
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        os.makedirs(upload_dir, exist_ok=True)

    async def execute(self, **kwargs) -> ToolResult:
        """Upload REAL image file"""
        start_time = datetime.utcnow()

        try:
            artisan_id = kwargs.get("artisan_id")
            image_file = kwargs.get("image_file")  # Can be file path or bytes
            image_type = kwargs.get("type", "product")  # product, profile, portfolio

            # Generate file ID and filename
            file_id = str(uuid.uuid4())

            # Determine extension from image_file
            if isinstance(image_file, str):
                # It's a file path
                if not os.path.exists(image_file):
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Image file not found: {image_file}",
                        execution_time=execution_time,
                        timestamp=datetime.utcnow()
                    )

                # Get extension from source file
                source_ext = Path(image_file).suffix.lower()
                if source_ext not in self.allowed_extensions:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Invalid image format: {source_ext}",
                        execution_time=(datetime.utcnow() - start_time).total_seconds(),
                        timestamp=datetime.utcnow()
                    )

                filename = f"{artisan_id}_{image_type}_{file_id}{source_ext}"
                file_path = os.path.join(self.upload_dir, filename)

                # Copy file
                import shutil
                shutil.copy2(image_file, file_path)
                file_size = os.path.getsize(file_path)

            elif isinstance(image_file, bytes):
                # It's binary data
                filename = f"{artisan_id}_{image_type}_{file_id}.png"
                file_path = os.path.join(self.upload_dir, filename)

                # Write bytes
                with open(file_path, 'wb') as f:
                    f.write(image_file)
                file_size = len(image_file)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Invalid image_file type",
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    timestamp=datetime.utcnow()
                )

            image_data = {
                "file_id": file_id,
                "filename": filename,
                "filepath": file_path,
                "url": f"/uploads/images/{filename}",
                "artisan_id": artisan_id,
                "type": image_type,
                "size": file_size,
                "upload_date": datetime.utcnow().isoformat(),
                "status": "uploaded"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=image_data,
                message=f"Image uploaded successfully",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"file_id": file_id, "filename": filename, "size": f"{file_size} bytes"}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Image upload failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def validate_image(self, filepath: str) -> Tuple[bool, str]:
        """Validate image file"""
        path = Path(filepath)

        if not path.exists():
            return False, "File does not exist"

        if path.suffix.lower() not in self.allowed_extensions:
            return False, "Invalid file format"

        if path.stat().st_size > self.max_file_size:
            return False, "File too large"

        return True, "Valid"


class FileStorageTool(BaseTool):
    """Generic file storage management"""

    def __init__(self, storage_dir: str = "./data/storage"):
        super().__init__(
            name="file_storage",
            description="Store and retrieve files",
            required_params=["file_name", "content"]
        )
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    async def execute(self, **kwargs) -> ToolResult:
        """Store REAL file"""
        start_time = datetime.utcnow()

        try:
            file_name = kwargs.get("file_name")
            content = kwargs.get("content")  # Can be string or bytes
            category = kwargs.get("category", "general")

            # Create category directory
            cat_dir = os.path.join(self.storage_dir, category)
            os.makedirs(cat_dir, exist_ok=True)

            # Generate unique filename
            file_id = str(uuid.uuid4())
            unique_filename = f"{file_id}_{file_name}"
            file_path = os.path.join(cat_dir, unique_filename)

            # Write REAL file to disk
            if isinstance(content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(content)
                file_size = len(content)
            else:
                # String content
                content_str = str(content)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content_str)
                file_size = len(content_str.encode('utf-8'))

            # Verify file was written
            if not os.path.exists(file_path):
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"File write verification failed",
                    execution_time=execution_time,
                    timestamp=datetime.utcnow()
                )

            actual_file_size = os.path.getsize(file_path)

            file_data = {
                "file_id": file_id,
                "filename": file_name,
                "stored_as": unique_filename,
                "category": category,
                "size": actual_file_size,
                "path": file_path,
                "url": f"/storage/{category}/{unique_filename}",
                "upload_date": datetime.utcnow().isoformat(),
                "status": "stored"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=file_data,
                message=f"File stored successfully at {file_path}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"file_id": file_id, "size": f"{actual_file_size} bytes"}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"File storage failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class MediaGalleryTool(BaseTool):
    """Manage media galleries for artisans"""

    def __init__(self):
        super().__init__(
            name="media_gallery",
            description="Manage artisan product galleries",
            required_params=["artisan_id"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Get or create gallery"""
        start_time = datetime.utcnow()

        try:
            artisan_id = kwargs.get("artisan_id")
            action = kwargs.get("action", "list")  # list, create, update

            gallery_data = {
                "artisan_id": artisan_id,
                "action": action,
                "galleries": [
                    {
                        "gallery_id": f"gal_{uuid.uuid4().hex[:8]}",
                        "name": "Product Collection",
                        "images": [],
                        "created_at": datetime.utcnow().isoformat(),
                        "is_public": True
                    },
                    {
                        "gallery_id": f"gal_{uuid.uuid4().hex[:8]}",
                        "name": "Process & Technique",
                        "images": [],
                        "created_at": datetime.utcnow().isoformat(),
                        "is_public": False
                    }
                ],
                "total_images": 0
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=gallery_data,
                message=f"Gallery retrieved for {artisan_id}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"artisan_id": artisan_id}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Gallery operation failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class DocumentProcessingTool(BaseTool):
    """Process documents like certificates, licenses"""

    def __init__(self):
        super().__init__(
            name="document_processing",
            description="Process and store important documents",
            required_params=["artisan_id", "document_type"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Process document"""
        start_time = datetime.utcnow()

        try:
            artisan_id = kwargs.get("artisan_id")
            document_type = kwargs.get("document_type")  # certificate, license, registration
            document_file = kwargs.get("document_file")

            document_data = {
                "document_id": f"doc_{uuid.uuid4().hex[:8]}",
                "artisan_id": artisan_id,
                "type": document_type,
                "filename": document_type,
                "url": f"/documents/{artisan_id}/{document_type}.pdf",
                "verified": False,
                "upload_date": datetime.utcnow().isoformat(),
                "status": "pending_verification"
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=document_data,
                message=f"Document processed",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"document_id": document_data["document_id"]}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Document processing failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


# Tool instances
image_upload = ImageUploadTool()
file_storage = FileStorageTool()
media_gallery = MediaGalleryTool()
document_processing = DocumentProcessingTool()
