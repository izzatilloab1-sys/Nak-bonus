# 💰 So'm Bonus Bot

Telegram bot — foydalanuvchilar **so'm** balansini to'playdi: referal, vazifalar
(reklama kanaliga obuna), promokod orqali, va **Payme** orqali balansni to'ldiradi.

> Butun tizim **faqat so'm** bilan ishlaydi. Stars/bonus balans degan narsa yo'q.
> Barcha hisob-kitob bitta umumiy so'm balansga tushadi.

---

## 🧩 Imkoniyatlar

- 🌐 **Til tanlash** — boshida 🇺🇿 O'zbek / 🇷🇺 Rus
- 📱 **Ro'yxatdan o'tish** — faqat **«📱 Telefon raqamni yuborish»** tugmasi orqali
  (qo'lda yozilgan raqam qabul qilinmaydi; tugma orqali yuborish majburiy)
- 💰 **So'm balans** — bitta umumiy balans
- 👥 **Referal** — do'st taklif qilish (hammasi so'mda):
  - Yangi referal **ro'yxatdan o'tganda** egasiga darhol `REFERRAL_JOIN_BONUS` so'm
  - Referal **har bir vazifa bajarganda** egasiga `REFERRAL_TASK_BONUS` so'm —
    lekin faqat referal ro'yxatdan o'tganidan **3 kun** (`REFERRAL_WINDOW_DAYS`)
    ichida bajarsa. 3 kundan keyin egaga hech narsa bormaydi
  - Firibgarlikdan himoya: o'ziga referal bo'lmaydi
- 🎯 **Vazifalar** — reklama kanaliga obuna → so'm. Miqdorni admin belgilaydi
- 🚪 **Chiqib ketish nazorati** — vazifa bajarib **1 hafta** (`UNSUB_CHECK_DAYS`)
  ichida kanaldan chiqib ketsa, bonus **ikkala tomondan** qaytarib olinadi
  (referalning o'z mukofoti + egaga ketgan bonus). Egaga chiqib ketgan odamning
  **ID + username** bilan xabar boradi. Qaytib qo'shilib «✅ Tekshirish» bossa —
  bonus **tiklanadi**
- 📢 **Majburiy obuna** — botdan foydalanishdan oldin kanallarga obuna shart
- 🔗 **Avtomatik invite link + obunachi hisobi** — bot kanalга admin qilinganda
  o'zi invite link yaratadi; bot orqali nechta odam kirgan/chiqqanini sanaydi.
  Admin har kanal uchun **chegara** belgilaydi — bot orqali kirganlar shu songa
  yetganda adminга xabar keladi (kanal avtomatik o'chmaydi)
- 🎁 **Promokod** — admin yaratadi (so'm beradi), har akkaunt **bir marta** ishlatadi
- 💳 **Balansni to'ldirish — 3 usul** (hammasi admin paneldan sozlanadi):
  - **Payme** — avtomatik (Merchant API, JSON-RPC 2.0)
  - **Click** — avtomatik (SHOP API, Prepare/Complete, imzo tekshiruvi)
  - **Karta (avto)** — foydalanuvchi kartaga to'laydi, admin bitta tugma bilan tasdiqlaydi
- 🛠 **Admin panel** — statistika, vazifa/kanal/promokod, balans qo'shish, ban, broadcast
- 🚫 **Ban tizimi** — middleware orqali
- 💾 **Zaxira (backup)** — ma'lumotlar bazasini Telegram kanalga avtomatik tashlash:
  - 👥 Foydalanuvchilar fayli (id, username, telefon, ism) — CSV, **har kuni**
  - 💰 Balanslar fayli (id bo'yicha kimda qancha so'm) — CSV, **har kuni**
  - 🗄 To'liq backup (`.db` — hamma ma'lumot) — **buyruq bilan** (`/backup`)
  - Uchalasi ham admin paneldan **qo'lda** ham olinadi
- ⛔ **Pul yechish — hozircha o'chirilgan** (keyinroq qo'shiladi)

---

## 📦 O'rnatish

```bash
# 1. Virtual muhit
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Kutubxonalar
pip install -r requirements.txt

# 3. Sozlamalar
cp .env.example .env
# .env ni to'ldiring (pastga qarang)

# 4. Ishga tushirish (bot + Payme webhook bir process'da)
python -m bot.main
```

> `python -m bot.main` ham botni (polling), ham Payme webhook serverini
> (default `0.0.0.0:8080`) ishga tushiradi. Alohida ishga tushirish kerak bo'lsa:
> `python -m bot.webhook`.

---

## ⚙️ Sozlash (.env)

| O'zgaruvchi | Tavsif |
|-------------|--------|
| `BOT_TOKEN` | @BotFather'dan olingan token |
| `ADMIN_IDS` | Admin Telegram ID'lari, vergul bilan (`111,222`). Birinchisi — ega |
| `DB_URL` | SQLite manzili (default `sqlite+aiosqlite:///bonus_bot.db`) |
| `REFERRAL_JOIN_BONUS` | Referal ro'yxatdan o'tganda egasiga beriladigan so'm |
| `REFERRAL_TASK_BONUS` | Referal **har bir** vazifa bajargach egasiga beriladigan so'm (3 kun oynasi ichida) |
| `REFERRAL_TASK_THRESHOLD` | (eski — endi ishlatilmaydi) |
| `REFERRAL_WINDOW_DAYS` | Referal ro'yxatdan o'tgach necha kun ichida bajarsa egaga bonus boradi (default **3**) |
| `UNSUB_CHECK_DAYS` | Vazifa bajargach necha kun ichida chiqsa bonus qaytariladi (default **7**) |
| `MIN_TOPUP` | Minimal to'ldirish summasi (so'm). Default **1000** |
| `PAYME_MERCHANT_ID` | Payme kassa (merchant) ID |
| `PAYME_SECRET_KEY` | Payme Merchant kaliti (Basic Auth: `Paycom:KEY`) |
| `PAYME_CHECKOUT_URL` | Checkout bazaviy URL (prod: `https://checkout.paycom.uz`, test: `https://checkout.test.paycom.uz`) |
| `WEBHOOK_HOST` / `WEBHOOK_PORT` | Payme callback serveri host/port |
| `PAYME_ENDPOINT_PATH` | Payme endpoint yo'li (default `/payme`) |

> Telegram ID'ingizni bilish uchun [@userinfobot](https://t.me/userinfobot) ga yozing.

---

## 💳 To'lov tizimi (3 usul — admin paneldan sozlanadi)

Bot **3 xil** to'lov usulini qo'llaydi. Uchalasi ham **admin paneldan** boshqariladi:

`/admin` → **💳 To'lov sozlamalari**:
- Har usulni **🟢 yoqish / 🔴 o'chirish**
- Kalitlarni **bot ichidan** kiritish (`.env` tahrirlamasdan — DB'da saqlanadi,
  `.env`dan ustun turadi)

Foydalanuvchi **💳 Balansni to'ldirish** → summa → **faqat yoqilgan usullar**
tugma bo'lib chiqadi.

| Usul | Qanday ishlaydi | Admin kiritadi |
|------|-----------------|----------------|
| **Payme** | Checkout havolasi → Merchant API callback → avto | Merchant ID, Secret key |
| **Click** | To'lov havolasi → SHOP API (Prepare/Complete) → avto | Service ID, Merchant ID, Secret key |
| **Karta (avto)** | Kartaga to'laydi → adminга xabar → admin «✅ To'landi» bosadi | Karta raqami, egasi |

> Webhook endpointlar: Payme → `/payme`, Click → `/click` (bitta aiohttp
> serverда, HTTPS domenга ulanadi).

---

## 💳 Payme Merchant integratsiyasi

Bot **Payme Merchant API** (JSON-RPC 2.0) ni to'liq qo'llab-quvvatlaydi. Payme =
**balansni to'ldirish** uchun ishlatiladi.

**Oqim:**
1. Foydalanuvchi **💳 Balansni to'ldirish** → summa tanlaydi (yoki «✏️ Boshqa summa»).
2. Bot `Order` (PENDING) yaratadi va **Payme Checkout havolasi** beradi
   (`m`=merchant, `ac.order_id`=buyurtma, `a`=tiyin).
3. Foydalanuvchi Payme'da to'laydi.
4. Payme Merchant kabinetidan sizning serveringizga JSON-RPC so'rovlar keladi.
5. `PerformTransaction` muvaffaqiyatli bo'lganda balans **avtomatik** to'ldiriladi
   va foydalanuvchiga xabar boradi.

### Qo'llab-quvvatlanadigan metodlar

| Metod | Vazifasi |
|-------|----------|
| `CheckPerformTransaction` | Buyurtma mavjudligi, holati, summasi to'g'riligini tekshirish |
| `CreateTransaction` | Tranzaksiya yaratish (`state=1`), Payme tx ID saqlash |
| `PerformTransaction` | To'lovni yakunlash (`state=2`), balansni to'ldirish, userga xabar |
| `CancelTransaction` | Bekor qilish/qaytarish (`state=-1` / `-2` refund) |
| `CheckTransaction` | Tranzaksiya holati va vaqtlarini qaytarish |
| `GetStatement` | Berilgan oraliqdagi tranzaksiyalar ro'yxati |

### Xatolik kodlari

| Kod | Ma'nosi |
|-----|---------|
| `-32504` | Avtorizatsiya yetarli emas (Basic Auth xato) |
| `-32601` | Metod topilmadi |
| `-32700` | JSON o'qib bo'lmadi |
| `-31001` | Noto'g'ri summa |
| `-31003` | Tranzaksiya topilmadi |
| `-31007` | Buyurtmani bajarib bo'lmaydi (allaqachon to'langan/holat mos emas) |
| `-31008` | Tranzaksiyani bajarib bo'lmaydi (holat noto'g'ri) |
| `-31050` | Buyurtma (`ac.order_id`) topilmadi/noto'g'ri |

### Payme kabinetida sozlash
1. Payme merchant kabinetida **kassa** yarating.
2. **Endpoint URL**: `https://sizning-domen.uz/payme` (HTTPS majburiy).
3. `account` maydoni: **`order_id`** (bitta maydon).
4. Kalitni `.env` dagi `PAYME_SECRET_KEY` ga yozing.
5. Avval **test** muhitda sinang (`PAYME_CHECKOUT_URL=https://checkout.test.paycom.uz`).

> ⚠️ Idempotentlik: `PerformTransaction` va `CancelTransaction` qayta chaqirilsa
> balans **ikki marta** o'zgarmaydi — faqat birinchi holat o'tishida ta'sir qiladi.

---

## 👥 Referal va kanal nazorat tizimi

### Referal oqimi
1. Foydalanuvchi referal havolani bosadi → `/start ref<egasi_id>`
2. Til tanlaydi → telefon raqamini (tugma orqali) yuboradi → ro'yxatdan o'tadi
3. **Egaga darhol** `REFERRAL_JOIN_BONUS` so'm beriladi
4. (Majburiy obuna bo'lsa) foydalanuvchi kanallarga obuna bo'ladi
5. Foydalanuvchi vazifa bajarsa:
   - **o'zi** `task.reward` so'm oladi
   - **egasi** `REFERRAL_TASK_BONUS` so'm oladi — *agar referal ro'yxatdan
     o'tganidan 3 kun ichida bajarsa*. Har vazifa uchun alohida.
   - 3 kundan keyin bajarsa — referalning o'z mukofoti baribir beriladi, lekin
     egaga hech narsa bormaydi.

### Chiqib ketish nazorati (1 hafta)
- Bot kanalni **real vaqtda** (`chat_member`) + **har 6 soatda** (zaxira
  tekshiruv) kuzatadi.
- Vazifa bajarib 1 hafta ichida kanaldan chiqib ketsa → bonus **ikkala tomondan**
  (foydalanuvchi + ega) qaytarib olinadi.
- **Egaga xabar:** chiqib ketgan odamning **ID + username** va qaysi vazifani
  bajarib chiqib ketgani.
- **Tiklash:** foydalanuvchi qaytib qo'shilib «✅ Tekshirish» bossa, bonus
  ikkala tomonga qaytadan beriladi.
- 1 haftadan keyin chiqsa — bonus qaytarilmaydi (qotadi).

### Avtomatik invite link + obunachi hisobi
- Botni kanalga **admin** qiling → bot avtomatik **invite link** yaratadi
  (vazifa/majburiy kanal qo'shilganda ham darhol yaratiladi).
- Bot shu link orqali nechta odam **kirgan** / **chiqqan** / hozir **faol**
  ekanini sanaydi (admin panelda ko'rinadi).
- Har kanal uchun **chegara** (`sub_limit`) belgilanadi (qo'shishda so'raladi,
  0 = cheksiz).
- Bot orqali **kirganlar** soni chegaraga yetganda → **adminга xabar** keladi
  (chiqqanlar ayrilmaydi — jami kirgan sanaladi). Kanal avtomatik o'chmaydi,
  admin o'zi qaror qiladi.

> ⚙️ `chat_member` / `my_chat_member` update'lari bot polling'da avtomatik
> so'raladi (`allowed_updates`). Bot kanalда **admin** bo'lishi shart — aks
> holda obuna/chiqish kuzatilmaydi va invite link yaratilmaydi.

---

## 💾 Zaxira (backup) tizimi

Bot o'chib qolsa yoki server qayta o'rnatilsa ma'lumot yo'qolmasligi uchun baza
Telegram **kanalga** fayl ko'rinishida tashlanadi.

### Kanalni ulash
1. Telegram'da kanal yarating (yoki mavjudini oling).
2. Botni o'sha kanalga **admin** qiling (fayl yuborish huquqi bilan).
3. Botда: `/admin` → **💾 Backup** → **📢 Kanalni ulash** → kanal ID
   (`-100...`) yoki `@username` kiriting.

> Kanal `.env` orqali emas, bot ichidan ulanadi va DB'da (`settings`) saqlanadi.

### 3 xil zaxira

| Tur | Tarkibi | Format | Jadval |
|-----|---------|--------|--------|
| 👥 **Foydalanuvchilar** | id, username, telefon, ism, til, sana | CSV (UTF-8) | Har kuni 00:00 + qo'lda |
| 💰 **Balanslar** | id, username, balans (so'm) | CSV (UTF-8) | Har kuni 00:00 + qo'lda |
| 🗄 **To'liq backup** | butun baza — ipidan ignasigacha | `.db` fayl | Qo'lda (`/backup`) |

- **Avtomatik:** har kuni soat **00:00** (server vaqti) foydalanuvchilar va
  balanslar fayli kanalga yuboriladi.
- **Qo'lda:** `/admin` → **💾 Backup** bo'limidagi tugmalar orqali istalgan paytda;
  to'liq backup uchun `/backup` buyrug'i ham bor.

### Tiklash (restore)
To'liq backup `.db` faylini serverда bot papkasidagi `bonus_bot.db` o'rniga
qo'ying va botni qayta ishga tushiring — hamma ma'lumot (userlar, balanslar,
referal, vazifa, promokod, to'lovlar) tiklanadi.

> ⚙️ Texnik: to'liq backup `VACUUM INTO` orqali olinadi — bu ochiq (ishlayotgan)
> bazani buzmasdan toza, yaxlit nusxa yaratadi.

---

## 🖥 Serverда ishga tushirish (systemd)

```bash
# Kodni serverga joylang va venv yarating
cd /opt/som-bonus-bot
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env   # to'ldiring
```

`/etc/systemd/system/sombot.service`:

```ini
[Unit]
Description=Som Bonus Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/som-bonus-bot
ExecStart=/opt/som-bonus-bot/venv/bin/python -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sombot
sudo systemctl status sombot
journalctl -u sombot -f          # loglarni kuzatish
```

### Payme webhook uchun HTTPS (nginx namunasi)

Payme faqat **HTTPS** endpoint'ga so'rov yuboradi. nginx reverse-proxy:

```nginx
server {
    listen 443 ssl;
    server_name sizning-domen.uz;

    ssl_certificate     /etc/letsencrypt/live/sizning-domen.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sizning-domen.uz/privkey.pem;

    location /payme {
        proxy_pass http://127.0.0.1:8080/payme;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> Bot kanalların obunasini tekshira olishi uchun uni har bir **majburiy obuna** va
> **vazifa** kanaliga **admin** qiling.

---

## 📂 Tuzilma

```
som-bonus-bot/
├── bot/
│   ├── main.py                 # kirish nuqtasi (polling + Payme webhook)
│   ├── webhook.py              # Payme JSON-RPC server (aiohttp)
│   ├── config.py               # .env sozlamalari
│   ├── middlewares.py          # ban middleware
│   ├── database/
│   │   ├── models.py           # SQLAlchemy modellar
│   │   └── db.py               # DB funksiyalari (referal, Payme, ...)
│   ├── handlers/
│   │   ├── registration.py     # til + telefon raqam
│   │   ├── user.py             # menyu, balans, referal, majburiy obuna
│   │   ├── tasks.py            # vazifalar
│   │   ├── promo.py            # promokod
│   │   ├── topup.py            # balans to'ldirish (Payme link)
│   │   └── admin.py            # admin panel
│   ├── keyboards/              # user va admin tugmalari
│   ├── services/
│   │   ├── payme.py            # Payme Merchant JSON-RPC 2.0
│   │   ├── click.py            # Click SHOP API (Prepare/Complete)
│   │   ├── payment_settings.py # 3 usul sozlamalari (admin panel / DB)
│   │   ├── backup.py           # zaxira (CSV + to'liq .db) kanalga
│   │   ├── channel_tracker.py  # invite link, qo'shilish/chiqish, chegara xabari
│   │   ├── unsub_checker.py    # har 6 soatda chiqib ketganlarni tekshirish
│   │   └── subscription.py     # obuna tekshiruvi
│   └── utils/
│       ├── states.py           # FSM holatlar
│       └── texts.py            # uz/ru matnlar (i18n)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔐 Xavfsizlik

- `.env` ni **hech qachon** git'ga qo'shmang (`.gitignore` da).
- `PAYME_SECRET_KEY` sir — faqat serveringizda saqlang.
- Payme endpoint faqat **HTTPS** orqali ochiq bo'lsin.
- Vazifa/majburiy obuna ishlashi uchun botni kanallarга **admin** qiling.
