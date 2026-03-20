"""
وظيفة تجزئة النصوص - نسخة مبسطة بدون tiktoken
"""

from typing import List, Dict, Any
from loguru import logger
import re

class TextChunker:
    """تقسيم النصوص إلى أجزاء (Chunks) - نسخة مبسطة"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.chunk_size = 500  # عدد الأحرف التقريبي
        self.chunk_overlap = 50

    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        تجزئة مستند إلى أجزاء
        """
        text = document['text']
        metadata = document['metadata']

        # تجزئة بسيطة حسب الفقرات
        chunks = self._simple_chunking(text)

        # إضافة البيانات الوصفية لكل جزء
        chunked_docs = []
        for i, chunk_text in enumerate(chunks):
            if not chunk_text.strip():
                continue

            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_id': i,
                'chunk_count': len(chunks)
            })

            chunked_docs.append({
                'text': chunk_text.strip(),
                'metadata': chunk_metadata
            })

        return chunked_docs

    def _simple_chunking(self, text: str) -> List[str]:
        """
        تجزئة بسيطة تعتمد على الفقرات وطول النص
        """
        # تقسيم حسب الفقرات (سطرين فارغين)
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if not para.strip():
                continue

            # إذا كانت الفقرة طويلة، قسمها لجمل
            if len(para) > self.chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= self.chunk_size:
                        if current_chunk:
                            current_chunk += " " + sentence
                        else:
                            current_chunk = sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
            else:
                # فقرة عادية
                if len(current_chunk) + len(para) <= self.chunk_size:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks