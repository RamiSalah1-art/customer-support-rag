"""
خط أنابيب معالجة المستندات - يربط بين التحميل والتقطيع والتضمين
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger
import json
from datetime import datetime

from .document_loader import DocumentLoader
from .chunking import TextChunker
from .embedding import EmbeddingGenerator

class IngestionPipeline:
    """يدير عملية معالجة المستندات بالكامل"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.loader = DocumentLoader(config)
        self.chunker = TextChunker(config)
        self.embedder = EmbeddingGenerator(config)
        self.vector_store_path = Path(config.get('vector_store', {}).get('path', 'data/vector_store'))
        self.index_file = self.vector_store_path / "index_info.json"
        self.hybrid_search = None  # للربط مع نظام البحث
        self.texts = []  # لتخزين النصوص للبحث النصي
        
    def set_hybrid_search(self, hybrid_search):
        """ربط hybrid_search مع pipeline"""
        self.hybrid_search = hybrid_search
        logger.info("✅ Hybrid search connected to pipeline")
    
    def get_texts(self):
        """إرجاع النصوص المعالجة (للبحث النصي)"""
        return self.texts
    
    def _load_index_info(self) -> Dict[str, Any]:
        """تحميل معلومات الفهرس الحالي"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"files": {}, "last_updated": None}
        return {"files": {}, "last_updated": None}
    
    def _save_index_info(self, info: Dict[str, Any]):
        """حفظ معلومات الفهرس"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        info["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    
    def _vector_store_exists(self) -> bool:
        """التحقق من وجود قاعدة المتجهات"""
        return (self.vector_store_path / "chroma.sqlite3").exists()
    
    def run(self, raw_data_path: str = "data/raw", force_rebuild: bool = False) -> bool:
        """
        تشغيل خط أنابيب المعالجة
        
        Args:
            raw_data_path: مسار المجلد الخام
            force_rebuild: إجبار إعادة بناء كل شيء
            
        Returns:
            bool: هل تمت المعالجة بنجاح
        """
        logger.info("🚀 بدء خط أنابيب معالجة المستندات...")
        
        # التحقق من وجود قاعدة المتجهات
        vector_store_exists = self._vector_store_exists()
        
        # تحديد ما إذا كنا بحاجة لإعادة بناء كامل
        if force_rebuild or not vector_store_exists:
            logger.warning("🔄 إعادة بناء كامل للفهرس...")
            documents = self.loader.load_all_documents(raw_data_path, force_reload=True)
        else:
            # تحميل الملفات الجديدة فقط
            documents = self.loader.load_all_documents(raw_data_path)
        
        if not documents:
            logger.info("📭 لا توجد مستندات جديدة للمعالجة")
            return True
        
        logger.info(f"✂️ تقطيع {len(documents)} مستند إلى أجزاء...")
        all_chunks = []
        for doc in documents:
            chunks = self.chunker.chunk_document(doc)
            all_chunks.extend(chunks)
            logger.info(f"   → {len(chunks)} جزء من {doc['metadata']['filename']}")
        
        logger.info(f"🧠 توليد {len(all_chunks)} تضمين...")
        texts = [chunk['text'] for chunk in all_chunks]
        self.texts = texts  # تخزين النصوص للاستخدام لاحقاً
        embeddings = self.embedder.generate_embeddings_batch(texts)
        
        # تجهيز البيانات للتخزين
        chunk_data = []
        for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
            chunk_data.append({
                'id': f"chunk_{i}",
                'text': chunk['text'],
                'embedding': embedding,
                'metadata': chunk['metadata']
            })
        
        # تخزين في قاعدة المتجهات إذا كان hybrid_search موجوداً
        if self.hybrid_search:
            try:
                # تمرير النصوص لـ hybrid_search لتهيئة BM25
                self.hybrid_search.set_documents(texts)
                logger.info(f"✅ BM25 initialized with {len(texts)} texts")
                
                # هنا سنضيف لاحقاً تخزين المتجهات في vector_store
                logger.info("💾 جاهز لتخزين المتجهات في قاعدة البيانات")
            except Exception as e:
                logger.error(f"❌ فشل تخزين المتجهات: {e}")
        
        logger.success(f"✅ اكتملت المعالجة: {len(documents)} ملفات, {len(all_chunks)} أجزاء")
        
        return True