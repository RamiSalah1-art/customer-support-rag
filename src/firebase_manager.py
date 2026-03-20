"""
إدارة الاتصال مع Firebase لمشروع RAG
"""

import firebase_admin
from firebase_admin import credentials, firestore, storage
from pathlib import Path
import os
from datetime import datetime
import tempfile

class FirebaseManager:
    """إدارة جميع عمليات Firebase"""
    
    def __init__(self, cred_path=None):
        """تهيئة الاتصال بـ Firebase"""
        if cred_path is None:
            # ابحث عن ملف JSON تلقائياً
            files = list(Path('.').glob('*.json'))
            json_files = [f for f in files if 'firebase' in str(f).lower()]
            if json_files:
                cred_path = str(json_files[0])
            else:
                raise FileNotFoundError("❌ ملف مفتاح Firebase غير موجود")
        
        self.cred_path = cred_path
        self._initialize()
    
    def _initialize(self):
        """تهيئة Firebase"""
        if not firebase_admin._apps:
            cred = credentials.Certificate(self.cred_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'customer-support-rag-4924b.appspot.com'
            })
        self.db = firestore.client()
        self.bucket = storage.bucket()
        print("✅ Firebase initialized")
    
    def save_query(self, user_id, question, answer, sources=None):
        """حفظ سؤال وجواب في Firestore"""
        data = {
            'user_id': user_id,
            'question': question,
            'answer': answer,
            'timestamp': datetime.now(),
            'sources': sources or []
        }
        doc_ref = self.db.collection('queries').document()
        doc_ref.set(data)
        print(f"✅ Query saved: {doc_ref.id}")
        return doc_ref.id
    
    def get_user_queries(self, user_id, limit=50):
        """استرجاع استعلامات مستخدم معين"""
        queries = self.db.collection('queries')\
            .where('user_id', '==', user_id)\
            .order_by('timestamp', direction='DESCENDING')\
            .limit(limit)\
            .get()
        
        return [q.to_dict() for q in queries]
    
    def upload_file(self, user_id, file_path):
        """رفع ملف إلى Firebase Storage"""
        blob_name = f"users/{user_id}/{Path(file_path).name}"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        print(f"✅ File uploaded: {blob_name}")
        return blob_name
    
    def download_file(self, blob_name, local_path=None):
        """تحميل ملف من Firebase Storage"""
        if local_path is None:
            local_path = Path('data/raw') / Path(blob_name).name
        
        blob = self.bucket.blob(blob_name)
        blob.download_to_filename(str(local_path))
        print(f"✅ File downloaded: {local_path}")
        return local_path
    
    def list_user_files(self, user_id):
        """عرض ملفات مستخدم معين"""
        blobs = self.bucket.list_blobs(prefix=f"users/{user_id}/")
        return [blob.name for blob in blobs]

# مثال استخدام سريع
if __name__ == "__main__":
    fb = FirebaseManager()
    
    # حفظ استعلام تجريبي
    fb.save_query(
        user_id="test_user",
        question="ما هي طرق الدفع؟",
        answer="نقبل فيزا وماستركارد",
        sources=["faq.txt"]
    )
    
    # عرض الاستعلامات
    queries = fb.get_user_queries("test_user")
    print("📊 Recent queries:", len(queries))