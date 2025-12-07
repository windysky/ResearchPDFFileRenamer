from abc import ABC, abstractmethod
from typing import Dict, Optional
import json
import re
from openai import OpenAI


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def extract_metadata(self, text: str) -> Dict[str, str]:
        """
        Extract paper metadata from text.

        Returns:
            Dict with keys: author, year, title
        """
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    EXTRACTION_PROMPT = """You are a research paper metadata extractor. Given the text from a research paper, extract:

1. First author's last name (just the surname, e.g., "Smith", "Zhang", "García")
2. Publication year (4 digits, e.g., "2023")
3. Short title (3-5 key words from the title, no special characters, use underscores between words)

If any field cannot be determined, use "Unknown" for that field.

Return ONLY a JSON object in this exact format, no other text:
{"author": "LastName", "year": "YYYY", "title": "Short_Title_Here"}

Paper text:
"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract metadata using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract metadata from research papers and return JSON only."
                    },
                    {
                        "role": "user",
                        "content": self.EXTRACTION_PROMPT + text[:6000]  # Limit input
                    }
                ],
                temperature=0.1,
                max_tokens=150
            )

            response_text = response.choices[0].message.content.strip()
            return self._parse_response(response_text)

        except Exception as e:
            raise LLMError(f"OpenAI API error: {str(e)}")

    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response to extract JSON"""
        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    'author': self._sanitize(data.get('author', 'Unknown')),
                    'year': self._sanitize_year(data.get('year', 'Unknown')),
                    'title': self._sanitize(data.get('title', 'Unknown'))
                }
            except json.JSONDecodeError:
                pass

        # Fallback if parsing fails
        return {
            'author': 'Unknown',
            'year': 'Unknown',
            'title': 'Research_Paper'
        }

    def _sanitize(self, value: str) -> str:
        """Sanitize a string for use in filename"""
        if not value or value.lower() == 'unknown':
            return 'Unknown'
        # Remove special characters, keep alphanumeric and underscores
        sanitized = re.sub(r'[^\w\s-]', '', str(value))
        sanitized = re.sub(r'[\s-]+', '_', sanitized)
        return sanitized[:50]  # Limit length

    def _sanitize_year(self, value: str) -> str:
        """Sanitize year value"""
        # Extract 4-digit year
        year_match = re.search(r'(19|20)\d{2}', str(value))
        if year_match:
            return year_match.group()
        return 'Unknown'


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider (for future use)"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model

    def extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract metadata using local Ollama"""
        # TODO: Implement Ollama API call
        # This is a placeholder for future local LLM support
        raise NotImplementedError("Ollama provider not yet implemented")


class LLMService:
    """Factory and facade for LLM providers"""

    def __init__(self, provider: str, api_key: Optional[str] = None,
                 model: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize LLM service with specified provider.

        Args:
            provider: 'openai' or 'ollama'
            api_key: API key for OpenAI
            model: Model name
            base_url: Base URL for local LLM (Ollama)
        """
        if provider == 'openai':
            if not api_key:
                raise ValueError("API key required for OpenAI provider")
            self._provider = OpenAIProvider(api_key, model or "gpt-4o-mini")
        elif provider == 'ollama':
            self._provider = OllamaProvider(base_url or "http://localhost:11434",
                                            model or "llama3.2")
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract metadata from paper text"""
        return self._provider.extract_metadata(text)

    def generate_filename(self, text: str) -> str:
        """
        Generate a filename from paper text.

        Returns:
            Filename in format: AuthorLastName_Year_ShortTitle.pdf
        """
        metadata = self.extract_metadata(text)
        filename = f"{metadata['author']}_{metadata['year']}_{metadata['title']}.pdf"
        return filename


class LLMError(Exception):
    """Custom exception for LLM errors"""
    pass
