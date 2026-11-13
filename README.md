# Stream Automation & Task Manager

Avtomatlashtirilgan video vazifalarini bajarish va monitoring qilish uchun yengil va qulay skript.

## Imkoniyatlari:
* ⚡ **Hududiy tarmoq (Tier 1) nazorati:** Yuqori stavkali hududiy tarmoq yoqilganligini avtomatik tekshiradi va nazorat qiladi.
* 📶 **Barqaror ulanish:** Internet uzilishi yoki MB tugashida xatoliksiz avtomatik kutish va tiklanish tizimi.
* 📱 **Termux va Android qo'llab-quvvatlash:** QR-kod orqali qulay va tezkor tizimga kirish (avtomatik galereyaga saqlash bilan).
* 📊 **Jonli Status Paneli:** Uptime, daromad, joriy balans va ko'rish jarayonining real vaqtdagi grafik ko'rsatkichlari.

## Termuxda 1 ta buyruq bilan ishga tushirish:

Termux terminalida quyidagi buyruqni kiriting:

```bash
pkg update -y && pkg install -y git python clang && git clone <REPO_URL> stream && cd stream && bash setup_termux.sh
```

*(O'rnatilgandan so'ng qayta ishga tushirish uchun:)*
```bash
cd stream
python main.py
```

## Sozlash:
Birinchi marta ishga tushirilganda dastur sizdan Telegram API ma'lumotlarini (`APP_ID` va `APP_HASH`) so'raydi va avtomatik tarzda `.env` faylini yaratadi.
