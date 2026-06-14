"""
Wakeel وکیل — Know Your Rights Scenario Engine
================================================
Guided decision-tree flowchart for common Pakistani legal situations.

Each scenario is a dict of steps. Each step has:
  - question_ur: the yes/no question in Urdu
  - question_en: English version
  - context_ur: explanatory context in Urdu
  - yes: next step_id if user answers yes
  - no:  next step_id if user answers no
  - terminal: True if this is the final step
  - guidance_ur: final advice (only on terminal steps)
  - action_steps: list of concrete actions (only on terminal steps)
  - urgency: "immediate" | "within_24h" | "within_week"
"""

from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO DECISION TREES
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS: dict[str, dict] = {

# ───────────────────────────────────────────────────────────────────────────
"arrested": {
    "title_ur": "مجھے گرفتار کیا گیا ہے",
    "title_en": "I Have Been Arrested",
    "icon": "🚔",
    "steps": {
        "start": {
            "question_ur": "کیا پولیس نے آپ کو گرفتاری کی وجہ بتائی ہے؟",
            "question_en": "Did the police inform you of the reason for your arrest?",
            "context_ur": "آرٹیکل 10 کے تحت پاکستانی آئین آپ کو گرفتاری کی وجہ جاننے کا حق دیتا ہے۔",
            "yes": "warrant_check",
            "no": "no_reason_given",
        },
        "no_reason_given": {
            "question_ur": "کیا آپ نے پولیس سے وجہ پوچھی ہے؟",
            "question_en": "Have you asked the police for the reason?",
            "context_ur": "آپ کو فوری طور پر گرفتاری کی وجہ بتانا پولیس کی قانونی ذمہ داری ہے۔",
            "yes": "demand_reason_terminal",
            "no": "demand_reason_terminal",
        },
        "demand_reason_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": (
                "پولیس کا آپ کو گرفتاری کی وجہ نہ بتانا آئین کی خلاف ورزی ہے۔\n\n"
                "فوری اقدامات کریں:"
            ),
            "action_steps": [
                "پولیس افسر سے واضح طور پر کہیں: 'مجھے گرفتاری کی وجہ بتائیں — یہ میرا آئینی حق ہے (آرٹیکل 10)'",
                "کسی خاندان کے فرد یا دوست کو فوری فون کریں اور اپنی جگہ بتائیں",
                "وکیل سے رابطہ کریں — پاکستان بار کونسل: 051-9207046",
                "اگر پولیس وجہ نہ بتائے تو تھانے کے SHO سے ملیں",
                "24 گھنٹے کے اندر مجسٹریٹ کے سامنے پیش ہونے کا مطالبہ کریں (دفعہ 61 CrPC)",
            ],
            "helplines": ["پولیس شکایات: 8787", "قانونی امداد: 051-9207046"],
        },
        "warrant_check": {
            "question_ur": "کیا پولیس کے پاس گرفتاری کا وارنٹ ہے؟",
            "question_en": "Does the police have an arrest warrant?",
            "context_ur": "غیر علمی جرائم (non-cognizable) میں پولیس کو گرفتاری کے لیے مجسٹریٹ کا وارنٹ چاہیے۔",
            "yes": "bailable_check",
            "no": "cognizable_check",
        },
        "cognizable_check": {
            "question_ur": "کیا الزام قتل، ڈکیتی، یا عصمت دری جیسا سنگین جرم ہے؟",
            "question_en": "Is the charge a serious offence like murder, robbery, or rape?",
            "context_ur": "سنگین جرائم (cognizable offences) میں پولیس وارنٹ کے بغیر گرفتار کر سکتی ہے۔",
            "yes": "serious_offence",
            "no": "illegal_arrest_terminal",
        },
        "illegal_arrest_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "یہ غیر قانونی گرفتاری ہو سکتی ہے۔ پولیس کو معمولی جرائم میں وارنٹ کے بغیر گرفتار کرنے کا حق نہیں۔",
            "action_steps": [
                "فوری طور پر وکیل سے رابطہ کریں",
                "ہائی کورٹ میں آرٹیکل 199 کے تحت حبس بے جا (Habeas Corpus) کی درخواست دائر کریں",
                "پولیس کے SHO اور DSP کو لکھ کر احتجاج کریں",
                "NHRC (قومی انسانی حقوق کمیشن) کو شکایت کریں: 051-9107500",
                "اپنے خاندان کو فوری مطلع کریں",
            ],
            "helplines": ["NHRC: 051-9107500", "قانونی امداد: 051-9207046"],
        },
        "serious_offence": {
            "question_ur": "کیا آپ نے ابھی تک وکیل سے رابطہ کیا ہے؟",
            "question_en": "Have you contacted a lawyer yet?",
            "context_ur": "سنگین الزامات میں فوری قانونی مشورہ انتہائی ضروری ہے۔",
            "yes": "bail_check",
            "no": "get_lawyer_terminal",
        },
        "get_lawyer_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "سنگین الزامات میں وکیل کے بغیر کچھ نہ بولیں — یہ آپ کے خلاف استعمال ہو سکتا ہے۔",
            "action_steps": [
                "ابھی خاندان کو فون کریں اور وکیل کا انتظام کہیں",
                "کچھ بھی بیان دینے سے انکار کریں جب تک وکیل موجود نہ ہو",
                "اپنا نام اور شناخت بتانے کے علاوہ خاموش رہیں",
                "پولیس کو کوئی کاغذ سائن نہ کریں",
                "24 گھنٹے میں مجسٹریٹ کے سامنے پیش ہونے کا حق یاد رکھیں",
                "اگر وکیل نہیں کر سکتے: ضلعی قانونی امداد کمیٹی سے مفت وکیل مانگیں",
            ],
            "helplines": ["قانونی امداد: 051-9207046", "AGHS: 042-35761999"],
        },
        "bailable_check": {
            "question_ur": "کیا آپ کو بتایا گیا ہے کہ جرم ضمانت والا ہے (bailable) ہے؟",
            "question_en": "Have you been told the offence is bailable?",
            "context_ur": "ضمانت والے جرائم میں پولیس کو آپ کو ضمانت دینی ہی پڑتی ہے — یہ آپ کا قانونی حق ہے۔",
            "yes": "bail_granted_check",
            "no": "non_bailable_terminal",
        },
        "bail_granted_check": {
            "question_ur": "کیا پولیس نے ضمانت دینے سے انکار کیا ہے؟",
            "question_en": "Has the police refused to grant bail?",
            "context_ur": "ضمانت والے جرم میں پولیس کا انکار غیر قانونی ہے۔",
            "yes": "bail_refused_terminal",
            "no": "bail_conditions_terminal",
        },
        "bail_refused_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "ضمانت والے جرم میں پولیس کا ضمانت سے انکار آپ کے حقوق کی خلاف ورزی ہے۔",
            "action_steps": [
                "SHO (تھانیدار) سے لکھ کر ضمانت مانگیں",
                "مجسٹریٹ کے سامنے ضمانت کی درخواست دائر کریں",
                "SP (سپرنٹنڈنٹ آف پولیس) کو شکایت کریں",
                "وکیل سے فوری ملیں — مجسٹریٹ کورٹ میں ضمانت کی درخواست دائر کریں",
            ],
            "helplines": ["پولیس شکایات: 8787"],
        },
        "bail_conditions_terminal": {
            "terminal": True,
            "urgency": "within_24h",
            "guidance_ur": "ضمانت مل گئی ہے۔ اب ان اہم باتوں کا خیال رکھیں:",
            "action_steps": [
                "ضمانت کی تمام شرائط کو احتیاط سے پڑھیں اور پوری کریں",
                "ہر پیشی پر حاضر ہوں — غیر حاضری پر ضمانت منسوخ ہو سکتی ہے",
                "وکیل سے مشورہ کریں کہ کیس کیسے آگے چلے گا",
                "شہر سے باہر جانے سے پہلے عدالت کی اجازت لیں",
                "گواہوں یا شاکی سے کوئی رابطہ نہ کریں",
            ],
            "helplines": [],
        },
        "non_bailable_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "غیر ضمانتی جرم میں ضمانت عدالت کی صوابدید پر ہے۔ فوری اقدامات کریں:",
            "action_steps": [
                "فوری وکیل کریں — ضمانت کی درخواست مجسٹریٹ یا سیشن کورٹ میں دائر ہوگی",
                "24 گھنٹے میں مجسٹریٹ کے سامنے پیشی کا حق مانگیں",
                "پولیس ریمانڈ زیادہ سے زیادہ 15 دن ہے — اس کے بعد عدالتی ریمانڈ",
                "خاموش رہیں — بغیر وکیل کوئی بیان نہ دیں",
                "تشدد کی صورت میں: ڈاکٹر سے معائنہ کروائیں اور NHRC کو مطلع کریں",
            ],
            "helplines": ["NHRC: 051-9107500", "AGHS: 042-35761999"],
        },
        "bail_check": {
            "question_ur": "کیا آپ کا وکیل ضمانت کی درخواست دائر کر چکا ہے؟",
            "question_en": "Has your lawyer filed a bail application?",
            "context_ur": "ضمانت کی درخواست جلد از جلد دائر ہونی چاہیے۔",
            "yes": "bail_hearing_terminal",
            "no": "file_bail_terminal",
        },
        "bail_hearing_terminal": {
            "terminal": True,
            "urgency": "within_24h",
            "guidance_ur": "ضمانت کی درخواست دائر ہے — اب صبر کریں اور ان باتوں کا خیال رکھیں:",
            "action_steps": [
                "ہر سماعت پر حاضر رہیں",
                "وکیل کو تمام حقائق بتائیں — کچھ چھپائیں نہیں",
                "خاندان کو صورتحال سے آگاہ رکھیں",
                "ضمانت منظور ہونے تک خاموش رہیں",
                "اگر ضمانت مسترد ہو تو ہائی کورٹ میں اپیل کریں",
            ],
            "helplines": [],
        },
        "file_bail_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "ضمانت کی درخواست فوری دائر کی جانی چاہیے:",
            "action_steps": [
                "وکیل سے آج ہی ضمانت کی درخواست تیار کروائیں",
                "مجسٹریٹ کورٹ میں (3 سال تک کے جرائم) یا سیشن کورٹ میں دائر کریں",
                "FIR کی کاپی، شناختی کارڈ اور دو گواہوں کا انتظام کریں",
                "ضمانت کی رقم کا انتظام کریں (سرپرست کے ذریعے)",
                "اگر ضمانت نہ ملے: ہائی کورٹ میں درخواست دیں",
            ],
            "helplines": ["قانونی امداد: 051-9207046"],
        },
    },
},

# ───────────────────────────────────────────────────────────────────────────
"eviction": {
    "title_ur": "مالک مکان مجھے نکال رہا ہے",
    "title_en": "Facing Eviction",
    "icon": "🏠",
    "steps": {
        "start": {
            "question_ur": "کیا مالک مکان نے آپ کو تحریری نوٹس دیا ہے؟",
            "question_en": "Has the landlord given you a written notice?",
            "context_ur": "پنجاب کرائے دار قانون 2009 کے تحت مالک مکان بغیر تحریری نوٹس اور عدالتی حکم کے نہیں نکال سکتا۔",
            "yes": "notice_reason_check",
            "no": "no_notice_terminal",
        },
        "no_notice_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "بغیر نوٹس کے بے دخلی مکمل طور پر غیر قانونی ہے۔ مالک مکان کو یہ حق نہیں:",
            "action_steps": [
                "مالک مکان کو واضح کہیں کہ آپ بغیر عدالتی حکم کے نہیں جائیں گے",
                "اگر مالک مکان زبردستی کرے: فوری 15 پر پولیس کال کریں",
                "دفعہ 448 (گھر میں زبردستی داخلہ) اور 506 (دھمکی) کے تحت FIR درج کروائیں",
                "رنٹ ٹریبونل میں فوری درخواست دائر کریں",
                "اگر تالا لگا دے یا بجلی/پانی بند کرے: یہ جرم ہے — FIR کریں",
            ],
            "helplines": ["پولیس: 15", "قانونی امداد: 042-99231530"],
        },
        "notice_reason_check": {
            "question_ur": "کیا نوٹس میں بے دخلی کی کوئی قانونی وجہ بتائی گئی ہے (جیسے کرایہ نہ دینا)؟",
            "question_en": "Does the notice state a legal reason (e.g. non-payment of rent)?",
            "context_ur": "قانونی وجوہات: 2 ماہ کا کرایہ نہ دینا، غیر قانونی استعمال، نقصان، یا مالک کی ذاتی ضرورت۔",
            "yes": "rent_default_check",
            "no": "invalid_notice_terminal",
        },
        "invalid_notice_terminal": {
            "terminal": True,
            "urgency": "within_24h",
            "guidance_ur": "بغیر قانونی وجہ کے نوٹس ناقابل عمل ہے۔ آپ کے اختیارات:",
            "action_steps": [
                "نوٹس کا جواب تحریری طور پر دیں کہ وجہ قانونی نہیں",
                "رنٹ ٹریبونل میں نوٹس کو چیلنج کریں",
                "وکیل سے مشورہ کریں",
                "کرایہ ادا کرتے رہیں — بینک ٹرانسفر سے تاکہ ثبوت رہے",
            ],
            "helplines": ["قانونی امداد: 042-99231530"],
        },
        "rent_default_check": {
            "question_ur": "کیا آپ نے 2 یا زیادہ مہینوں کا کرایہ نہیں دیا؟",
            "question_en": "Have you not paid rent for 2 or more months?",
            "context_ur": "2 ماہ کا کرایہ نہ دینا قانونی بے دخلی کی وجہ ہے — لیکن پھر بھی عدالتی حکم ضروری ہے۔",
            "yes": "pay_rent_terminal",
            "no": "contest_eviction_terminal",
        },
        "pay_rent_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "کرایہ بقایا ہے — لیکن ابھی بھی آپ کے پاس حل موجود ہے:",
            "action_steps": [
                "فوری طور پر بقایا کرایہ ادا کریں — بینک ٹرانسفر سے",
                "اگر مالک لینے سے انکار کرے: رنٹ ٹریبونل میں کرایہ جمع کروا دیں",
                "رسید ضرور لیں",
                "رنٹ ٹریبونل میں خود کو رجسٹر کریں",
                "یاد رہے: صرف عدالتی حکم سے بے دخلی ہو سکتی ہے — خود مختار نہیں",
            ],
            "helplines": [],
        },
        "contest_eviction_terminal": {
            "terminal": True,
            "urgency": "within_24h",
            "guidance_ur": "کرایہ باقاعدہ دیا ہے تو بے دخلی کو چیلنج کریں:",
            "action_steps": [
                "تمام کرایہ کی رسیدیں اور بینک ریکارڈ اکٹھے کریں",
                "رنٹ ٹریبونل میں جواب دائر کریں",
                "وکیل کریں — رنٹ کیسز میں عام طور پر کم فیس لگتی ہے",
                "سماعت تک مکان میں رہیں — خود نہ نکلیں",
                "مالک مکان کی کوئی بھی زبانی دھمکی ریکارڈ کریں",
            ],
            "helplines": ["قانونی امداد: 042-99231530"],
        },
    },
},

# ───────────────────────────────────────────────────────────────────────────
"salary_unpaid": {
    "title_ur": "تنخواہ نہیں مل رہی",
    "title_en": "Employer Not Paying Salary",
    "icon": "💼",
    "steps": {
        "start": {
            "question_ur": "کیا آپ کے پاس ملازمت کا تحریری معاہدہ یا appointment letter ہے؟",
            "question_en": "Do you have a written employment contract or appointment letter?",
            "context_ur": "تحریری معاہدہ آپ کا سب سے مضبوط ثبوت ہے۔",
            "yes": "how_many_months",
            "no": "no_contract_check",
        },
        "no_contract_check": {
            "question_ur": "کیا آپ کے پاس تنخواہ کی کوئی سلپ یا بینک ٹرانسفر کا ریکارڈ ہے؟",
            "question_en": "Do you have pay slips or bank transfer records as evidence?",
            "context_ur": "زبانی معاہدہ بھی قانونی ہے — لیکن ثبوت ضروری ہے۔",
            "yes": "how_many_months",
            "no": "gather_evidence_terminal",
        },
        "gather_evidence_terminal": {
            "terminal": True,
            "urgency": "within_week",
            "guidance_ur": "ثبوت کے بغیر کیس مشکل ہے — پہلے یہ اکٹھا کریں:",
            "action_steps": [
                "گواہوں کے بیانات لیں (ساتھی ملازمین)",
                "WhatsApp پیغامات، ای میل محفوظ کریں",
                "حاضری رجسٹر کی کاپی لیں",
                "کسی بھی سرکاری دستاویز کی کاپی لیں جس پر آپ کا نام ہو",
                "پھر لیبر کورٹ میں شکایت دائر کریں",
            ],
            "helplines": ["لیبر ہیلپ لائن: 042-99231530"],
        },
        "how_many_months": {
            "question_ur": "کیا 3 یا زیادہ مہینوں کی تنخواہ رکی ہوئی ہے؟",
            "question_en": "Is salary withheld for 3 or more months?",
            "context_ur": "جتنا زیادہ عرصہ، اتنا مضبوط کیس — لیکن فوری قدم اٹھانا بھی ضروری ہے۔",
            "yes": "serious_salary_terminal",
            "no": "first_complaint_terminal",
        },
        "first_complaint_terminal": {
            "terminal": True,
            "urgency": "within_week",
            "guidance_ur": "پہلے آجر سے تحریری مطالبہ کریں، پھر شکایت درج کریں:",
            "action_steps": [
                "آجر کو تحریری طور پر (رجسٹرڈ خط) تنخواہ کا مطالبہ کریں",
                "7 دن کی مہلت دیں — اگر نہ دے تو لیبر کورٹ جائیں",
                "لیبر کورٹ میں شکایت مفت درج ہوتی ہے",
                "EOBI میں شکایت کریں اگر رجسٹریشن نہیں کی",
                "وکیل کی ضرورت نہیں — لیبر کورٹ میں خود بھی جا سکتے ہیں",
            ],
            "helplines": ["لیبر ہیلپ لائن: 042-99231530"],
        },
        "serious_salary_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "3 ماہ سے زیادہ تنخواہ نہ دینا سنگین قانونی خلاف ورزی ہے:",
            "action_steps": [
                "فوری لیبر کورٹ میں شکایت دائر کریں — آج ہی",
                "Payment of Wages Act 1936 کے تحت جرمانے کا دعویٰ کریں",
                "Industrial & Commercial Employment Ordinance 1968 کے تحت برطرفی کا دعویٰ بھی ممکن ہے",
                "EOBI کو شکایت کریں",
                "اگر آجر دھمکی دے: پولیس کو مطلع کریں",
                "لیبر کورٹ 24 ماہ تک کی تنخواہ بطور معاوضہ دلوا سکتی ہے",
            ],
            "helplines": ["لیبر ہیلپ لائن: 042-99231530", "EOBI: 021-99203444"],
        },
    },
},

# ───────────────────────────────────────────────────────────────────────────
"false_fir": {
    "title_ur": "میرے خلاف جھوٹی FIR درج ہوئی ہے",
    "title_en": "False FIR Filed Against Me",
    "icon": "📋",
    "steps": {
        "start": {
            "question_ur": "کیا آپ نے FIR کی کاپی حاصل کر لی ہے؟",
            "question_en": "Have you obtained a copy of the FIR?",
            "context_ur": "FIR کی کاپی آپ کا قانونی حق ہے — پولیس مفت دینے کی پابند ہے۔",
            "yes": "arrest_fear_check",
            "no": "get_fir_copy_terminal",
        },
        "get_fir_copy_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "پہلے FIR کی کاپی حاصل کریں:",
            "action_steps": [
                "تھانے سے FIR کی تصدیق شدہ کاپی مانگیں — یہ مفت ملنی چاہیے",
                "اگر پولیس انکار کرے: DSP کو درخواست دیں",
                "آن لائن چیک کریں: Punjab Safe Cities Authority پورٹل پر FIR نمبر سے",
                "کاپی ملنے پر وکیل کو دکھائیں",
            ],
            "helplines": ["پولیس: 15"],
        },
        "arrest_fear_check": {
            "question_ur": "کیا آپ کو ڈر ہے کہ پولیس جلد گرفتار کرے گی؟",
            "question_en": "Are you afraid the police will arrest you soon?",
            "context_ur": "گرفتاری سے پہلے Pre-Arrest Bail (ضمانت قبل از گرفتاری) لینا بہتر حکمت عملی ہے۔",
            "yes": "pre_arrest_bail_terminal",
            "no": "quash_fir_terminal",
        },
        "pre_arrest_bail_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "فوری ضمانت قبل از گرفتاری کے لیے اقدامات کریں:",
            "action_steps": [
                "آج ہی وکیل کریں — Pre-Arrest Bail کی درخواست سیشن کورٹ یا ہائی کورٹ میں دائر ہوگی",
                "FIR کی کاپی وکیل کو دیں",
                "ثابت کریں کہ آپ بھاگنے والے نہیں اور تحقیقات میں تعاون کریں گے",
                "ضمانت ملنے تک گھر پر رہیں — غیر ضروری سفر نہ کریں",
                "گواہوں سے رابطہ نہ کریں — یہ ضمانت منسوخی کی وجہ بن سکتا ہے",
            ],
            "helplines": ["قانونی امداد: 051-9207046"],
        },
        "quash_fir_terminal": {
            "terminal": True,
            "urgency": "within_week",
            "guidance_ur": "جھوٹی FIR کو قانونی طریقے سے چیلنج کریں:",
            "action_steps": [
                "ہائی کورٹ میں FIR کالعدم قرار دینے (Quash) کی درخواست دائر کریں",
                "ثبوت اکٹھے کریں کہ FIR جھوٹی ہے (گواہ، CCTV، موبائل ریکارڈ)",
                "FIR درج کرنے والے کے خلاف جھوٹی شکایت کا مقدمہ (دفعہ 182 PPC) درج کروا سکتے ہیں",
                "تحقیقاتی افسر کو تمام ثبوت دیں",
                "وکیل کے ذریعے SP کو تحریری شکایت دیں",
            ],
            "helplines": ["قانونی امداد: 051-9207046"],
        },
    },
},

# ───────────────────────────────────────────────────────────────────────────
"domestic_violence": {
    "title_ur": "گھریلو تشدد کا سامنا ہے",
    "title_en": "Facing Domestic Violence",
    "icon": "🛡️",
    "steps": {
        "start": {
            "question_ur": "کیا آپ ابھی محفوظ جگہ پر ہیں؟",
            "question_en": "Are you currently in a safe place?",
            "context_ur": "آپ کی حفاظت سب سے پہلے ہے۔",
            "yes": "violence_type_check",
            "no": "immediate_safety_terminal",
        },
        "immediate_safety_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "ابھی فوری اقدام کریں — آپ کی جان زیادہ اہم ہے:",
            "action_steps": [
                "فوری گھر سے نکلیں — پڑوسی، رشتہ دار، یا کسی محفوظ جگہ جائیں",
                "پولیس ہیلپ لائن: 15 — ابھی کال کریں",
                "خواتین ہیلپ لائن (پنجاب): 1043",
                "Dar-ul-Aman (سرکاری پناہ گاہ) جائیں — ہر ضلع میں موجود ہے",
                "AGHS: 042-35761999 — مفت قانونی اور نفسیاتی مدد",
            ],
            "helplines": ["پولیس: 15", "خواتین ہیلپ لائن: 1043", "AGHS: 042-35761999"],
        },
        "violence_type_check": {
            "question_ur": "کیا تشدد جسمانی ہے (مار پیٹ، زخم)؟",
            "question_en": "Is the violence physical (beating, injury)?",
            "context_ur": "جسمانی تشدد کے لیے طبی معائنہ اور FIR دونوں ضروری ہیں۔",
            "yes": "physical_violence_terminal",
            "no": "legal_options_terminal",
        },
        "physical_violence_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "جسمانی تشدد جرم ہے — فوری اقدامات کریں:",
            "action_steps": [
                "فوری ڈاکٹر سے معائنہ کروائیں اور Medico-Legal Certificate (MLC) لیں",
                "تصاویر کھینچیں — زخموں کا ثبوت محفوظ کریں",
                "تھانے میں FIR درج کروائیں — دفعہ 337 (زخم) یا 354 (عورت پر حملہ)",
                "Domestic Violence (Prevention and Protection) Act کے تحت Protection Order مانگیں",
                "خاندان کو مطلع کریں",
                "Dar-ul-Aman جائیں اگر گھر محفوظ نہیں",
            ],
            "helplines": ["پولیس: 15", "خواتین ہیلپ لائن: 1043", "Rozan: 051-2890505"],
        },
        "legal_options_terminal": {
            "terminal": True,
            "urgency": "within_24h",
            "guidance_ur": "نفسیاتی یا معاشی تشدد بھی قانونی جرم ہے:",
            "action_steps": [
                "فیملی کورٹ میں Protection Order کے لیے درخواست دیں",
                "اگر شادی شدہ ہیں: نفقہ (maintenance) کا دعویٰ کریں",
                "AGHS یا Rozan سے مفت قانونی مشورہ لیں",
                "ثبوت محفوظ کریں: پیغامات، گواہ، ریکارڈنگ",
                "Domestic Violence Act کے تحت magistrate سے رابطہ کریں",
            ],
            "helplines": ["AGHS: 042-35761999", "Rozan: 051-2890505", "خواتین ہیلپ لائن: 1043"],
        },
    },
},

# ───────────────────────────────────────────────────────────────────────────
"cyber_crime": {
    "title_ur": "آن لائن ہراسانی یا سائبر جرم",
    "title_en": "Online Harassment / Cyber Crime",
    "icon": "💻",
    "steps": {
        "start": {
            "question_ur": "کیا کوئی آپ کی جعلی سوشل میڈیا پروفائل بنا کر ہراساں کر رہا ہے؟",
            "question_en": "Is someone creating fake profiles or harassing you online?",
            "context_ur": "PECA 2016 کی دفعہ 20 کے تحت آن لائن ہراسانی جرم ہے۔",
            "yes": "fake_profile_terminal",
            "no": "other_cyber_check",
        },
        "fake_profile_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "جعلی پروفائل اور آن لائن ہراسانی PECA 2016 کے تحت جرم ہے:",
            "action_steps": [
                "تمام اسکرین شاٹس اور ثبوت محفوظ کریں",
                "FIA Cyber Crime Wing کو آن لائن شکایت کریں: complaint.fia.gov.pk",
                "FIA ہیلپ لائن: 1991 (24 گھنٹے)",
                "سوشل میڈیا پلیٹ فارم پر جعلی اکاؤنٹ رپورٹ کریں",
                "مقامی پولیس میں FIR بھی درج کروا سکتے ہیں",
                "Digital Rights Foundation: 0800-39393 (مفت مشورہ)",
            ],
            "helplines": ["FIA Cyber Crime: 1991", "Digital Rights: 0800-39393"],
        },
        "other_cyber_check": {
            "question_ur": "کیا کوئی آپ کی نجی تصاویر یا ویڈیو شیئر کر رہا ہے یا کر نے کی دھمکی دے رہا ہے؟",
            "question_en": "Is someone sharing or threatening to share your private images/videos?",
            "context_ur": "یہ PECA دفعہ 21 کے تحت سنگین جرم ہے — فوری اقدام ضروری ہے۔",
            "yes": "image_abuse_terminal",
            "no": "general_cyber_terminal",
        },
        "image_abuse_terminal": {
            "terminal": True,
            "urgency": "immediate",
            "guidance_ur": "یہ انتہائی سنگین جرم ہے — فوری اقدام کریں:",
            "action_steps": [
                "FIA Cyber Crime Wing: 1991 — ابھی کال کریں",
                "Digital Rights Foundation: 0800-39393 — خصوصی مدد",
                "تمام ثبوت (اسکرین شاٹ، URLs) محفوظ کریں",
                "کسی کو بتانے سے نہ ڈریں — یہ آپ کی غلطی نہیں",
                "FIA کیس درج کرنے کے بعد مواد ہٹوانے میں مدد کرتی ہے",
                "خاندان یا دوست سے مدد لیں",
            ],
            "helplines": ["FIA Cyber Crime: 1991", "Digital Rights: 0800-39393"],
        },
        "general_cyber_terminal": {
            "terminal": True,
            "urgency": "within_24h",
            "guidance_ur": "دیگر سائبر جرائم کے لیے:",
            "action_steps": [
                "ثبوت محفوظ کریں — اسکرین شاٹ، URLs، پیغامات",
                "FIA Cyber Crime Wing کو شکایت: complaint.fia.gov.pk یا 1991",
                "مقامی پولیس میں FIR بھی ممکن ہے",
                "بینک فراڈ ہو تو: فوری بینک کو مطلع کریں اور SBP کو شکایت کریں",
                "ہیکنگ: فوری پاس ورڈ تبدیل کریں اور FIA کو مطلع کریں",
            ],
            "helplines": ["FIA Cyber Crime: 1991"],
        },
    },
},

}


# ═══════════════════════════════════════════════════════════════════════════
# Engine functions
# ═══════════════════════════════════════════════════════════════════════════

def get_scenario_list() -> list[dict]:
    """Returns all available scenarios with metadata."""
    return [
        {
            "id":       scenario_id,
            "title_ur": data["title_ur"],
            "title_en": data["title_en"],
            "icon":     data["icon"],
        }
        for scenario_id, data in SCENARIOS.items()
    ]


def get_first_step(scenario_id: str) -> Optional[dict]:
    """Returns the first step of a scenario."""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return None
    step = scenario["steps"]["start"].copy()
    step["step_id"]    = "start"
    step["is_terminal"] = step.get("terminal", False)
    step["progress_pct"] = 10
    return step


def get_next_step(
    scenario_id: str,
    current_step_id: str,
    answer: str,  # "yes" | "no" | "unsure"
) -> Optional[dict]:
    """
    Given the current step and user's answer, returns the next step.
    'unsure' is treated as 'no' (cautious path).
    """
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return None

    current_step = scenario["steps"].get(current_step_id)
    if not current_step:
        return None

    # Treat unsure as no (cautious / more protective path)
    direction = "yes" if answer == "yes" else "no"
    next_step_id = current_step.get(direction)

    if not next_step_id:
        return None

    next_step = scenario["steps"].get(next_step_id)
    if not next_step:
        return None

    result = next_step.copy()
    result["step_id"]     = next_step_id
    result["is_terminal"] = result.get("terminal", False)

    # Calculate rough progress percentage
    all_steps   = list(scenario["steps"].keys())
    step_index  = all_steps.index(next_step_id) if next_step_id in all_steps else 0
    result["progress_pct"] = min(90, int((step_index / max(len(all_steps), 1)) * 100) + 10)

    return result


def get_step(scenario_id: str, step_id: str) -> Optional[dict]:
    """Returns a specific step by ID."""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return None
    step = scenario["steps"].get(step_id)
    if not step:
        return None
    result = step.copy()
    result["step_id"]     = step_id
    result["is_terminal"] = result.get("terminal", False)
    return result
