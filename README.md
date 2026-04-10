# tiktuk-0sinT
 
**أداة متقدمة مخصصة لـ TikTok OSINT** في Kali NetHunter (Termux أو Kali Desktop) تعمل باللغة الإنجليزية، مع **أوامر CLI جاهزة** وبدون أخطاء.

 **أداة مطورة بالكامل** تُسمّى **`tiktok_osint_advanced.py`**، تعمل مباشرة في Kali 
 
- **معلومات حسابية**:
  - Username, UID  
  - Followers  
  - Likes  
  - Videos  
  - Creation Date  
  - Region  
  - Language  
  - Interactive Videos (Videos, Likes, Shares)  

- **OSINT بيانات مفتوحة**:
  - Email  
  - Phone Number  
  - Website / Personal Link  

***

### 1. كيف تُجمع البيانات من TikTok؟

الصناعة الداخلية للـ TikTok تحتوي على:
- **HTML + JS** (Rich DOM)
- **APIs** (GraphQL / internal API)
- **Structured Data** (JSON inside HTML)

الأداة ستستخدم **Python + requests + BeautifulSoup + re** لجمع البيانات من:
- `https://www.tiktok.com/@username` (الصفحة العامة)

***

### 2. أوامر CLI جاهزة للعمل في Kali

#### 2.1 تثبيت المتطلبات أول مرة

```bash
sudo apt update
sudo apt install python3-pip python3-colorama python3-bs4 requests -y
```

***

#### 2.2 تنزيل/إنشاء الأداة

```bash
# احفظ الكود في: tiktok_osint_advanced.py
nano tiktok_osint_advanced.py
```

ارفع محتوى الأداة (الكود سيكون مكتوبًا في خطوة 4).

***

#### 2.3 جعل الأداة قابلة للتنفيذ

```bash
chmod +x tiktok_osint_advanced.py
```

***

### 3. أوامر CLI جاهزة للاستخدام

#### 3.1 فحص حساب واحد مع تفصيل النتائج

```bash
python3 tiktok_osint_advanced.py -u selcherbny -v
```

- `-u selcherbny` – اسم المستخدم في TikTok  
- `-v` – تفصيل النتائج (Verbose)

سيظهر لك:

```text
Username: selcherbny
UID: 123456789 (إن وُجد)
Followers: 12000
Likes: 85000
Videos: 150
Creation Date: 2022-01-15
Region: Amman, Jordan
Language: English
Interactive Videos: 80
Email: selcherbny@gmail.com
Phone: +96278xxxxxxx
Website: https://example.com/contact
```

***

#### 3.2 حفظ النتائج في JSON

```bash
python3 tiktok_osint_advanced.py -u selcherbny -o selcherbny_result.json -v
```

- `-o selcherbny_result.json` – حفظ في JSON  
- `-v` – تفصيل النتائج

***

#### 3.3 استخدام Tor للحماية من التتبع

```bash
python3 tiktok_osint_advanced.py -u selcherbny --tor
```

- `--tor` – استخدام Tor SOCKS5 (`127.0.0.1:9050`)

***

#### 3.4 استخدام Proxy (Burp Suite أو أي Proxy)

```bash
python3 tiktok_osint_advanced.py -u selcherbny -v -p 127.0.0.1:8080
```

- `-p 127.0.0.1:8080` – استخدام proxy  
- `-v` – تفصيل النتائج


### 5. كيف تستخدم الأداة في Bug Bounty أو Red Team

- **Bug Bounty**:
  - استخدم `tiktok_osint_advanced.py` لجمع بيانات مفتوحة (OSINT) عن حسابات TikTok.
- **Red Team**:
  - استخدم Tor أو Proxy لجمع بيانات مخفية.
  - استخدم الأداة مع Burp Suite لتحليل requests.

***

### 6. ملاحظة قانونية وخصوصية

- استخدم هذه الأداة فقط في:
  - Bug Bounty مسموح.
  - اختبار أمني/Red Team على مساحات مسموح بها.
- لا تستخدمها لجمع بيانات مخترِقة أو لمراقبة أفراد بدون إذن.


