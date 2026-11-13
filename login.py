import os
import sys
import asyncio
import getpass
import urllib.parse
import qrcode
from dotenv import load_dotenv
from telethon import TelegramClient, functions
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    FloodWaitError
)
from telethon.tl.types.auth import SentCodeTypeApp, SentCodeTypeSms

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')
SESSION_FILE = os.path.join(BASE_DIR, 'userbot')
INIT_DATA_FILE = os.path.join(BASE_DIR, 'init_data.txt')

def setup_env_file():
    """Agar .env bo'lmasa, foydalanuvchidan so'rab yaratish"""
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        if os.getenv('APP_ID') and os.getenv('APP_HASH'):
            return

    print("=" * 60)
    print("           TIZIMNI SOZLASH (API SETUP)")
    print("=" * 60)
    print("[!] my.telegram.org saytidan olingan API ma'lumotlarni kiriting:")
    
    app_id = ""
    while not app_id:
        app_id = input("[?] APP_ID kiriting: ").strip()

    app_hash = ""
    while not app_hash:
        app_hash = input("[?] APP_HASH kiriting: ").strip()

    phone = input("[?] Telefon raqam (+998...) [ixtiyoriy]: ").strip()

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(f"APP_ID={app_id}\nAPP_HASH={app_hash}\nPHONE={phone}\n")

    print("[✓] .env sozlama fayli muvaffaqiyatli saqlandi!\n")
    load_dotenv(ENV_FILE)

setup_env_file()

app_id = int(os.getenv('APP_ID'))
app_hash = os.getenv('APP_HASH')
phone_env = os.getenv('PHONE')

client = TelegramClient(SESSION_FILE, app_id, app_hash)

async def save_init_data():
    """Botdan WebApp havolasi va initData olish"""
    print("\n[*] WebApp initData olinmoqda...")
    try:
        bot = await client.get_entity('VidiPayMrBoT')
        web_view = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            url='https://157-180-25-63.sslip.io/app',
            platform='android'
        ))
        if '#tgWebAppData=' in web_view.url:
            raw_data = web_view.url.split('#tgWebAppData=')[1].split('&tgWebAppVersion=')[0]
            init_data = urllib.parse.unquote(raw_data)
            with open(INIT_DATA_FILE, 'w', encoding='utf-8') as f:
                f.write(init_data)
            print("[✓] 'init_data.txt' fayliga WebApp auth muvaffaqiyatli saqlandi!")
    except Exception as e:
        print(f"[!] Bot ma'lumotini olishda: {e}")

async def login_with_qr():
    """QR kod orqali tezkor kirish"""
    print("\n" + "=" * 60)
    print("           QR KOD ORQALI KIRISH")
    print("=" * 60)
    print("[*] QR kod tayyorlanmoqda...")
    
    try:
        qr_login = await client.qr_login()
        
        qr_img_path = os.path.join(BASE_DIR, 'stream_login_qr.png')
        qr = qrcode.QRCode(border=2)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_img_path)

        try:
            os.startfile(qr_img_path)
            print("[+] QR rasm ekranda ochildi!")
        except Exception:
            pass

        print("\nTerminaldagi QR kod:")
        qr.print_ascii(invert=True)

        print("\n" + "-" * 60)
        print("KO'RSATMA:")
        print("1. Telefoningizda Telegram ilovasini oching.")
        print("2. Sozlamalar -> Qurilmalar -> 'Qurilmani ulash' tugmasini bosing.")
        print("3. Ekranda chiqqan ushbu QR kodga kamerani qarating.")
        print("-" * 60)
        print("[*] Skaner qilinishi kutilmoqda (60 soniya)...")

        user = await qr_login.wait(timeout=60)
        print("\n[✓] QR kod skaner qilindi va tasdiqlandi!")
        return user

    except SessionPasswordNeededError:
        print("\n[*] Akkauntingizda 2FA (ikki bosqichli parol) o'rnatilgan.")
        pwd = getpass.getpass("[?] Ikki bosqichli parolingizni kiriting: ")
        return await client.sign_in(password=pwd)
    except asyncio.TimeoutError:
        print("\n[-] Vaqt tugadi! QR kod skaner qilinmadi.")
        return None
    except Exception as e:
        print(f"\n[-] QR login xatosi: {e}")
        return None

async def login_with_code():
    """Telegram ilovasi / SMS kodi orqali kirish"""
    print("\n" + "=" * 60)
    print("           KOD ORQALI KIRISH")
    print("=" * 60)

    phone = phone_env
    if not phone:
        phone = input("Telefon raqamingizni kiriting (+998...): ").strip()
    else:
        print(f"[*] Telefon raqam: {phone}")

    print("[*] Tasdiqlash kodi so'ralmoqda...")
    try:
        sent_code = await client.send_code_request(phone)
    except FloodWaitError as e:
        print(f"[-] Telegram cheklovi! {e.seconds} soniya kutishingiz kerak.")
        return None
    except Exception as e:
        print(f"[-] Xatolik yuz berdi: {e}")
        return None

    if isinstance(sent_code.type, SentCodeTypeApp):
        print("\n" + "!" * 60)
        print("DIQQAT: Kod TELEGRAM ilovasidagi rasmiy 'Telegram' chatiga bordi!")
        print("!" * 60 + "\n")
    elif isinstance(sent_code.type, SentCodeTypeSms):
        print("\n[*] Tasdiqlash kodi telefoningizga SMS orqali yuborildi.\n")

    code = input("[?] Telegramga kelgan kodni kiriting: ").strip().replace(" ", "")

    try:
        user = await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
        return user
    except PhoneCodeInvalidError:
        print("[-] Kiritilgan kod noto'g'ri!")
        return None
    except SessionPasswordNeededError:
        print("\n[*] Akkauntingizda 2FA (ikki bosqichli parol) o'rnatilgan.")
        password = getpass.getpass("[?] Ikki bosqichli parolingizni kiriting: ")
        try:
            return await client.sign_in(password=password)
        except PasswordHashInvalidError:
            print("[-] 2FA parol noto'g'ri!")
            return None
    except Exception as e:
        print(f"[-] Kirishda xatolik: {e}")
        return None

async def main():
    print("[*] Telegram serveriga ulanmoqda...")
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print("\n[+] Akkaunt ulangan:")
        print(f"    - Ism: {me.first_name}")
        print(f"    - Username: @{me.username if me.username else 'yo\'q'}")
        print(f"    - Telefon: +{me.phone}")
        await save_init_data()
        await client.disconnect()
        return

    print("\nQaysi usul orqali kirishni xohlaysiz?")
    print("  [1] QR-kod orqali (TAVSIYA ETILADI)")
    print("  [2] Telegram kodi orqali")
    
    choice = input("\nTanlovingiz (1 yoki 2) [Standart: 1]: ").strip() or '1'

    user = None
    if choice == '1':
        user = await login_with_qr()
    else:
        user = await login_with_code()

    if user and await client.is_user_authorized():
        me = await client.get_me()
        print("\n" + "=" * 60)
        print("[✓] AKKAUNTGA MUVAFFAQIYATLI KIRILDI!")
        print(f"    - Ism: {me.first_name}")
        print(f"    - Username: @{me.username if me.username else 'yo\'q'}")
        print("=" * 60)
        await save_init_data()
    else:
        print("\n[-] Tizimga kirish amalga oshmadi.")

    await client.disconnect()
    print("\n[✓] Jarayon yakunlandi.")

if __name__ == '__main__':
    asyncio.run(main())
