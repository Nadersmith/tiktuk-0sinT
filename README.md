# tiktuk-0sinT

مجموعة أدوات OSINT لأنشطة تحليل ملفات المستخدمين على TikTok باستخدام Python، مصممة للعمل على Kali Linux / Kali NetHunter / Termux. 

تتضمن المشروع عدة إصدارات:

- `tiktok_osint_pro.py` — النسخة الرئيسية والمتقدمة
- `tiktuk-osint.py` — نسخة مبسطة
- `pro.py` — أداة سريعة لاستخراج معلومات الملف من رابط كامل

## ما الذي يمكن للأداة جمعه؟

- اسم المستخدم
- اسم العرض
- السيرة الشخصية / bio
- التحقق (Verified)
- عدد المتابعين
- عدد الإعجابات
- رابط الصورة/الملف الشخصي
- الروابط الخارجية في السيرة
- البريد الإلكتروني إن وُجد
- رقم الهاتف إن وُجد
- الموقع الشخصي/الويب إن وُجد
- دعم حفظ النتائج بصيغة JSON / CSV / HTML
- دعم استخدام Tor أو Proxy
- دعم التحليل المجمع لعدد من المستخدمين

---

## بنية المشروع

```bash
.
├── README.md
├── pro.py
├── tiktok_osint_pro.py
├── tiktuk-osint.py
├── osint_cache.db          # ينشئ تلقائياً عند التشغيل
├── osint_logs.txt          # سجل التشغيل
└── results.json            # مثال لملف خرج إن تم حفظه
```

---

## متطلبات التشغيل

### 1) تثبيت Python والاعتمادات

```bash
sudo apt update
sudo apt install python3 python3-pip python3-bs4 python3-colorama -y
pip3 install requests PySocks
```

إذا كنت تستخدم Tor، تأكد من تشغيل الخدمة:

```bash
sudo service tor start
```

---

## النسخة الرئيسية: tiktok_osint_pro.py

### استخدام حساب واحد

```bash
python3 tiktok_osint_pro.py -u username
```

### استخدام ملف يحتوي أسماء مستخدمين

```bash
python3 tiktok_osint_pro.py -f usernames.txt
```

### حفظ النتيجة بصيغة JSON

```bash
python3 tiktok_osint_pro.py -u username -o report.json
```

### حفظ النتيجة بصيغة CSV

```bash
python3 tiktok_osint_pro.py -u username -o report.csv
```

### إنشاء تقرير HTML

```bash
python3 tiktok_osint_pro.py -u username --html report.html
```

### استخدام Proxy

```bash
python3 tiktok_osint_pro.py -u username -p http://127.0.0.1:8080
```

### استخدام Tor

```bash
python3 tiktok_osint_pro.py -u username --tor
```

### تعطيل التخزين المؤقت

```bash
python3 tiktok_osint_pro.py -u username --no-cache
```

### مثال كامل

```bash
python3 tiktok_osint_pro.py -f usernames.txt -o report.json --html report.html --tor -v
```

---

## النسخة المبسطة: tiktuk-osint.py

### استخدام حساب واحد

```bash
python3 tiktuk-osint.py -u username
```

### إنشاء تقرير HTML

```bash
python3 tiktuk-osint.py -u username -r
```

### استخدام Proxy

```bash
python3 tiktuk-osint.py -u username -p 127.0.0.1:8080
```

### استخدام Tor

```bash
python3 tiktuk-osint.py -u username -t
```

---

## أداة الرابط الكامل: pro.py

هذه النسخة مناسبة عندما يكون لديك رابط كامل لملف شخصي بدلاً من اسم المستخدم فقط.

```bash
python3 pro.py -u "https://www.tiktok.com/@username"
```

### خياراته

```bash
python3 pro.py --help
```

### مثال حفظ النتيجة

```bash
python3 pro.py -u "https://www.tiktok.com/@username" -o result.json
```

### استخدام Proxy

```bash
python3 pro.py -u "https://www.tiktok.com/@username" -p http://127.0.0.1:8080
```

### استخدام Tor

```bash
python3 pro.py -u "https://www.tiktok.com/@username" --tor
```

---

## ملاحظات حول الأداء

- توجد قاعدة بيانات SQLite (`osint_cache.db`) لتخزين النتائج مؤقتًا وتجنب الطلبات المكررة.
- يوجد ملف `osint_logs.txt` لتسجيل الأخطاء والمعاملات.
- بعض الصفحات على TikTok قد تكون محمية أو تتطلب جلسة متقدمة، لذلك قد تختلف النتائج حسب الموقع والطلب.
- استخدام Tor أو Proxy قد يساعد في الحفاظ على الخصوصية، لكنه لا يضمن الوصول الكامل إلى كل صفحة.

---

## مثال مخرجات JSON

```json
[
  {
    "username": "exampleuser",
    "display_name": "Example User",
    "bio": "Content creator",
    "verified": true,
    "followers": 12345,
    "likes": 98765,
    "avatar_url": "https://example.com/avatar.jpg",
    "social_links": [
      {
        "text": "Website",
        "url": "https://example.com"
      }
    ],
    "emails": ["user@example.com"],
    "phones": ["+966500000000"],
    "scraped_at": "2026-10-03T12:00:00"
  }
]
```

---

## تنبيه قانوني وخصوصية

تُستخدم هذه الأدوات فقط للأغراض التالية:

- اختبار الأمان المسموح به
- Bug Bounty في البيئات المصرح لها
- Red Team داخل النطاق المصرح به
- جمع بيانات OSINT مفتوحة بشكل قانوني

لا تستخدم هذه الأدوات:

- في التجسس أو مراقبة الأفراد دون إذن
- في الوصول إلى بيانات خاصة أو محظورة
- في أي نشاط غير قانوني أو غير مصرح به

---

## ملاحظات

- هذا المشروع يُستخدم لأغراض تعليمية وتجريبية فقط.
- قد تحتاج بعض البيئات إلى تعديل إعدادات الـ User-Agent أو Proxy أو headers حسب موقع TikTok.
- إذا كانت الصفحة تُعيد HTML غير كامل أو محجوب، فقد يتطلب الأمر تحديثات مستقبلية في استخراج البيانات.

---

## الاستخدام السريع

```bash
# النسخة المتقدمة
python3 tiktok_osint_pro.py -u username -o result.json --tor

# أداة الرابط الكامل
python3 pro.py -u "https://www.tiktok.com/@username" -o result.json
```

إذا رغبت، أستطيع أيضاً تحديث ملف README ليصبح مزودًا بـ "Quick Start" مختصر ونسخة باللغة الإنجليزية فقط أو إضافة قسم Screenshots / Examples.
