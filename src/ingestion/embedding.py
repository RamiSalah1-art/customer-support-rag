"""
وحدة إنشاء الـ Embeddings - تحويل النصوص إلى متجهات رقمية
"""

from typing import List, Dict, Any, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
from loguru import logger
import os
import time

class EmbeddingGenerator:
    """توليد الـ Embeddings للنصوص"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # إعدادات النموذج
        model_config = config.get('models', {}).get('embedding', {})
        self.primary_model = model_config.get('primary', 'text-embedding-3-small')
        self.backup_model = model_config.get('backup', 'sentence-transformers/all-MiniLM-L6-v2')
        self.dimensions = model_config.get('dimensions', 1536)
        
        # تهيئة النماذج
        self.client = None
        self.local_model = None
        
        # استخدام النموذج المحلي (مجاني)
        self._setup_local_model()
    
    def _setup_local_model(self):
        """تهيئة النموذج المحلي كبديل مجاني"""
        try:
            logger.info(f"تحميل النموذج المحلي: {self.backup_model}")
            self.local_model = SentenceTransformer(self.backup_model)
            logger.info("✅ تم تحميل النموذج المحلي بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل تحميل النموذج المحلي: {e}")
            self.local_model = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        توليد embedding لنص واحد (مجاني)
        
        Args:
            text: النص المراد تحويله
            
        Returns:
            قائمة الأرقام (المتجه)
        """
        if not self.local_model:
            raise Exception("النموذج المحلي غير متاح")
        
        return self._generate_local_embedding(text)
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        توليد embeddings لعدة نصوص (دفعة واحدة)
        
        Args:
            texts: قائمة النصوص
            batch_size: حجم الدفعة الواحدة
            
        Returns:
            قائمة المتجهات
        """
        if not self.local_model:
            raise Exception("النموذج المحلي غير متاح")
        
        return self._generate_local_embeddings_batch(texts)
    
    def _generate_local_embedding(self, text: str) -> List[float]:
        """توليد embedding باستخدام النموذج المحلي"""
        embedding = self.local_model.encode(text)
        return embedding.tolist()
    
    def _generate_local_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """توليد embeddings دفعة واحدة باستخدام النموذج المحلي"""
        embeddings = self.local_model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        حساب التشابه بين متجهين (باستخدام cosine similarity)
        
        Args:
            embedding1: المتجه الأول
            embedding2: المتجه الثاني
            
        Returns:
            درجة التشابه بين 0 و 1
        """
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return dot_product / (norm_a * norm_b)