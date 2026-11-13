#!/data/data/com.termux/files/usr/bin/bash

echo "=================================================="
echo "    🚀 STREAM TASK MANAGER (TERMUX) O'RNATISH    "
echo "=================================================="

# Paketlarni yangilash va kerakli dasturlarni o'rnatish
pkg update -y
pkg install -y python git libjpeg-turbo clang termux-tools

# Termux xotiraga ruxsat (Galereyaga QR saqlash uchun)
termux-setup-storage

# Python kutubxonalarini o'rnatish
pip install --upgrade pip
pip install requests telethon python-dotenv qrcode pillow

echo "=================================================="
echo "    [✓] O'RNATISH YAKUNLANDI!                     "
echo "    Dastur ishga tushirilmoqda...                 "
echo "=================================================="

python main.py
