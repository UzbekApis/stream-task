# VidiPay Mobile & Termux Auto-Earner (MrBeast Videos)

MrBeast videolarini avtomatik tomosha qilish orqali VidiPay platformasidan pul yig'uvchi to'liq avtomatlashtirilgan bot.

## Imkoniyatlari:
* ⚡ **Tier 1 (AQSH) VPN nazorati:** Agar telefonda Tier 1 (AQSH) VPN yoqilmagan bo'lsa, past stavkada ishlab zarar ko'rmaslik uchun bot ishlamay kutib turadi. VPN yoqilishi bilan darhol maksimal stavkada ($0.0023/s ~ $8.28/soat) ishlab ketadi.
* 📶 **Internet uzilishidan himoya:** MB tugasa yoki internet uzilsa, to'xtamaydi — internet ulanguncha kutib, ulangach avtomatik davom etadi.
* 📱 **Termux va Android uchun optimallashtirilgan:** QR-kod avtomatik tarzda telefon galereyasiga saqlanadi (`/sdcard/DCIM/vidipay_login_qr.png`).
* 📊 **Real-time Jonli Dashboard:** Ishlash vaqti (uptime), hozirgi balans, shu sessiyada ishlangan daromad, daromad stavkasi va video tomosha progressi.

## Termuxda 1 ta buyruq bilan o'rnatish:
Termux ilovasini oching va quyidagi buyruqni kiriting:

```bash
pkg update -y && pkg install -y git python clang && git clone https://github.com/<USERNAME>/<REPO_NAME>.git vidi && cd vidi && bash setup_termux.sh
```

*(Yoki fayllarni yuklab olgandan so'ng:)*
```bash
cd vidi
bash setup_termux.sh
```

## Dasturni qayta ishga tushirish:
Keyingi safar Termuxda shunchaki:
```bash
cd vidi
python main.py
```
buyrug'ini berish kifoya!
