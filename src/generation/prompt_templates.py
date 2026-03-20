"""
وحدة إدارة قوالب المطالبات - تنظيم وتنسيق المطالبات المختلفة
"""

from typing import Dict, Any, Optional
import yaml
from pathlib import Path
from loguru import logger

class PromptTemplates:
    """إدارة قوالب المطالبات للنماذج اللغوية"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """تحميل القوالب من ملف YAML"""
        template_path = self.config.get('generation', {}).get('prompt_template', 'config/prompts.yaml')
        
        try:
            if Path(template_path).exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    self.templates = yaml.safe_load(f)
                logger.info(f"✅ Loaded {len(self.templates)} prompt templates")
            else:
                logger.warning(f"⚠️ Template file not found: {template_path}")
                self._load_default_templates()
        except Exception as e:
            logger.error(f"❌ Failed to load templates: {e}")
            self._load_default_templates()
    
    def _load_default_templates(self):
        """تحميل القوالب الافتراضية إذا لم يوجد ملف"""
        self.templates = {
            'rag_prompt': self._get_default_rag_prompt(),
            'query_expansion_prompt': self._get_default_query_expansion_prompt(),
            'evaluation_prompt': self._get_default_evaluation_prompt(),
            'summarization_prompt': self._get_default_summarization_prompt()
        }
        logger.info("✅ Loaded default templates")
    
    def get_template(self, template_name: str, **kwargs) -> str:
        """
        الحصول على قالب منسق
        
        Args:
            template_name: اسم القالب
            **kwargs: المتغيرات المراد إدراجها في القالب
            
        Returns:
            النص المنسق
        """
        template = self.templates.get(template_name, '')
        if not template:
            logger.warning(f"Template '{template_name}' not found, using empty string")
            return ''
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Error formatting template: {e}")
            return template
    
    def get_system_prompt(self, persona: str = "customer_support") -> str:
        """
        الحصول على رسالة النظام (system prompt) حسب الشخصية
        
        Args:
            persona: نوع الشخصية (customer_support, code_assistant, etc.)
            
        Returns:
            نص رسالة النظام
        """
        system_prompts = {
            "customer_support": """
                أنت مساعد دعم عملاء محترف. تتميز بـ:
                - الدقة: تستخدم فقط المعلومات المقدمة لك
                - الأدب: تتحدث بلغة مهذبة ومحترمة
                - الوضوح: تقدم إجابات واضحة ومباشرة
                - المساعدة: تسعى دائماً لحل مشكلة العميل
                
                إذا لم تكن متأكداً من المعلومة، قل ذلك بصراحة.
                استشهد بالمصادر عند الإمكان.
            """,
            
            "code_assistant": """
                أنت مساعد برمجة خبير. تتميز بـ:
                - كتابة كود نظيف ومنظم
                - شرح الكود خطوة بخطوة
                - اقتراح أفضل الممارسات
                - تحسين أداء الكود
                
                قدم أمثلة عملية مع الشرح.
            """,
            
            "analyst": """
                أنت محلل بيانات محترف. تتميز بـ:
                - تحليل دقيق ومنهجي
                - استخلاص رؤى قيمة من البيانات
                - تقديم توصيات قابلة للتنفيذ
                - استخدام لغة واضحة غير تقنية
                
                ادعم تحليلك بالأرقام والحقائق.
            """
        }
        
        return system_prompts.get(persona, system_prompts["customer_support"])
    
    def _get_default_rag_prompt(self) -> str:
        """قالب RAG الافتراضي"""
        return """
            أنت مساعد دعم عملاء ذكي لشركة {company_name}. 
            مهمتك هي الإجابة على استفسارات العملاء بناءً فقط على المعلومات المقدمة في السياق أدناه.
            
            ## تعليمات مهمة:
            1. استخدم فقط المعلومات الموجودة في السياق للإجابة
            2. إذا لم تكن المعلومة موجودة في السياق، قل "لا توجد معلومات كافية للإجابة على هذا السؤال في قاعدة معرفتنا"
            3. استشهد بالمصدر لكل معلومة تقدمها (باستخدام [المصدر: اسم المستند])
            4. كن دقيقاً ومختصراً، لا تزد معلومات من عندك
            5. استخدم لغة مهذبة واحترافية
            
            ## السياق المتاح:
            {context}
            
            ## سؤال العميل:
            {question}
            
            ## الإجابة:
        """
    
    def _get_default_query_expansion_prompt(self) -> str:
        """قالب توسيع الاستعلام الافتراضي"""
        return """
            أنت خبير في تحسين استعلامات البحث.
            
            السؤال الأصلي: {original_query}
            
            المهمة: قم بتوليد 3 صيغ بديلة لنفس السؤال لتحسين فرص العثور على المعلومات.
            
            تعليمات:
            - استخدم مرادفات مختلفة
            - غير صياغة السؤال
            - أضف كلمات مفتاحية محتملة ذات صلة
            - حافظ على نفس المعنى الأساسي
            
            الصيغ البديلة (صيغة JSON):
        """
    
    def _get_default_evaluation_prompt(self) -> str:
        """قالب التقييم الافتراضي"""
        return """
            أنت مقيم خبير لأنظمة الذكاء الاصطناعي.
            
            السؤال: {question}
            الإجابة المتوقعة: {expected_answer}
            إجابة النظام: {system_answer}
            السياق المستخدم: {context}
            
            قيم الإجابة وفق المقاييس التالية (من 0 إلى 10):
            
            1. الدقة (Accuracy): هل الإجابة صحيحة واقعياً؟
            2. الاكتمال (Completeness): هل تغطي الإجابة جميع جوانب السؤال؟
            3. الاستشهاد بالمصادر (Citation): هل تستخدم الإجابة المصادر بشكل صحيح؟
            4. عدم الهلوسة (Hallucination): هل تلتزم الإجابة بالمعلومات الموجودة فقط؟
            5. الوضوح (Clarity): هل الإجابة واضحة وسهلة الفهم؟
            
            قدم تقييمك بصيغة JSON مع تعليق مختصر لكل مقياس.
        """
    
    def _get_default_summarization_prompt(self) -> str:
        """قالب التلخيص الافتراضي"""
        return """
            أنت خبير في تلخيص النصوص.
            
            النص الأصلي:
            {text}
            
            المهمة: قدم تلخيصاً دقيقاً للنص مع الحفاظ على المعلومات الرئيسية.
            
            الطول المطلوب: {max_length} كلمة
            
            التلخيص:
        """
    
    def add_template(self, name: str, template: str):
        """إضافة قالب جديد"""
        self.templates[name] = template
        logger.info(f"✅ Added new template: {name}")
    
    def save_templates(self, file_path: Optional[str] = None):
        """حفظ القوالب إلى ملف"""
        save_path = file_path or 'config/prompts.yaml'
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.templates, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"✅ Templates saved to {save_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save templates: {e}")