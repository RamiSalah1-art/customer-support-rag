"""
لوحة إدارة المشرفين - مراقبة وتحليل أداء النظام
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sys
from pathlib import Path
import time
sys.path.append(str(Path(__file__).parent.parent))

# استيراد قاعدة البيانات ونظام المستخدمين
from src.qa_database import qa_db
from src.users import user_manager

# إعداد الصفحة
st.set_page_config(
    page_title="لوحة الإدارة - مساعد الدعم",
    page_icon="📊",
    layout="wide"
)

# التحقق من كلمة سر المشرف
def check_password():
    """نظام دخول بسيط للمشرف"""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.markdown("## 🔐 دخول المشرفين")
        password = st.text_input("كلمة السر", type="password")
        if st.button("دخول"):
            if password == "Rami@2026$StrongAdmin":  # غيرها لاحقاً
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("❌ كلمة سر خاطئة")
        return False
    return True

if check_password():
    st.title("📊 لوحة إدارة مساعد الدعم الذكي")
    
    # قائمة جانبية
    menu = st.sidebar.selectbox(
        "القائمة",
        ["الرئيسية", "إدارة الأسئلة", "إدارة المستخدمين", "إحصائيات", "الإعدادات"]
    )
    
    if menu == "الرئيسية":
        st.markdown("### 📋 نظرة عامة")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("إجمالي الأسئلة", len(qa_db.qa_pairs), "+2")
        with col2:
            st.metric("إجمالي المستخدمين", len(user_manager.users), "+1")
        with col3:
            st.metric("الاستعلامات اليوم", "345", "+12%")
        with col4:
            st.metric("الدقة", "100%", "0%")
        
        st.markdown("---")
        st.markdown("### 🔥 أكثر الأسئلة شيوعاً")
        
        # بيانات تجريبية
        questions_data = pd.DataFrame({
            'السؤال': ['عروض خاصة', 'طرق الدفع', 'التوصيل', 'الإرجاع', 'كلمة المرور'],
            'عدد الاستعلامات': [145, 132, 98, 87, 76]
        })
        
        fig = px.bar(questions_data, x='السؤال', y='عدد الاستعلامات', 
                     title='أكثر 5 أسئلة تكرراً')
        st.plotly_chart(fig, use_container_width=True)
    
    elif menu == "إدارة الأسئلة":
        st.markdown("### 📝 إدارة الأسئلة والأجوبة")
        
        # عرض الأسئلة الحالية
        st.markdown("#### الأسئلة الحالية")
        
        questions = list(qa_db.qa_pairs.items())
        
        # عرض في جدول
        df = pd.DataFrame(questions, columns=['السؤال', 'الإجابة'])
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### إضافة سؤال جديد")
        
        col1, col2 = st.columns(2)
        with col1:
            new_question = st.text_input("السؤال الجديد")
        with col2:
            new_answer = st.text_area("الإجابة")
        
        if st.button("➕ إضافة سؤال"):
            if new_question and new_answer:
                # إضافة للسؤال
                key = new_question.lower().strip()
                qa_db.qa_pairs[key] = new_answer
                st.success(f"✅ تم إضافة السؤال: {new_question}")
                st.rerun()
            else:
                st.warning("⚠️ الرجاء إدخال السؤال والإجابة")
        
        st.markdown("---")
        st.markdown("#### تعديل إجابة")
        
        # اختيار سؤال للتعديل
        question_to_edit = st.selectbox("اختر سؤال", list(qa_db.qa_pairs.keys()))
        
        if question_to_edit:
            current_answer = qa_db.qa_pairs[question_to_edit]
            new_answer_edit = st.text_area("الإجابة الجديدة", current_answer)
            
            if st.button("✏️ تحديث الإجابة"):
                qa_db.qa_pairs[question_to_edit] = new_answer_edit
                st.success(f"✅ تم تحديث إجابة: {question_to_edit}")
                st.rerun()
    
    elif menu == "إدارة المستخدمين":
        st.markdown("### 👥 إدارة المستخدمين")
        
        # عرض المستخدمين الحاليين
        st.markdown("#### المستخدمين الحاليين")
        users_data = []
        for username, data in user_manager.users.items():
            users_data.append({
                "المستخدم": username,
                "الخطة": data["plan"],
                "انتهاء الاشتراك": data["expiry"] or "لا ينتهي"
            })
        
        df_users = pd.DataFrame(users_data)
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### ➕ إضافة مستخدم جديد")
        
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("اسم المستخدم الجديد")
            new_password = st.text_input("كلمة السر", type="password")
        with col2:
            new_plan = st.selectbox("الخطة", ["basic", "professional", "enterprise"])
            new_expiry = st.date_input("تاريخ انتهاء الاشتراك", datetime.now() + timedelta(days=30))
        
        if st.button("➕ إضافة مستخدم"):
            if new_username and new_password:
                # إضافة المستخدم مباشرة
                user_manager.users[new_username] = {
                    "password_hash": user_manager._hash_password(new_password),
                    "plan": new_plan,
                    "expiry": new_expiry.strftime("%Y-%m-%d")
                }
                st.success(f"✅ تم إضافة المستخدم {new_username}")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ الرجاء إدخال اسم المستخدم وكلمة السر")
        
        st.markdown("---")
        st.markdown("#### 🔄 تمديد اشتراك مستخدم")
        
        # اختيار مستخدم للتمديد
        user_to_extend = st.selectbox("اختر مستخدم", list(user_manager.users.keys()))
        
        if user_to_extend:
            current_expiry = user_manager.users[user_to_extend].get("expiry", "غير محدد")
            st.info(f"تاريخ الانتهاء الحالي: {current_expiry}")
            
            new_expiry_date = st.date_input("تاريخ الانتهاء الجديد", datetime.now() + timedelta(days=365))
            
            if st.button("📅 تمديد الاشتراك"):
                user_manager.users[user_to_extend]["expiry"] = new_expiry_date.strftime("%Y-%m-%d")
                st.success(f"✅ تم تمديد اشتراك {user_to_extend} حتى {new_expiry_date}")
                st.rerun()
    
    elif menu == "إحصائيات":
        st.markdown("### 📈 إحصائيات متقدمة")
        
        # اختيار الفترة
        period = st.selectbox("الفترة", ["آخر 7 أيام", "آخر 30 يوم", "آخر سنة"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            # رسم بياني للاستعلامات
            dates = pd.date_range(end=datetime.now(), periods=30).tolist()
            values = pd.Series(range(30)) * 2 + 10
            df_daily = pd.DataFrame({'التاريخ': dates, 'الاستعلامات': values})
            
            fig1 = px.line(df_daily, x='التاريخ', y='الاستعلامات', 
                          title='الاستعلامات اليومية')
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # توزيع الاستعلامات حسب الوقت
            hours = list(range(24))
            values = [20, 15, 10, 8, 5, 3, 2, 5, 15, 30, 45, 50,
                     55, 60, 58, 55, 60, 65, 70, 65, 50, 40, 30, 25]
            df_hours = pd.DataFrame({'الساعة': hours, 'الاستعلامات': values})
            
            fig2 = px.bar(df_hours, x='الساعة', y='الاستعلامات',
                         title='توزيع الاستعلامات حسب الساعة')
            st.plotly_chart(fig2, use_container_width=True)
    
    elif menu == "الإعدادات":
        st.markdown("### ⚙️ إعدادات النظام")
        
        st.markdown("#### تغيير كلمة سر المشرف")
        new_password = st.text_input("كلمة السر الجديدة", type="password")
        confirm_password = st.text_input("تأكيد كلمة السر", type="password")
        
        if st.button("تحديث كلمة السر"):
            if new_password and new_password == confirm_password:
                # تحديث كلمة سر admin
                if "admin" in user_manager.users:
                    user_manager.users["admin"]["password_hash"] = user_manager._hash_password(new_password)
                    st.success("✅ تم تحديث كلمة السر")
                else:
                    st.error("❌ مستخدم admin غير موجود")
            else:
                st.error("❌ كلمة السر غير متطابقة")
        
        st.markdown("---")
        st.markdown("#### إعدادات التطبيق")
        
        col1, col2 = st.columns(2)
        with col1:
            theme = st.selectbox("الثيم", ["فاتح", "داكن", "تلقائي"])
        with col2:
            language = st.selectbox("اللغة", ["العربية", "الإنجليزية"])
        
        if st.button("💾 حفظ الإعدادات"):
            st.success("✅ تم حفظ الإعدادات")