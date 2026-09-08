# بطاقة تعريف المستودع — eFootball Competitive Platform

> **الغرض من هذا الملف:** مرجع تأسيسي قابل للنسخ والإرسال إلى أي أداة ذكاء اصطناعي حتى تفهم هوية المشروع، معماريته، نطاقه الحالي، مرحلة التطوير، وطريقة التعامل معه قبل اقتراح أو تنفيذ أي تغيير.
>
> **آخر تحديث:** 2026-09-08

## 1. الهوية المختصرة

- **اسم المشروع:** eFootball Competitive Platform
- **الاسم التسويقي الظاهر في الواجهة:** eFootball Arena
- **النوع:** منصة تنافسية اجتماعية للاعبي eFootball.
- **المستودع:** `Anwarefahmi22/efootball-competitive-platform`
- **الفرع الأساسي:** `main`
- **الهدف:** جمع هوية اللاعب، البطولات، المباريات، الترتيب، التحقق من النتائج، الثقة، المجتمع، والاقتصاد داخل منصة واحدة.
- **لغة المنتج الحالية:** الواجهات عربية RTL، بينما أسماء الملفات والكود والتعليقات الأساسية باللغة الإنجليزية.
- **حالة المنتج:** MVP/نموذج أولي متقدم قيد البناء، وليس منتجًا إنتاجيًا مكتملًا.

## 2. الحالة والمرحلة الحالية

المشروع بدأ بخطة من ثماني مراحل، وتذكر الوثائق أن المرحلة الأولى هي **Core Identity / Player Identity**: المستخدمون، الملفات الشخصية، التسجيل، تسجيل الدخول، وJWT. لكن المستودع الحالي تجاوز هذا الوصف فعليًا؛ إذ يحتوي الكود والترحيلات على محركات المنافسة والتحقق والثقة والمجتمع والاقتصاد والمواسم ونظام المجموعات والإقصائيات.

لذلك يجب فهم الوضع الحالي بهذه الصيغة:

1. **الهوية والمصادقة:** موجودة ومتصلة بالـAPI.
2. **محرك البطولات والمباريات:** موجود بكود ونماذج وترحيلات متعددة، ويشمل single elimination وleague وgroup knockout.
3. **التحقق والأدلة والنزاعات:** موجود، بما في ذلك رفع الأدلة وتأكيد النتيجة وفتح النزاع وحله.
4. **التقييم والثقة ومكافحة الغش:** موجودة على مستوى النماذج والخدمات والـAPI.
5. **المجتمع:** منشورات، إعجابات، تعليقات، ومتابعة.
6. **الاقتصاد:** محافظ، معاملات، إيداعات، وطلبات سحب.
7. **المواسم والتحليلات:** موجودة في الـAPI والنماذج.
8. **تطبيق Android:** مخطط له مستقبلًا، ولا توجد حاليًا قاعدة تطبيق Android فعلية؛ الموجود README فقط.

هذه ليست إشارة إلى أن كل هذه الأجزاء جاهزة للإنتاج أو مغطاة اختباريًا؛ هي إشارة إلى أن هيكلها البرمجي موجود داخل الفرع الحالي.

## 3. بنية المستودع

```text
/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # مسارات HTTP
│   │   ├── core/            # منطق المجال والخدمات المساعدة
│   │   ├── db/              # Base وAsyncSession
│   │   ├── models/          # نماذج SQLAlchemy
│   │   ├── schemas/         # نماذج Pydantic للطلب والاستجابة
│   │   └── main.py          # إنشاء تطبيق FastAPI وCORS
│   ├── alembic/versions/    # ترحيلات قاعدة البيانات 001 إلى 011
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── landing/index.html   # الصفحة التسويقية
│   ├── web/auth.html        # التسجيل وتسجيل الدخول
│   ├── web/app/             # dashboard/profile/ratings/tournaments
│   └── shared/              # theme.css وapi.js وnav.js
├── android/                 # خطة مستقبلية، ليس تطبيقًا مكتملًا
├── docs/
│   ├── ARCHITECTURE.md
│   └── REPOSITORY_IDENTITY.md
├── docker-compose.yml
└── README.md
```

## 4. التقنية والتشغيل

### Backend

- Python 3.11+
- FastAPI 0.115.6
- Uvicorn
- SQLAlchemy 2.x بنمط async
- asyncpg
- PostgreSQL 16
- Alembic 1.14
- Pydantic v2 وPydantic Settings
- `python-jose` لـJWT
- `passlib` وbcrypt لتجزئة كلمات المرور
- `python-multipart` للطلبات متعددة الأجزاء ورفع الملفات

### Frontend

- HTML/CSS/JavaScript خام بدون إطار عمل أو bundler.
- واجهة RTL عربية.
- `frontend/shared/api.js` هو عميل API المشترك.
- التوكنات تحفظ حاليًا في `localStorage`.

### Docker

يعرّف `docker-compose.yml` ثلاث خدمات:

- `db`: PostgreSQL 16 على المنفذ `5432`.
- `api`: يبني من `backend/Dockerfile`، يشغل `alembic upgrade head` ثم Uvicorn على `8000`.
- `web`: Nginx يخدم `frontend/web` على `8080`.

التدفق المحلي المتوقع:

```text
المتصفح :8080
    │
    └── JavaScript fetch
            │
            └── FastAPI :8000/api/v1
                    │
                    └── PostgreSQL :5432
```

ملف البيئة المطلوب هو `backend/.env` اعتمادًا على `backend/.env.example`. لا ينبغي تضمين أسرار حقيقية في المستودع. المتغيرات الأساسية هي:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`

## 5. طبقات الـBackend

### نقطة الدخول

`backend/app/main.py` ينشئ تطبيق FastAPI بعنوان المشروع وإصداره `0.1.0`، يفعّل CORS، ثم يركب كل المسارات تحت:

```text
/api/v1
```

يوجد أيضًا:

```text
GET /health
```

ويرجع:

```json
{"status": "ok"}
```

### المصادقة والهوية

`backend/app/api/v1/auth.py` يوفر:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

الآلية الحالية:

- التسجيل يتطلب email وpassword بطول 8 إلى 128 وdisplay name بطول 2 إلى 100.
- كلمة المرور لا تخزّن كنص صريح؛ تستخدم bcrypt.
- يتم إصدار access token وrefresh token بصيغة JWT.
- نوع التوكن موجود في claim باسم `type` وقيمته `access` أو `refresh`.
- هوية المستخدم موجودة في claim باسم `sub`.
- مدة access token الافتراضية 30 دقيقة.
- مدة refresh token الافتراضية 7 أيام.
- `get_current_user` يتحقق من التوقيع والنوع ووجود المستخدم وكونه فعالًا.

النماذج الأساسية:

- `User`: البريد، الهاتف، كلمة المرور المجزأة، الاسم، التفعيل، التحقق، التواريخ.
- `Profile`: الصورة، النبذة، البلد، واسم اللاعب داخل eFootball.

### محرك البطولات

المسارات الرئيسية في `tournaments.py`:

- إنشاء واستعراض وعرض وتعديل البطولات.
- إلغاء البطولة.
- standings وgroups.
- الانضمام والمغادرة.
- قبول أو رفض مشارك عند تفعيل الموافقة.
- تنفيذ القرعة.
- بدء البطولة.
- بدء مرحلة knockout.

الصيغ المعرفة:

- `single_elimination`
- `league`
- `group_knockout`

الحالات المعرفة تشمل:

- `draft`
- `registration_open`
- `registration_closed`
- `in_progress`
- `completed`
- `cancelled`

النموذج يدعم رسوم الدخول، الجوائز، توزيع الجائزة، الموافقة على المشاركين، عدد المجموعات، الموسم، الفائز، المنشئ، ووقت البداية.

### المباريات والنتائج والأدلة

`matches.py` يوفر:

- قراءة مباراة أو مباريات بطولة.
- إرسال نتيجة.
- قراءة الأدلة.
- عرض صورة الدليل.
- تأكيد النتيجة.
- فتح نزاع.
- حل النزاع.

حالات المباراة:

- `waiting`
- `ready`
- `in_progress`
- `result_submitted`
- `disputed`
- `completed`
- `cancelled`

كل مباراة تحمل `round_number` و`bracket_slot`. يجب استخدام `bracket_slot` لترتيب التقدم في bracket؛ لا ينبغي الاعتماد على `created_at` أو UUID لأنهما غير حتميين لهذا الغرض.

### التقييم والثقة ومكافحة الغش

- `ratings.py`: leaderboard وتقييم لاعب.
- `trust.py`: عرض درجة ثقة اللاعب.
- `fraud.py`: كشف المرشحين للتواطؤ عبر `collusion-candidates`.
- `core/rating.py` و`core/trust.py` و`core/analytics.py`: منطق المجال المرتبط بهذه الميزات.

### المجتمع

`posts.py` يوفر:

- إنشاء المنشورات.
- قائمة المنشورات وقراءة منشور.
- قراءة صورة المنشور.
- الإعجاب وإلغاء الإعجاب.
- إضافة التعليقات وقراءة التعليقات.

`social.py` يوفر:

- متابعة لاعب.
- إلغاء المتابعة.
- إحصاءات المتابعة.

### الاقتصاد

`economy.py` يوفر:

- محفظة المستخدم الحالية.
- معاملات المحفظة.
- قراءة محفظة مستخدم.
- إيداع.
- إنشاء طلب سحب.
- قائمة طلبات السحب.
- قبول أو رفض طلب السحب.

النماذج الأساسية هي `Wallet` و`Transaction` و`WithdrawalRequest`. يجب التعامل مع هذه المنطقة على أنها حساسة ماليًا، وعدم تغيير منطق الأرصدة أو الصلاحيات دون مراجعة المعاملات الذرية وسجل التدقيق.

### المواسم والتحليلات

- `seasons.py`: إنشاء الموسم، قائمة المواسم، قراءة موسم، standings.
- `analytics.py`: تحليلات المنصة، تحليلات لاعب، تحليلات بطولة.

## 6. نماذج البيانات الحالية

نماذج SQLAlchemy الموجودة في `backend/app/models/`:

| المجال | النماذج |
|---|---|
| الهوية | `User`, `Profile` |
| البطولات | `Tournament`, `TournamentParticipant` |
| المباريات | `Match`, `MatchEvidence` |
| المجموعات | `Group` |
| التقييم | `PlayerRating` |
| الثقة | `PlayerTrust` |
| المجتمع | `Post`, `Comment`, `PostLike`, `Follow` |
| الاقتصاد | `Wallet`, `Transaction`, `WithdrawalRequest` |
| المواسم | `Season` |

جميع هذه النماذج تعتمد UUID كمفاتيح أساسية، وPostgreSQL كقاعدة بيانات مستهدفة، مع علاقات وقيود unique وforeign keys مناسبة للمجالات الأساسية.

## 7. تاريخ قاعدة البيانات

سلسلة Alembic الحالية خطية من `001` إلى `011`:

1. `001_create_users_and_profiles`: المستخدمون والملفات.
2. `002_competition_engine`: محرك المنافسة.
3. `003_verification_engine`: التحقق والأدلة.
4. `004_trust_fraud_engine`: الثقة ومكافحة الغش.
5. `005_community_engine`: المجتمع.
6. `006_economy_engine`: الاقتصاد.
7. `007_draw_system`: نظام القرعة.
8. `008_seasons`: المواسم.
9. `009_participant_approval`: موافقة المشاركين.
10. `010_group_knockout`: المجموعات والأدوار الإقصائية.
11. `011_tournament_winner`: تخزين فائز البطولة.

عند إضافة تغيير على schema يجب إنشاء migration جديدة بدل تعديل migrations مطبقة سابقًا.

## 8. الواجهة الحالية

الصفحات الموجودة:

- `frontend/landing/index.html`: صفحة تعريف وتسويق باللغة العربية.
- `frontend/web/auth.html`: المصادقة.
- `frontend/web/app/dashboard.html`: لوحة التحكم.
- `frontend/web/app/profile.html`: الملف الشخصي.
- `frontend/web/app/ratings.html`: التقييمات.
- `frontend/web/app/tournaments.html`: البطولات.

`frontend/shared/api.js`:

- يحدد API base على `http://localhost:8000/api/v1`.
- يرسل Authorization Bearer تلقائيًا.
- يحاول تجديد access token مرة واحدة عند 401 باستخدام refresh token.
- يحفظ access وrefresh tokens في `localStorage`.
- يعرض رسائل أخطاء عربية مناسبة للواجهة.

## 9. قواعد مهمة لأي أداة ذكاء اصطناعي

عند تعديل المستودع:

1. افحص الملفات المرتبطة بالميزة قبل الكتابة؛ لا تفترض أن README يعكس كامل الكود الحالي.
2. حافظ على بنية FastAPI الحالية: router ثم schema ثم model ثم core/db عند الحاجة.
3. استخدم SQLAlchemy async ولا تضف استدعاءات synchronous إلى مسار الطلب.
4. أضف migration لأي تغيير في قاعدة البيانات.
5. حافظ على UUID وPostgreSQL وأنماط العلاقات الحالية.
6. لا تضع أسرارًا أو كلمات مرور أو JWT secrets داخل الكود أو ملفات commit.
7. لا تغيّر صلاحيات الاقتصاد أو حل النزاعات أو تقدم bracket دون فحص أثر التغيير على الحالات الحالية.
8. استخدم استجابات Pydantic الموجودة بدل إعادة تعريف نماذج متكررة.
9. حافظ على RTL واللغة العربية في واجهة المستخدم.
10. اجعل تغييرات الواجهة متوافقة مع `shared/api.js` ونظام التوكن الحالي، أو وثّق بوضوح أي انتقال.
11. لا تعتبر وجود endpoint دليلًا على اكتمال الميزة؛ تحقق من الصلاحيات، الحالات، المعاملات، migration، والاختبارات.
12. لا تحذف تغييرات محلية غير مرتبطة بالمهمة.

## 10. نواقص ومخاطر معروفة يجب أخذها في الاعتبار

هذه النقاط تصف حالة المستودع ولا تعني تلقائيًا أن المطلوب هو إصلاحها الآن:

- README و`docs/ARCHITECTURE.md` متأخران عن اتساع الكود؛ يلزم توحيد وثائق المرحلة.
- لا يظهر في الجذر نظام frontend حديث أو package manager؛ الواجهة static HTML/JS.
- تطبيق Android غير منفذ فعليًا بعد.
- التوكنات محفوظة في `localStorage`، وهو قرار يحتاج مراجعة أمنية قبل الإنتاج.
- CORS مضبوط حاليًا لعناوين localhost محددة.
- Docker يستخدم قيم تطوير واضحة؛ يجب تغيير كلمات مرور PostgreSQL وJWT secret في أي بيئة حقيقية.
- لا ينبغي اعتبار `dev-secret-change-in-production` إعدادًا صالحًا للإنتاج.
- يجب التأكد من وجود اختبارات آلية كافية قبل توسيع محركات البطولات والاقتصاد والثقة.
- رفع الملفات والأدلة يحتاج مراجعة حدود الحجم، نوع الملف، التخزين، والصلاحيات قبل الإنتاج.

## 11. تعريف النجاح في المرحلة الحالية

يُعتبر المشروع في حالة MVP قابلة للتجربة عندما يمكن:

1. تشغيل PostgreSQL وAPI وweb عبر Docker Compose.
2. تنفيذ migrations حتى revision `011`.
3. تسجيل مستخدم وتسجيل الدخول وتجديد التوكن.
4. عرض وتحديث الملف الشخصي.
5. إنشاء بطولة والانضمام إليها وإدارتها.
6. توليد مباريات وإرسال النتائج وتأكيدها أو فتح نزاع وحله.
7. قراءة التقييم والثقة والمحتوى الاجتماعي والمحفظة عبر الصلاحيات الصحيحة.
8. الوصول إلى كل ذلك من صفحات الويب الموجودة.

أما الجاهزية الإنتاجية فتتطلب، بالإضافة إلى ذلك، اختبارات شاملة، إدارة أسرار، مراقبة، سجلات تدقيق، حماية رفع الملفات، سياسة صلاحيات واضحة، ومراجعة أمنية وأداء.

## 12. Prompt جاهز لإرساله إلى أداة ذكاء اصطناعي

انسخ النص التالي مع المستودع أو قبله:

```text
أنت تعمل على مستودع اسمه eFootball Competitive Platform، وهو monorepo لمنصة تنافسية اجتماعية للاعبي eFootball. الهدف طويل المدى هو دعم هوية اللاعب، الملفات الشخصية، البطولات، المباريات، الترتيب، التحقق من النتائج، الثقة ومكافحة الغش، المجتمع، البث/الميزات الحية، والاقتصاد.

التقنية الحالية:
- Backend: Python 3.11+ وFastAPI وSQLAlchemy 2 async وPostgreSQL 16 وAlembic وPydantic v2.
- Auth: JWT access/refresh tokens مع bcrypt.
- Frontend: HTML/CSS/JavaScript خام، واجهة عربية RTL، وNginx.
- التشغيل المحلي: Docker Compose بخدمات db على 5432، api على 8000، web على 8080.

بنية المستودع:
- backend/app/api/v1 للمسارات.
- backend/app/core لمنطق المجال.
- backend/app/models لنماذج SQLAlchemy.
- backend/app/schemas لنماذج Pydantic.
- backend/alembic/versions لترحيلات قاعدة البيانات.
- frontend/landing للصفحة التسويقية.
- frontend/web/auth.html للمصادقة وfrontend/web/app لصفحات التطبيق.
- android حاليًا خطة مستقبلية فقط وليس تطبيقًا مكتملًا.

المرحلة الحالية:
الوثائق الأصلية تصف Phase 1 بأنها Core Identity، لكن الكود الحالي تجاوزها ويحتوي فعليًا على الهوية، البطولات، المباريات، الأدلة والنزاعات، التقييم، الثقة، مكافحة الغش، المجتمع، الاقتصاد، المواسم، التحليلات، المجموعات والإقصائيات. آخر migration هي 011_tournament_winner. اعتبر المشروع MVP متقدمًا قيد البناء، وليس نظامًا إنتاجيًا مكتملًا.

المجالات الموجودة:
- User/Profile وregister/login/refresh/me.
- Tournaments بصيغ single_elimination وleague وgroup_knockout.
- Matches مع submit-result وconfirm وdispute وresolve-dispute وevidence.
- Ratings وtrust وfraud analytics.
- Posts/comments/likes/follows.
- Wallet/transactions/deposits/withdrawals.
- Seasons وplatform/player/tournament analytics.

قواعد العمل:
1. اقرأ الملفات المرتبطة قبل التعديل ولا تعتمد على README وحده.
2. استخدم async SQLAlchemy والـschemas والـrouters الموجودة.
3. أنشئ migration جديدة لأي تغيير في schema.
4. حافظ على UUID وPostgreSQL وRTL.
5. لا تضع أسرارًا في الكود؛ قيم Docker الحالية تطويرية فقط.
6. راجع الصلاحيات وحالات الحالة والمعاملات الذرية، خصوصًا الاقتصاد والنزاعات والبطولات.
7. لا تعتبر endpoint موجودًا دليلًا على اكتمال الميزة.
8. نفّذ أصغر تغيير صحيح، ثم شغّل الاختبارات/الفحوص الموجودة.
9. إذا كان الطلب غامضًا أو يغيّر قرارًا معماريًا كبيرًا، اسأل قبل التنفيذ.
```
