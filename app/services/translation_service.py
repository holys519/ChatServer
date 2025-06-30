"""
Translation Service for Japanese-English bidirectional translation
Handles automatic language detection and translation for research queries
"""

import re
from typing import Optional, Dict, Any
from langchain_core.messages import HumanMessage
from app.services.gemini_service import gemini_service


class TranslationService:
    """Service for handling Japanese-English translations using Gemini"""
    
    def __init__(self):
        self.gemini_service = gemini_service
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text is primarily Japanese or English
        Returns: 'ja' for Japanese, 'en' for English
        """
        # Count Japanese characters (hiragana, katakana, kanji)
        japanese_chars = len(re.findall(r'[ひ-ゖヒ-ヾ一-龯]', text))
        total_chars = len(re.sub(r'\s', '', text))
        
        if total_chars == 0:
            return 'en'
        
        japanese_ratio = japanese_chars / total_chars
        
        # If more than 30% Japanese characters, consider it Japanese
        return 'ja' if japanese_ratio > 0.3 else 'en'
    
    async def translate_to_english(self, japanese_text: str) -> str:
        """
        Translate Japanese text to English for academic/medical search
        Optimized for research and medical terminology
        """
        try:
            prompt = f"""
Translate the following Japanese text to English for academic/medical research purposes.

Requirements:
- Use precise medical and scientific terminology
- Maintain technical accuracy
- Optimize for academic database searches (PubMed, etc.)
- Use standard English academic phrases
- Do not add explanations, just provide the translation

Japanese text: "{japanese_text}"

English translation:"""

            messages = [HumanMessage(content=prompt)]
            response = await self.gemini_service.send_message(
                model_name="gemini-2.0-flash-001",
                history=[],
                message=prompt
            )
            
            # Clean the response to get just the translation
            translation = response.strip().strip('"').strip("'")
            
            # Remove any prefixes like "English translation:" if present
            if ":" in translation:
                parts = translation.split(":", 1)
                if len(parts) == 2 and len(parts[0]) < 30:
                    translation = parts[1].strip()
            
            return translation if translation else japanese_text
            
        except Exception as e:
            print(f"❌ Translation to English failed: {str(e)}")
            return japanese_text
    
    async def translate_text(self, text: str, source_lang: str = "ja", target_lang: str = "en") -> str:
        """
        Deprecated alias for translate_to_english() / translate_to_japanese()
        This method exists for backward compatibility only.
        Please use translate_to_english() or translate_to_japanese() instead.
        """
        print("⚠️ Warning: translate_text() is deprecated. Use translate_to_english() or translate_to_japanese() instead.")
        
        if source_lang == "ja" and target_lang == "en":
            return await self.translate_to_english(text)
        elif source_lang == "en" and target_lang == "ja":
            return await self.translate_to_japanese(text)
        else:
            # Default behavior for unsupported language pairs
            return text
    
    async def translate_to_japanese(self, english_text: str) -> str:
        """
        Translate English text to natural Japanese
        Optimized for academic and medical content
        """
        try:
            prompt = f"""
Translate the following English text to natural Japanese.

Requirements:
- Use appropriate Japanese medical/scientific terminology
- Maintain academic tone and accuracy
- Use natural Japanese expression
- Preserve technical meaning
- Do not add explanations, just provide the translation

English text: "{english_text}"

Japanese translation:"""

            messages = [HumanMessage(content=prompt)]
            response = await self.gemini_service.send_message(
                model_name="gemini-2.0-flash-001",
                history=[],
                message=prompt
            )
            
            # Clean the response to get just the translation
            translation = response.strip().strip('"').strip("'")
            
            # Remove any prefixes if present
            if ":" in translation:
                parts = translation.split(":", 1)
                if len(parts) == 2 and len(parts[0]) < 30:
                    translation = parts[1].strip()
            
            return translation if translation else english_text
            
        except Exception as e:
            print(f"❌ Translation to Japanese failed: {str(e)}")
            return english_text
    
    async def translate_search_query(self, query: str) -> Dict[str, str]:
        """
        Translate search query if needed and return both original and translated versions
        
        Returns:
            Dict with 'original', 'translated', 'original_language', 'search_language'
        """
        original_language = self.detect_language(query)
        
        if original_language == 'ja':
            # Japanese input -> translate to English for search
            translated_query = await self.translate_to_english(query)
            return {
                'original': query,
                'translated': translated_query,
                'original_language': 'ja',
                'search_language': 'en'
            }
        else:
            # English input -> use as-is
            return {
                'original': query,
                'translated': query,
                'original_language': 'en',
                'search_language': 'en'
            }
    
    async def translate_results(self, english_content: str, target_language: str = 'ja') -> str:
        """
        Translate research results back to the user's preferred language
        
        Args:
            english_content: The content in English (typically from research papers)
            target_language: Target language ('ja' for Japanese, 'en' for English)
        
        Returns:
            Translated content
        """
        if target_language == 'en':
            return english_content
        
        # Translate to Japanese
        return await self.translate_to_japanese(english_content)
    
    async def create_bilingual_summary(self, original_query: str, english_results: str) -> str:
        """
        Create a bilingual summary that shows both languages when appropriate
        """
        original_language = self.detect_language(original_query)
        
        if original_language == 'ja':
            # Translate results to Japanese
            japanese_results = await self.translate_to_japanese(english_results)
            
            # Create bilingual format
            return f"""# 検索結果 / Search Results

**元の検索クエリ**: {original_query}
**English Search Query**: {await self.translate_to_english(original_query)}

---

{japanese_results}

---

<details>
<summary>Original English Results</summary>

{english_results}

</details>"""
        else:
            # Original was English, return as-is
            return english_results


# Singleton instance
translation_service = TranslationService()