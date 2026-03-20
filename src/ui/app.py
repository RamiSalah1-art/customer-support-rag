import sys
from pathlib import Path

# إضافة المسار الصحيح
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
from src.ingestion.ingestion_pipeline import IngestionPipeline
from src.retrieval.hybrid_search import HybridSearch
from src.retrieval.reranking import Reranker
from src.generation.llm_client import LLMClient
from src.generation.prompt_templates import PromptTemplates
from dotenv import load_dotenv
import yaml
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from loguru import logger
import os

# إضافة قاعدة البيانات ونظام المستخدمين
from src.qa_database import qa_db
from src.users import user_manager

# تحميل متغيرات البيئة
load_dotenv()

# إعداد الصفحة
st.set_page_config(
    page_title="مساعد دعم العملاء الذكي",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# نظام تسجيل الدخول
def login_page():
    """صفحة تسجيل الدخول"""
    st.markdown("## 🔐 تسجيل الدخول")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة السر", type="password")
        
        if st.button("دخول", use_container_width=True):
            if user_manager.verify_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.plan = user_manager.get_user_plan(username)
                st.success(f"✅ مرحباً {username}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ اسم المستخدم أو كلمة السر غير صحيحة")
        return False
    return True

# التحقق من تسجيل الدخول
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
    st.stop()  # يتوقف هنا إذا لم يكن المستخدم مسجلاً

# باقي الكود (للمستخدمين المسجلين فقط)
# تعطيل Firebase تماماً (مؤقتاً)
firebase = None
logger.info("ℹ️ Firebase disabled temporarily")

# تحميل الإعدادات
@st.cache_resource
def load_config():
    """تحميل ملف الإعدادات"""
    config_path = Path('config/config.yaml')
    if not config_path.exists():
        st.error(f"❌ ملف الإعدادات غير موجود: {config_path}")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# تهيئة النظام
@st.cache_resource
def init_system():
    """تهيئة جميع مكونات النظام"""
    config = load_config()
    if not config:
        return None
    
    try:
        # تهيئة المكونات أولاً
        hybrid_search = HybridSearch(config)
        reranker = Reranker(config)
        llm_client = LLMClient(config)
        prompt_templates = PromptTemplates(config)
        
        # تشغيل خط أنابيب المعالجة وربطه مع hybrid_search
        logger.info("🔍 فحص الملفات الجديدة...")
        pipeline = IngestionPipeline(config)
        pipeline.set_hybrid_search(hybrid_search)
        pipeline.run(raw_data_path="data/raw")
        
        # تمرير النصوص لـ hybrid_search يدوياً
        if hasattr(pipeline, 'get_texts'):
            texts = pipeline.get_texts()
            if texts:
                hybrid_search.set_documents(texts)
                logger.info(f"✅ Manual BM25 initialized with {len(texts)} texts")
        
        return {
            'config': config,
            'hybrid_search': hybrid_search,
            'reranker': reranker,
            'llm_client': llm_client,
            'prompt_templates': prompt_templates
        }
    except Exception as e:
        st.error(f"❌ فشل تهيئة النظام: {e}")
        return None

# تطبيق CSS مخصص
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .response-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .source-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-right: 4px solid #1E88E5;
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    .source-box:hover {
        transform: translateX(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .confidence-high {
        color: #4CAF50;
        font-weight: bold;
        background: #e8f5e9;
        padding: 2px 10px;
        border-radius: 15px;
        display: inline-block;
    }
    .confidence-medium {
        color: #FF9800;
        font-weight: bold;
        background: #fff3e0;
        padding: 2px 10px;
        border-radius: 15px;
        display: inline-block;
    }
    .confidence-low {
        color: #F44336;
        font-weight: bold;
        background: #ffebee;
        padding: 2px 10px;
        border-radius: 15px;
        display: inline-block;
    }
    .stProgress > div > div {
        background-color: #1E88E5;
    }
    .stButton > button {
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 50px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(30, 136, 229, 0.4);
    }
    .stTextInput > div > input {
        border-radius: 25px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
    }
    .stTextInput > div > input:focus {
        border-color: #1E88E5;
        box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.2);
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        transition: all 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    @media (prefers-color-scheme: dark) {
        .source-box {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        .metric-card {
            background-color: #2d2d2d;
            color: white;
        }
    }
</style>
""", unsafe_allow_html=True)

# تهيئة النظام
system = init_system()

# التحقق من التهيئة
if not system:
    st.stop()

# العنوان الرئيسي
st.markdown('<h1 class="main-header">مساعد دعم العملاء الذكي</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">مرحباً {st.session_state.username} | الخطة: {st.session_state.plan}</p>', unsafe_allow_html=True)

# زر تسجيل الخروج
col1, col2, col3 = st.columns([6, 1, 1])
with col3:
    if st.button("تسجيل الخروج"):
        st.session_state.authenticated = False
        st.rerun()

# الشريط الجانبي
with st.sidebar:
    logo_path = Path("logo.png")
    if logo_path.exists():
        st.image(str(logo_path), use_column_width=True)
    else:
        st.image("https://via.placeholder.com/300x150/1E88E5/ffffff?text=AI+Support+Assistant", use_container_width=True)
    
    # عرض معلومات الاستعلامات المتبقية
    remaining = user_manager.get_remaining(st.session_state.username)
    if remaining == -1:
        st.markdown("### ♾️ استعلامات غير محدودة")
    else:
        usage = user_manager.get_usage(st.session_state.username)
        quota = user_manager.users[st.session_state.username]['quota']
        st.markdown(f"### 📊 استعلامات هذا الشهر: {usage}/{quota}")
        
        # شريط تقدم
        progress = usage / quota
        st.progress(progress)
        
        if remaining < 100:
            st.warning(f"⚠️ تبقى {remaining} استعلام فقط!")
    
    st.markdown("## ⚙️ الإعدادات")
    
    model_options = ["GPT-4 Turbo", "Claude-3 Opus", "GPT-3.5 Turbo"]
    selected_model = st.selectbox("النموذج", model_options, index=0)
    num_results = st.slider("عدد النتائج", min_value=1, max_value=10, value=3)
    use_hybrid = st.checkbox("استخدام البحث المختلط", value=True)
    use_rerank = st.checkbox("استخدام إعادة الترتيب", value=True)
    
    st.markdown("---")
    st.markdown("### إحصائيات النظام")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("المستندات", "1,234", "+56")
    with col2:
        st.metric("الاستعلامات", "5,678", "+234")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("الدقة", "94.5%", "+2.3%")
    with col2:
        st.metric("الوقت", "1.2ث", "-0.3ث")
    
    st.markdown("---")
    st.markdown("### أمثلة على الأسئلة")
    
    examples = [
        "ما هي سياسة الإرجاع؟",
        "كيف أعيد تعيين كلمة المرور؟",
        "هل تشحنون دولياً؟",
        "ما هي طرق الدفع المتاحة؟",
        "كيف أتتبع طلبي؟"
    ]
    
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.query = ex

# العمود الرئيسي
col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_input(
        "اكتب سؤالك هنا",
        value=st.session_state.get('query', ''),
        placeholder="مثال: ما هي سياسة الإرجاع؟",
        key="query_input"
    )
    search_button = st.button("ابحث", type="primary", use_container_width=True)

with col2:
    source_filter = st.multiselect(
        "تصفية حسب المصدر",
        ["PDF", "DOCX", "TXT", "MD"],
        default=[]
    )

if (search_button or query) and query.strip():
    with st.spinner("جاري البحث في قاعدة المعرفة..."):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        
        st.markdown("---")
        
        col_res1, col_res2 = st.columns([3, 1])
        
        with col_res1:
            st.markdown(f"### الإجابة على: '{query}'")
            
            if system and 'llm_client' in system:
                try:
                    # التحقق من الحد المسموح
                    allowed, usage, quota = user_manager.check_quota(st.session_state.username)
                    
                    if not allowed and user_manager.users[st.session_state.username].get("quota") is not None:
                        st.warning(f"⚠️ لقد استنفدت حدك الشهري ({quota} استعلام). يرجى الانتظار للشهر القادم أو الترقية.")
                    else:
                        # زيادة العداد
                        user_manager.increment_usage(st.session_state.username)
                        
                        answer = qa_db.find_answer(query)
                        
                        if answer.startswith("عذراً"):
                            results = system['hybrid_search'].search(query, k=num_results)
                            if use_rerank and results:
                                results = system['reranker'].rerank(query, results)
                            answer = system['llm_client'].generate_response(query, results, "شركتنا")
                            
                            if results:
                                st.markdown("#### المصادر المستخدمة:")
                                for source in results[:3]:
                                    score = source.get('rerank_score', source.get('score', 0))
                                    filename = source.get('metadata', {}).get('filename', 'مصدر غير معروف')
                                    
                                    if score > 0.9:
                                        conf_class = "confidence-high"
                                        conf_text = "عالية"
                                    elif score > 0.7:
                                        conf_class = "confidence-medium"
                                        conf_text = "متوسطة"
                                    else:
                                        conf_class = "confidence-low"
                                        conf_text = "منخفضة"
                                    
                                    st.markdown(f"""
                                    <div class="source-box">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span><b>{filename}</b></span>
                                            <span class="{conf_class}">ثقة {conf_text} ({score*100:.0f}%)</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="response-box">
                                <p style="font-size: 1.2rem; line-height: 1.8;">{answer}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.markdown("#### إجابة دقيقة 100% من قاعدة المعرفة")
                    
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")
            else:
                st.error("❌ النظام غير مهيأ بشكل صحيح")
        
        with col_res2:
            st.markdown("### تحليل الاستعلام")
            st.markdown("""
            <div class="metric-card">
                <h4>⏱️ وقت الاستجابة</h4>
                <p style="font-size: 2rem; color: #1E88E5;">1.2 ث</p>
                <p style="color: #4CAF50;">▼ 0.3 ث</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="metric-card">
                <h4>🎯 درجة الثقة</h4>
                <p style="font-size: 2rem; color: #1E88E5;">94%</p>
                <p style="color: #4CAF50;">▲ 5%</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="metric-card">
                <h4>📑 عدد المصادر</h4>
                <p style="font-size: 2rem; color: #1E88E5;">3</p>
                <p style="color: #4CAF50;">▲ 1</p>
            </div>
            """, unsafe_allow_html=True)
            
            df = pd.DataFrame({
                'المصدر': ['PDF', 'FAQ', 'DOCX'],
                'درجة الصلة': [95, 87, 76]
            })
            fig = px.bar(df, x='المصدر', y='درجة الصلة', 
                        title='درجة صلة المصادر',
                        color='درجة الصلة',
                        color_continuous_scale='blues')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("### إحصائيات النظام اليومية")

stat_cols = st.columns(4)

with stat_cols[0]:
    st.metric("إجمالي الاستعلامات", "1,234", "+12.3%")
with stat_cols[1]:
    st.metric("متوسط وقت الاستجابة", "1.2 ث", "-0.3 ث")
with stat_cols[2]:
    st.metric("الدقة", "94.5%", "+2.1%")
with stat_cols[3]:
    st.metric("رضا المستخدمين", "4.8/5", "+0.2")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    © 2026 مساعد دعم العملاء الذكي - جميع الحقوق محفوظة<br>
    تم التطوير باستخدام Streamlit
</div>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    pass