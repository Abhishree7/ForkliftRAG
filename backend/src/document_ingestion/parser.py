"""Document parser for extracting text and metadata from various formats."""
import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from llama_parse import LlamaParse
from docx import Document as DocxDocument
import logging

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parser for PDF, DOCX, and TXT documents using LlamaParse for PDFs."""
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 20MB
    
    def __init__(self, llama_parse_api_key: Optional[str] = None):
        """
        Initialize document parser.
        
        Args:
            llama_parse_api_key: LlamaParse API key (if None, reads from LLAMA_PARSE_API_KEY env var)
        
        Raises:
            ValueError: If LlamaParse API key is not provided
        """
        self.supported_formats = ['pdf', 'docx', 'txt']
        self.llama_parse_api_key = llama_parse_api_key or os.getenv("LLAMA_PARSE_API_KEY")
        
        if not self.llama_parse_api_key:
            raise ValueError(
                "LlamaParse API key is required for PDF parsing. "
                "Please provide it via LLAMA_PARSE_API_KEY environment variable or llama_parse_api_key parameter."
            )
        
        try:
            self.llama_parser = LlamaParse(
                api_key=self.llama_parse_api_key,
                result_type="markdown",  # Get structured markdown output
                verbose=True
            )
            logger.info("LlamaParse initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LlamaParse: {str(e)}")
            raise ValueError(f"Failed to initialize LlamaParse: {str(e)}")
    
    def parse(self, file_path: str, company_id: str, document_type: str = 'manual') -> Dict:
        """
        Parse a document and extract text with metadata.
        
        Args:
            file_path: Path to the document file
            company_id: UUID of the company
            document_type: Type of document (manual, sop, safety_guideline, shipping_protocol)
        
        Returns:
            Dictionary with document_id, chunks, and metadata
        """
        # Validate file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File size {file_size} exceeds maximum {self.MAX_FILE_SIZE} bytes")
        
        file_ext = os.path.splitext(file_path)[1][1:].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        document_name = os.path.basename(file_path)
        
        # Parse based on file type
        if file_ext == 'pdf':
            chunks = self._parse_pdf(file_path)
        elif file_ext == 'docx':
            chunks = self._parse_docx(file_path)
        else:  # txt
            chunks = self._parse_txt(file_path)
        
        # Add metadata to each chunk
        for chunk in chunks:
            chunk['document_id'] = document_id
            chunk['company_id'] = company_id
            chunk['document_name'] = document_name
            chunk['document_type'] = document_type
            chunk['upload_timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        return {
            'document_id': document_id,
            'document_name': document_name,
            'company_id': company_id,
            'document_type': document_type,
            'chunks': chunks,
            'total_chunks': len(chunks)
        }
    
    def _parse_pdf(self, file_path: str) -> List[Dict]:
        """Parse PDF file using LlamaParse."""
        if not self.llama_parser:
            raise ValueError(
                "LlamaParse is required for PDF parsing. "
                "Please provide LLAMA_PARSE_API_KEY environment variable or llama_parse_api_key parameter."
            )
        
        chunks = []
        
        try:
            logger.info(f"Parsing PDF with LlamaParse: {file_path}")
            documents = self.llama_parser.load_data(file_path)
            
            # Process LlamaParse results
            # LlamaParse returns a list of Document objects
            page_num = 1
            for doc in documents:
                # Get text content
                text = doc.text if hasattr(doc, 'text') else str(doc)
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                
                # Extract page number from metadata if available
                if metadata:
                    # Try different possible metadata keys for page number
                    for key in ['page_label', 'page_number', 'page']:
                        if key in metadata:
                            try:
                                page_num = int(metadata[key])
                                break
                            except (ValueError, TypeError):
                                pass
                
                if text and text.strip():
                    # Extract section title from markdown headers or text
                    section_title = self._extract_section_title_from_markdown(text)
                    if not section_title:
                        section_title = self._extract_section_title(text)
                    
                    chunks.append({
                        'page_number': page_num,
                        'chunk_text': text.strip(),
                        'section_title': section_title
                    })
                    page_num += 1
            
            logger.info(f"LlamaParse extracted {len(chunks)} chunks from PDF")
            return chunks
        except Exception as e:
            logger.error(f"Error parsing PDF with LlamaParse {file_path}: {str(e)}")
            raise
    
    def _extract_section_title_from_markdown(self, text: str) -> str:
        """Extract section title from markdown text (looks for headers)."""
        lines = text.split('\n')
        for line in lines[:10]:  # Check first 10 lines for headers
            line = line.strip()
            # Check for markdown headers (# Header, ## Header, etc.)
            if line.startswith('#'):
                # Remove # symbols and return the title
                title = line.lstrip('#').strip()
                if title:
                    return title
        return ""
    
    def _parse_docx(self, file_path: str) -> List[Dict]:
        """Parse DOCX file."""
        chunks = []
        try:
            doc = DocxDocument(file_path)
            current_section = "Introduction"
            current_text = []
            page_num = 1
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Check if this is a heading (section title)
                if para.style.name.startswith('Heading'):
                    # Save previous section if exists
                    if current_text:
                        chunks.append({
                            'page_number': page_num,
                            'chunk_text': '\n'.join(current_text),
                            'section_title': current_section
                        })
                        current_text = []
                    
                    current_section = text
                    page_num += 1  # Approximate page breaks
                else:
                    current_text.append(text)
            
            # Add last section
            if current_text:
                chunks.append({
                    'page_number': page_num,
                    'chunk_text': '\n'.join(current_text),
                    'section_title': current_section
                })
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {str(e)}")
            raise
        
        return chunks
    
    def _parse_txt(self, file_path: str) -> List[Dict]:
        """Parse TXT file."""
        chunks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by double newlines (common section separator)
            sections = content.split('\n\n')
            page_num = 1
            
            for section in sections:
                if section.strip():
                    section_title = self._extract_section_title(section)
                    chunks.append({
                        'page_number': page_num,
                        'chunk_text': section.strip(),
                        'section_title': section_title
                    })
                    page_num += 1
        except Exception as e:
            logger.error(f"Error parsing TXT {file_path}: {str(e)}")
            raise
        
        return chunks
    
    def _extract_section_title(self, text: str) -> str:
        """Extract section title from text (first line or heading)."""
        lines = text.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line and len(line) < 100:  # Likely a title
                # Check if it looks like a heading
                if line.isupper() or line.endswith(':') or len(line.split()) < 10:
                    return line
        return "Section"  # Default title

