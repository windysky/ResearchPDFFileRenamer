import pdfplumber
import re
from typing import Tuple, Optional


class PDFService:
    """Service for extracting text from PDF files"""

    # Keywords that indicate we've reached the abstract section
    ABSTRACT_KEYWORDS = [
        'abstract', 'summary', 'introduction', 'keywords',
        '1.', '1 ', 'i.', 'i '
    ]

    @staticmethod
    def extract_text(pdf_path: str, max_pages: int = 2) -> str:
        """
        Extract text from PDF, focusing on first pages up to abstract.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to extract (default 2)

        Returns:
            Extracted text content
        """
        text_parts = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_extract = min(max_pages, total_pages)

                for i in range(pages_to_extract):
                    page = pdf.pages[i]
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)

                    # Check if we've found the abstract on first page
                    if i == 0 and PDFService._has_abstract(page_text):
                        # First page has abstract, might be enough
                        # But still get page 2 for safety
                        pass

        except Exception as e:
            raise PDFExtractionError(f"Failed to extract text from PDF: {str(e)}")

        full_text = "\n\n".join(text_parts)

        # Clean up the text
        full_text = PDFService._clean_text(full_text)

        # Truncate to abstract section if possible
        truncated = PDFService._truncate_after_abstract(full_text)

        return truncated

    @staticmethod
    def _has_abstract(text: str) -> bool:
        """Check if text contains abstract section"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ['abstract', 'summary'])

    @staticmethod
    def _truncate_after_abstract(text: str) -> str:
        """
        Truncate text after the abstract section to reduce LLM token usage.
        Looks for 'Introduction' or numbered sections after abstract.
        """
        text_lower = text.lower()

        # Find abstract position
        abstract_pos = -1
        for keyword in ['abstract', 'summary']:
            pos = text_lower.find(keyword)
            if pos != -1:
                abstract_pos = pos
                break

        if abstract_pos == -1:
            # No abstract found, return full text (limited)
            return text[:8000]  # Limit to ~2000 tokens

        # Find where abstract ends (usually at Introduction or section 1)
        end_markers = [
            '\nintroduction', '\n1.', '\n1 ', '\ni.',
            '\nkeywords', '\nkey words', '\n2.'
        ]

        end_pos = len(text)
        for marker in end_markers:
            pos = text_lower.find(marker, abstract_pos + 50)  # Start after abstract header
            if pos != -1 and pos < end_pos:
                # Include a bit after the marker for context
                end_pos = pos + 500

        # Return text up to the end position, but at least include abstract
        result = text[:min(end_pos, len(text))]

        # Ensure we don't cut off mid-sentence
        last_period = result.rfind('.')
        if last_period > len(result) - 100:
            result = result[:last_period + 1]

        return result[:8000]  # Final safety limit

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers and headers/footers patterns
        text = re.sub(r'\n\d+\n', '\n', text)
        # Restore paragraph breaks
        text = re.sub(r'\.(\s+)([A-Z])', r'.\n\n\2', text)
        return text.strip()

    @staticmethod
    def validate_pdf(pdf_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file is a valid PDF.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    return False, "File is not a valid PDF (invalid header)"

            # Try to open with pdfplumber to verify it's readable
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return False, "PDF has no pages"

            return True, None

        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors"""
    pass
