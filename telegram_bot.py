# telegram_bot.py
import sys
from pathlib import Path
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إضافة مسار المشروع
sys.path.append(str(Path(__file__).parent))
from src.qa_database import qa_db

# إعدادات التسجيل (لرؤية الأخطاء)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# استبدل هذا بالتوكن الذي حصلت عليه من BotFather
TOKEN = "8740927932:AAHakHOdtarWGHGphOSzJszEN8su6US0wX0"

# أمر /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
🌟 مرحباً بك في بوت مساعد دعم العملاء الذكي! 🌟

أنا هنا لمساعدتك في الإجابة عن أي استفسارات متعلقة بالمنتجات والخدمات.

📝 **كيف تستخدمني؟**
فقط اكتب سؤالك وسأجيبك فوراً!

❓ **نماذج أسئلة:**
• ما هي طرق الدفع المتاحة؟
• كيف أعيد تعيين كلمة المرور؟
• كم يستغرق توصيل الطلب؟
• ما هي سياسة الإرجاع؟

📞 للدعم المباشر: +249 91 900 0011

ابدأ بكتابة سؤالك الآن! 🚀
    """
    await update.message.reply_text(welcome_message)

# أمر /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = """
🔍 **المساعدة**

اكتب أي سؤال وسأحاول الإجابة عليه.

الأسئلة المدعومة حالياً:
• عروض خاصة
• طرق الدفع
• كلمة المرور
• التوصيل
• الإرجاع
• الدعم الفني
• ساعات العمل
• المنتجات
• تتبع الطلب

إذا لم أستطع الإجابة، سأخبرك بذلك.
    """
    await update.message.reply_text(help_message)

# معالجة الرسائل النصية (الأسئلة)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    user = update.effective_user.first_name
    
    logger.info(f"سؤال من {user}: {question}")
    
    # البحث عن إجابة في قاعدة البيانات
    answer = qa_db.find_answer(question)
    
    # إرسال الرد
    response = f"❓ **سؤالك:** {question}\n\n✅ **الإجابة:** {answer}"
    await update.message.reply_text(response)

# معالجة الأخطاء
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"حدث خطأ: {context.error}")
    if update and update.message:
        await update.message.reply_text("عذراً، حدث خطأ تقني. يرجى المحاولة لاحقاً.")

# تشغيل البوت
def main():
    print("🤖 جاري تشغيل البوت...")
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # بدء البوت
    print("✅ البوت يعمل الآن! اضغط Ctrl+C للإيقاف")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()