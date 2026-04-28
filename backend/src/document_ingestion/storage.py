"""Document storage handler for local and cloud storage."""
import os
import shutil
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DocumentStorage:
    """Handler for storing original documents."""
    
    def __init__(self, base_path: str = "./documents"):
        self.base_path = base_path
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Create base directory if it doesn't exist."""
        os.makedirs(self.base_path, exist_ok=True)
    
    def store(self, file_path: str, company_id: str, document_id: str) -> str:
        """
        Store a document file.
        
        Args:
            file_path: Path to source file
            company_id: UUID of the company
            document_id: UUID of the document
        
        Returns:
            Path to stored file
        """
        # Create company-specific directory
        company_dir = os.path.join(self.base_path, company_id)
        os.makedirs(company_dir, exist_ok=True)
        
        # Get file extension
        file_ext = os.path.splitext(file_path)[1]
        
        # Create destination path
        dest_path = os.path.join(company_dir, f"{document_id}{file_ext}")
        
        # Copy file
        try:
            shutil.copy2(file_path, dest_path)
            logger.info(f"Stored document {document_id} at {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Error storing document {document_id}: {str(e)}")
            raise
    
    def retrieve(self, company_id: str, document_id: str) -> Optional[str]:
        """
        Retrieve path to stored document.
        
        Args:
            company_id: UUID of the company
            document_id: UUID of the document
        
        Returns:
            Path to document or None if not found
        """
        company_dir = os.path.join(self.base_path, company_id)
        
        # Try to find file with any extension
        for ext in ['.pdf', '.docx', '.txt']:
            file_path = os.path.join(company_dir, f"{document_id}{ext}")
            if os.path.exists(file_path):
                return file_path
        
        return None
    
    def delete(self, company_id: str, document_id: str) -> bool:
        """
        Delete a stored document.
        
        Args:
            company_id: UUID of the company
            document_id: UUID of the document
        
        Returns:
            True if deleted, False if not found
        """
        company_dir = os.path.join(self.base_path, company_id)
        
        for ext in ['.pdf', '.docx', '.txt']:
            file_path = os.path.join(company_dir, f"{document_id}{ext}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted document {document_id}")
                    return True
                except Exception as e:
                    logger.error(f"Error deleting document {document_id}: {str(e)}")
                    raise
        
        return False

