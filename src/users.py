"""
إدارة المستخدمين وكلمات السر
"""

import hashlib
import hmac
from datetime import datetime
import json
from pathlib import Path

class UserManager:
    """إدارة المستخدمين والمصادقة"""
    
    def __init__(self):
        # قاعدة بيانات المستخدمين
        self.users = {
            "admin": {
                "password_hash": self._hash_password("admin123"),
                "plan": "admin",
                "expiry": None,  # لا ينتهي
                "quota": None,   # غير محدود
                "monthly_quota": None
            },
            "client1": {
                "password_hash": self._hash_password("client123"),
                "plan": "basic",
                "expiry": "2026-04-16",
                "quota": 1000,   # حد شهري
                "monthly_quota": 1000
            },
            "client2": {
                "password_hash": self._hash_password("pro12345"),
                "plan": "professional",
                "expiry": "2026-05-16",
                "quota": 10000,
                "monthly_quota": 10000
            },
            "ramicompany": {
                "password_hash": self._hash_password("rami2026"),
                "plan": "professional",
                "expiry": "2027-03-16",
                "quota": 10000,
                "monthly_quota": 10000
            }
        }
        
        # ملف تخزين استخدام الاستعلامات
        self.usage_file = Path("data/usage.json")
        self.usage = self._load_usage()
        self._check_monthly_reset()
    
    def _load_usage(self):
        """تحميل عداد الاستعلامات من ملف"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # التحقق من وجود المفتاح 'usage'
                    if isinstance(data, dict) and 'usage' in data:
                        return data['usage']
                    elif isinstance(data, dict):
                        return data
            except:
                pass
        return {}
    
    def _save_usage(self):
        """حفظ عداد الاستعلامات إلى ملف"""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(self.usage, f, ensure_ascii=False, indent=2)
    
    def _check_monthly_reset(self):
        """إعادة تعيين العداد شهرياً"""
        reset_file = Path("data/last_reset.txt")
        current_month = datetime.now().strftime("%Y-%m")
        
        if reset_file.exists():
            with open(reset_file, 'r') as f:
                last_reset = f.read().strip()
            if last_reset != current_month:
                self.usage = {}
                with open(reset_file, 'w') as f:
                    f.write(current_month)
        else:
            reset_file.parent.mkdir(parents=True, exist_ok=True)
            with open(reset_file, 'w') as f:
                f.write(current_month)
    
    def _hash_password(self, password: str) -> str:
        """تشفير كلمة السر"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, username: str, password: str) -> bool:
        """التحقق من صحة المستخدم وكلمة السر"""
        if username not in self.users:
            return False
        
        user = self.users[username]
        password_hash = self._hash_password(password)
        
        return hmac.compare_digest(user["password_hash"], password_hash)
    
    def get_user_plan(self, username: str) -> str:
        """الحصول على خطة المستخدم"""
        return self.users.get(username, {}).get("plan", "none")
    
    def is_expired(self, username: str) -> bool:
        """التحقق من انتهاء الاشتراك"""
        user = self.users.get(username)
        if not user or not user.get("expiry"):
            return False
        
        expiry = datetime.strptime(user["expiry"], "%Y-%m-%d")
        return datetime.now() > expiry
    
    def check_quota(self, username: str) -> tuple[bool, int, int]:
        """
        التحقق من الحد المسموح
        
        Returns:
            tuple: (مسموح, المستخدم, الحد الأقصى)
        """
        if username not in self.users:
            return False, 0, 0
        
        user = self.users[username]
        
        # المشرف أو الخطط غير المحدودة
        if user.get("quota") is None:
            return True, 0, 0
        
        usage = self.usage.get(username, 0)
        quota = user["quota"]
        
        return usage < quota, usage, quota
    
    def increment_usage(self, username: str) -> bool:
        """
        زيادة عداد الاستعلامات
        
        Returns:
            bool: هل تمت الزيادة بنجاح
        """
        if username not in self.users:
            return False
        
        # التحقق من الحد أولاً
        allowed, usage, quota = self.check_quota(username)
        if not allowed and self.users[username].get("quota") is not None:
            return False
        
        self.usage[username] = self.usage.get(username, 0) + 1
        self._save_usage()
        return True
    
    def get_usage(self, username: str) -> int:
        """الحصول على عدد الاستعلامات المستخدمة"""
        return self.usage.get(username, 0)
    
    def get_remaining(self, username: str) -> int:
        """الحصول على الاستعلامات المتبقية"""
        if username not in self.users:
            return 0
        
        user = self.users[username]
        if user.get("quota") is None:
            return -1  # غير محدود
        
        usage = self.usage.get(username, 0)
        return max(0, user["quota"] - usage)
    
    def reset_usage(self, username: str = None):
        """إعادة تعيين عداد مستخدم معين أو الكل"""
        if username:
            self.usage.pop(username, None)
        else:
            self.usage = {}
        self._save_usage()

# نسخة واحدة للتطبيق
user_manager = UserManager()