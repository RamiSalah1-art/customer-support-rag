"""
وحدة إعادة الترتيب (Reranking) باستخدام Cross-encoder
"""

from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
import numpy as np
from loguru import logger

class Reranker:
    """نظام إعادة ترتيب النتائج باستخدام Cross-encoder"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # إعدادات إعادة الترتيب
        rerank_config = config.get('retrieval', {}).get('reranking', {})
        self.enabled = rerank_config.get('enabled', True)
        self.top_k_rerank = rerank_config.get('top_k_rerank', 20)
        self.final_k = rerank_config.get('final_k', 5)
        
        # تهيئة النموذج
        model_name = rerank_config.get('model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        try:
            self.model = CrossEncoder(model_name)
            logger.info(f"✅ Reranker model {model_name} loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load reranker model: {e}")
            self.enabled = False
    
    def rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        إعادة ترتيب النتائج باستخدام Cross-encoder
        
        Args:
            query: الاستعلام الأصلي
            results: قائمة النتائج المراد إعادة ترتيبها
            
        Returns:
            قائمة النتائج بعد إعادة الترتيب
        """
        if not self.enabled or len(results) == 0:
            return results[:self.final_k]
        
        # اختيار أفضل النتائج لإعادة الترتيب
        candidates = results[:min(self.top_k_rerank, len(results))]
        
        # تحضير أزواج (استعلام، مستند) للتقييم
        pairs = [[query, r.get('text', '')] for r in candidates]
        
        # الحصول على درجات Cross-encoder
        try:
            scores = self.model.predict(pairs)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results[:self.final_k]
        
        # إضافة الدرجات الجديدة
        for i, score in enumerate(scores):
            candidates[i]['rerank_score'] = float(score)
        
        # إعادة الترتيب حسب الدرجات الجديدة
        reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        logger.info(f"Reranked {len(reranked)} results, top score: {reranked[0]['rerank_score']:.4f}")
        
        return reranked[:self.final_k]
    
    def rerank_with_explanations(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        إعادة ترتيب النتائج مع شرح موجز لكل نتيجة
        
        Args:
            query: الاستعلام الأصلي
            results: قائمة النتائج
            
        Returns:
            نتائج مع درجة وتفسير مبسط
        """
        if not self.enabled:
            return results
        
        # إعادة الترتيب أولاً
        reranked = self.rerank(query, results)
        
        # إضافة شرح مبسط (يمكن توسيعه لاحقاً)
        for result in reranked:
            score = result.get('rerank_score', 0)
            if score > 0.8:
                result['relevance_explanation'] = "highly relevant"
            elif score > 0.5:
                result['relevance_explanation'] = "moderately relevant"
            else:
                result['relevance_explanation'] = "somewhat relevant"
        
        return reranked