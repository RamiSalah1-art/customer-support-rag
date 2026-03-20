"""
وحدة البحث المختلط - تجمع بين البحث الدلالي والنصي
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import chromadb
from loguru import logger

class HybridSearch:
    """نظام بحث مختلط (دلالي + نصي)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # إعدادات البحث المختلط
        hybrid_config = config.get('retrieval', {}).get('hybrid_search', {})
        self.enabled = hybrid_config.get('enabled', True)
        self.dense_weight = hybrid_config.get('dense_weight', 0.7)
        self.sparse_weight = hybrid_config.get('sparse_weight', 0.3)
        self.fusion_method = hybrid_config.get('fusion_method', 'rrf')
        
        # تهيئة النماذج
        self.dense_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # تهيئة قاعدة المتجهات (سيتم تمريرها من الخارج)
        self.vector_store = None
        self.documents = []  # قائمة النصوص للبحث النصي
        self.bm25 = None
    
    def set_vector_store(self, vector_store):
        """تعيين قاعدة المتجهات"""
        self.vector_store = vector_store
        logger.info("✅ Vector store set successfully")
    
    def set_documents(self, documents: List[str]):
        """
        تعيين المستندات للبحث النصي وتهيئة BM25
        
        Args:
            documents: قائمة النصوص
        """
        self.documents = documents
        if documents:
            tokenized_docs = [doc.split() for doc in documents]
            self.bm25 = BM25Okapi(tokenized_docs)
            logger.info(f"✅ BM25 initialized with {len(documents)} documents")
        else:
            logger.warning("⚠️ No documents provided for BM25")
    
    def initialize_bm25(self, documents: List[str]):
        """
        تهيئة BM25 مع المستندات (للتوافق مع الكود القديم)
        
        Args:
            documents: قائمة النصوص
        """
        self.set_documents(documents)
    
    def search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        بحث مختلط يجمع بين الدلالي والنصي
        
        Args:
            query: استعلام البحث
            k: عدد النتائج المطلوبة
            
        Returns:
            قائمة بالنتائج مرتبة
        """
        if not self.enabled:
            # استخدام البحث الدلالي فقط
            return self._dense_search(query, k)
        
        # الحصول على نتائج من كلا الطريقتين
        dense_results = self._dense_search(query, k*2)  # نطلب ضعف العدد للدمج
        sparse_results = self._sparse_search(query, k*2)
        
        # دمج النتائج
        if self.fusion_method == 'rrf':
            combined_results = self._reciprocal_rank_fusion(dense_results, sparse_results, k)
        else:
            combined_results = self._weighted_fusion(dense_results, sparse_results, k)
        
        return combined_results
    
    def _dense_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """بحث دلالي باستخدام المتجهات"""
        if not self.vector_store:
            logger.error("❌ Vector store not set - dense search unavailable")
            return []
        
        try:
            # توليد embedding للاستعلام
            query_vector = self.dense_model.encode(query).tolist()
            
            # بحث في قاعدة المتجهات
            results = self.vector_store.query(
                query_embeddings=[query_vector],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # تنسيق النتائج
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1.0 - results['distances'][0][i],  # تحويل المسافة إلى درجة
                    'method': 'dense'
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"❌ Dense search failed: {e}")
            return []
    
    def _sparse_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """بحث نصي باستخدام BM25"""
        if not self.bm25:
            logger.error("❌ BM25 not initialized - sparse search unavailable")
            return []
        
        try:
            # بحث BM25
            tokenized_query = query.split()
            scores = self.bm25.get_scores(tokenized_query)
            
            # ترتيب النتائج حسب الدرجة
            top_indices = np.argsort(scores)[::-1][:k]
            
            # تنسيق النتائج
            formatted_results = []
            for idx in top_indices:
                if scores[idx] > 0:  # فقط النتائج ذات الصلة
                    formatted_results.append({
                        'id': f"doc_{idx}",
                        'text': self.documents[idx],
                        'metadata': {},
                        'score': float(scores[idx]),
                        'method': 'sparse',
                        'index': int(idx)
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"❌ Sparse search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, dense_results: List, sparse_results: List, k: int, k_const: int = 60) -> List[Dict]:
        """
        دمج النتائج باستخدام Reciprocal Rank Fusion
        
        Args:
            dense_results: نتائج البحث الدلالي
            sparse_results: نتائج البحث النصي
            k: عدد النتائج النهائية
            k_const: ثابت RRF (عادة 60)
            
        Returns:
            نتائج مدمجة ومرتبة
        """
        if not dense_results and not sparse_results:
            return []
        
        # قاموس لتجميع الدرجات
        scores = {}
        
        # إضافة درجات RRF من النتائج الدلالية
        for rank, result in enumerate(dense_results):
            doc_id = result.get('id', result.get('text', ''))
            rrf_score = 1.0 / (k_const + rank + 1)
            if doc_id not in scores:
                scores[doc_id] = {'score': 0, 'result': result}
            scores[doc_id]['score'] += rrf_score
        
        # إضافة درجات RRF من النتائج النصية
        for rank, result in enumerate(sparse_results):
            doc_id = result.get('id', result.get('text', ''))
            rrf_score = 1.0 / (k_const + rank + 1)
            if doc_id not in scores:
                scores[doc_id] = {'score': 0, 'result': result}
            scores[doc_id]['score'] += rrf_score
        
        # ترتيب حسب الدرجة واختيار أفضل k
        sorted_items = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)[:k]
        
        # تنسيق النتائج النهائية
        final_results = []
        for doc_id, data in sorted_items:
            result = data['result'].copy()
            result['fusion_score'] = data['score']
            result['fusion_method'] = 'rrf'
            final_results.append(result)
        
        return final_results
    
    def _weighted_fusion(self, dense_results: List, sparse_results: List, k: int) -> List[Dict]:
        """
        دمج النتائج باستخدام الأوزان الخطية
        
        Args:
            dense_results: نتائج البحث الدلالي
            sparse_results: نتائج البحث النصي
            k: عدد النتائج النهائية
            
        Returns:
            نتائج مدمجة ومرتبة
        """
        if not dense_results and not sparse_results:
            return []
        
        # تطبيع الدرجات لكل قائمة
        dense_scores = self._normalize_scores(dense_results)
        sparse_scores = self._normalize_scores(sparse_results)
        
        # قاموس لتجميع الدرجات الموزونة
        combined = {}
        
        for result in dense_results:
            doc_id = result.get('id', result.get('text', ''))
            combined[doc_id] = {
                'result': result,
                'score': dense_scores.get(doc_id, 0) * self.dense_weight
            }
        
        for result in sparse_results:
            doc_id = result.get('id', result.get('text', ''))
            if doc_id in combined:
                combined[doc_id]['score'] += sparse_scores.get(doc_id, 0) * self.sparse_weight
            else:
                combined[doc_id] = {
                    'result': result,
                    'score': sparse_scores.get(doc_id, 0) * self.sparse_weight
                }
        
        # ترتيب واختيار أفضل k
        sorted_items = sorted(combined.items(), key=lambda x: x[1]['score'], reverse=True)[:k]
        
        final_results = []
        for doc_id, data in sorted_items:
            result = data['result'].copy()
            result['fusion_score'] = data['score']
            result['fusion_method'] = 'weighted'
            final_results.append(result)
        
        return final_results
    
    def _normalize_scores(self, results: List[Dict]) -> Dict[str, float]:
        """
        تطبيع الدرجات لتكون بين 0 و 1
        
        Args:
            results: قائمة النتائج
            
        Returns:
            قاموس بالدرجات الطبيعية
        """
        if not results:
            return {}
        
        scores = [r.get('score', 0) for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return {r.get('id', r.get('text', '')): 1.0 for r in results}
        
        normalized = {}
        for r in results:
            doc_id = r.get('id', r.get('text', ''))
            score = r.get('score', 0)
            normalized[doc_id] = (score - min_score) / (max_score - min_score)
        
        return normalized