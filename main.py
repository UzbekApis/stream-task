import os
import sys
import time
import json
import shutil
import hashlib
import asyncio
import datetime
import subprocess
import requests
import urllib.parse
import urllib3
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

urllib3.disable_warnings()

BASE_URL = "https://157-180-25-63.sslip.io"
VP_PROOF_SALT = "vp20261108k3p9x2m7q4w8r1t6y0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INIT_DATA_FILE = os.path.join(BASE_DIR, 'init_data.txt')
SESSION_FILE = os.path.join(BASE_DIR, 'userbot')
ENV_FILE = os.path.join(BASE_DIR, '.env')

# Statistika o'zgaruvchilari
SESSION_START_TIME = time.time()
INITIAL_BALANCE = None
CURRENT_BALANCE = 0.0
EARNED_THIS_SESSION = 0.0
VIDEOS_COMPLETED = 0

def clear_console():
    os.system('clear' if os.name != 'nt' else 'cls')

def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def render_dashboard(status: str, video_title: str = "", video_pos: int = 0, video_dur: int = 0, tier_info: dict = None):
    uptime = format_duration(time.time() - SESSION_START_TIME)
    tier_num = tier_info.get('tier', 3) if tier_info else 3
    country = tier_info.get('country_code', 'Unknown') if tier_info else 'Unknown'
    rate = tier_info.get('reward_per_second', 0.0023) if tier_info else 0.0023
    hourly_rate = float(rate) * 3600

    tier_badge = f"Tier {tier_num} ({country}) [★ TIER 1 MAX]" if tier_num == 1 else f"Tier {tier_num} ({country}) [! TIER 3]"
    title_short = (video_title[:34] + '...') if len(video_title) > 34 else video_title

    clear_console()
    print("=" * 60)
    print("        ⚡ STREAM AUTO-TASK MANAGER DASHBOARD ⚡        ")
    print("=" * 60)
    print(f" ⏱  Ishlash vaqti:      {uptime:<10} | 📶 {status}")
    print(f" 🛡  Hudud va Tier:     {tier_badge}")
    print(f" ⚡  Daromad stavkasi:   {rate} $/s (~${hourly_rate:.2f}/soat)")
    print("-" * 60)
    print(f" 💰  Boshlang'ich:       ${INITIAL_BALANCE:.4f}")
    print(f" 📈  Sessiyada ishlandi: +${EARNED_THIS_SESSION:.4f}")
    print(f" 💵  Joriy Balans:       ${CURRENT_BALANCE:.4f}")
    print("-" * 60)
    print(f" 🎬  Jami bajarildi:     {VIDEOS_COMPLETED} ta vazifa")
    if video_title:
        progress = f"{video_pos}s/{video_dur}s"
        pct = int((video_pos / max(1, video_dur)) * 100) if video_dur > 0 else 0
        bar_len = 16
        filled = int(bar_len * (pct / 100))
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f" 📺  Hozirgi oqim:       {title_short}")
        print(f" ⏱  Jarayon:             [{bar}] {progress} ({pct}%)")
    print("=" * 60)
    print("  To'xtatish: Ctrl+C")
    print("=" * 60)

def compute_proof(kind: str, fields: list) -> str:
    raw = f"{VP_PROOF_SALT}|{kind}|{'|'.join(str(f) for f in fields)}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def save_qr_to_gallery(qr_img_path):
    """QR kodni Android galereyasiga saqlash va ochish"""
    gallery_dirs = [
        "/sdcard/DCIM",
        "/sdcard/Pictures",
        os.path.expanduser("~/storage/pictures"),
        os.path.expanduser("~/storage/dcim")
    ]
    saved_locations = []
    for gdir in gallery_dirs:
        try:
            if os.path.exists(gdir):
                target = os.path.join(gdir, "stream_login_qr.png")
                shutil.copyfile(qr_img_path, target)
                saved_locations.append(target)
        except Exception:
            pass

    try:
        subprocess.run(["termux-open", qr_img_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    return saved_locations

def setup_env_file():
    """Agar .env bo'lmasa yoki bo'sh bo'lsa, avtomatik yaratish"""
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        if os.getenv('APP_ID') and os.getenv('APP_HASH'):
            return

    clear_console()
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

    print("[✓] .env sozlama fayli muvaffaqiyatli yaratildi!\n")
    load_dotenv(ENV_FILE)

async def ensure_telegram_login():
    """Telegram sessiyasini tekshirish va kirish"""
    setup_env_file()

    app_id = int(os.getenv('APP_ID'))
    app_hash = os.getenv('APP_HASH')
    phone_env = os.getenv('PHONE')

    from telethon import TelegramClient, functions
    from telethon.errors import SessionPasswordNeededError
    from telethon.tl.types.auth import SentCodeTypeApp
    import qrcode

    client = TelegramClient(SESSION_FILE, app_id, app_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"[✓] Akkaunt ulangan: {me.first_name} (@{me.username or 'yoq'})")
        await client.disconnect()
        return

    clear_console()
    print("=" * 60)
    print("             AKKAUNTGA KIRISH")
    print("=" * 60)
    print("  [1] QR-kod orqali kirish (TAVSIYA ETILADI)")
    print("  [2] Telegram kodi orqali kirish")
    choice = input("\nTanlovingiz (1 yoki 2) [Standart: 1]: ").strip() or "1"

    if choice == "1":
        print("\n[*] QR kod tayyorlanmoqda...")
        qr_login = await client.qr_login()

        local_qr = os.path.join(BASE_DIR, "login_qr.png")
        qr = qrcode.QRCode(border=2)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(local_qr)

        gallery_paths = save_qr_to_gallery(local_qr)

        print("\nTerminaldagi QR kod:")
        qr.print_ascii(invert=True)

        print("\n" + "-" * 60)
        if gallery_paths:
            print(f"[+] QR kod telefoningiz Galereyasiga saqlandi:")
            print(f"    {gallery_paths[0]}")
        print("KO'RSATMA:")
        print("1. Telefoningizda Telegram ilovasiga kiring.")
        print("2. Sozlamalar -> Qurilmalar -> 'Qurilmani ulash' tugmasini bosing.")
        print("3. Ekranda chiqqan ushbu QR kodni skaner qiling.")
        print("-" * 60)
        print("[*] Skaner qilinishi kutilmoqda (60 soniya)...")

        try:
            await qr_login.wait(timeout=60)
            print("[✓] QR kod tasdiqlandi!")
        except SessionPasswordNeededError:
            import getpass
            pwd = getpass.getpass("[?] 2FA (ikki bosqichli) parolingizni kiriting: ")
            await client.sign_in(password=pwd)
    else:
        phone = phone_env or input("Telefon raqam (+998...): ").strip()
        sent_code = await client.send_code_request(phone)
        if isinstance(sent_code.type, SentCodeTypeApp):
            print("\n[!] DIQQAT: Kod TELEGRAM ilovasidagi 'Telegram' chatiga bordi!")
        else:
            print("\n[*] Kod telefoningizga SMS orqali bordi.")

        code = input("[?] Kodni kiriting: ").strip().replace(" ", "")
        try:
            await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
        except SessionPasswordNeededError:
            import getpass
            pwd = getpass.getpass("[?] 2FA parolingizni kiriting: ")
            await client.sign_in(password=pwd)

    bot = await client.get_entity('VidiPayMrBoT')
    res = await client(functions.messages.RequestWebViewRequest(
        peer=bot,
        bot=bot,
        url='https://157-180-25-63.sslip.io/app',
        platform='android'
    ))
    raw_data = res.url.split('#tgWebAppData=')[1].split('&tgWebAppVersion=')[0]
    init_data = urllib.parse.unquote(raw_data)
    with open(INIT_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(init_data)

    await client.disconnect()
    print("[✓] Login muvaffaqiyatli yakunlandi!")
    time.sleep(1)

def check_internet_and_tier():
    """Internet va Tier 1 nazorati"""
    first_warn = True
    while True:
        try:
            r = requests.get(f"{BASE_URL}/tier/status", verify=False, timeout=6)
            if r.status_code == 200:
                data = r.json()
                tier = data.get('tier', 3)
                if tier == 1:
                    return data
                else:
                    if first_warn:
                        clear_console()
                        print("\n" + "!" * 60)
                        print("  [!] DIQQAT: TIER 1 (AQSH) VPN ULANMAGAN!")
                        print(f"      Hozirgi IP: {data.get('ip')} | Hudud: {data.get('country_code')} (Tier {tier})")
                        print("      Past stavkada ishlamaslik uchun vazifalar to'xtatib turildi.")
                        print("      Iltimos, telefoningizda AQSH (USA) VPN'ni yoqing!")
                        print("!" * 60)
                        first_warn = False
                    print(f"\r[*] Tier 1 VPN kutilmoqda... [{datetime.datetime.now().strftime('%H:%M:%S')}]", end='', flush=True)
                    time.sleep(3)
            else:
                time.sleep(3)
        except Exception:
            clear_console()
            print("\n" + "-" * 60)
            print("  [!] INTERNET UZILDI YOKI MB TUGADI!")
            print("      Internetga qayta ulanishi avtomatik kutilmoqda...")
            print(f"      Tekshirilmoqda... [{datetime.datetime.now().strftime('%H:%M:%S')}]")
            print("-" * 60)
            time.sleep(4)

async def refresh_init_data():
    try:
        from telethon import TelegramClient, functions
        app_id = int(os.getenv('APP_ID'))
        app_hash = os.getenv('APP_HASH')
        client = TelegramClient(SESSION_FILE, app_id, app_hash)
        await client.connect()
        bot = await client.get_entity('VidiPayMrBoT')
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            url='https://157-180-25-63.sslip.io/app',
            platform='android'
        ))
        raw_data = res.url.split('#tgWebAppData=')[1].split('&tgWebAppVersion=')[0]
        init_data = urllib.parse.unquote(raw_data)
        with open(INIT_DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(init_data)
        await client.disconnect()
        return init_data
    except Exception:
        return None

def get_init_data():
    if os.path.exists(INIT_DATA_FILE):
        with open(INIT_DATA_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return asyncio.run(refresh_init_data())

def get_mrbeast_videos():
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCX6OQ3DkcsbYNE6H8uQQuVA"
    try:
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        videos = []
        for entry in root.findall('atom:entry', ns):
            vid = entry.find('yt:videoId', ns).text
            title = entry.find('atom:title', ns).text
            videos.append({'id': vid, 'title': title, 'duration': 900})
        if videos:
            return videos
    except Exception:
        pass

    return [
        {'id': 'sHpEqeSByPI', 'title': 'Unboxing The World\'s Largest Toy', 'duration': 920},
        {'id': 'kPI9Mc35mOg', 'title': 'Trap Door Roulette', 'duration': 840},
        {'id': '_c2e1NcI3Sc', 'title': 'Beat Professional Athlete, Win $100,000', 'duration': 1100},
        {'id': '41UzbuW6wJs', 'title': 'Can A Robot Do My Chores?', 'duration': 780},
        {'id': 'mND4T0lzg_g', 'title': 'How People Treat You Based on Subscribers', 'duration': 950}
    ]

def main():
    global INITIAL_BALANCE, CURRENT_BALANCE, EARNED_THIS_SESSION, VIDEOS_COMPLETED

    asyncio.run(ensure_telegram_login())

    init_data = get_init_data()

    def make_headers(auth_str):
        return {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': auth_str,
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/app"
        }

    headers = make_headers(init_data)

    tier_info = check_internet_and_tier()

    while True:
        try:
            user_resp = requests.post(f"{BASE_URL}/user/sync", headers=headers, json={}, verify=False, timeout=8)
            if user_resp.status_code == 401:
                init_data = asyncio.run(refresh_init_data())
                headers = make_headers(init_data)
                continue
            if user_resp.status_code == 200:
                user_info = user_resp.json().get('user', {})
                CURRENT_BALANCE = float(user_info.get('balance', 0))
                if INITIAL_BALANCE is None:
                    INITIAL_BALANCE = CURRENT_BALANCE
                break
        except Exception:
            tier_info = check_internet_and_tier()

    render_dashboard("Tayyor, vazifalar yuklanmoqda...", "", 0, 0, tier_info)

    videos = get_mrbeast_videos()

    video_idx = 0
    while True:
        video = videos[video_idx % len(videos)]
        video_idx += 1

        vid_id = video['id']
        title = video['title']
        duration = video['duration']

        tier_info = check_internet_and_tier()

        start_proof = compute_proof('start', [vid_id, int(duration)])
        start_payload = {
            'proof': start_proof,
            'video_source': 'mrbeast_uploads',
            'video_id': vid_id,
            'video_duration_seconds': duration,
            'player_position_seconds': 0,
            'player_state': 1
        }

        sess_ok = False
        while not sess_ok:
            try:
                start_res = requests.post(f"{BASE_URL}/view/session/start", headers=headers, json=start_payload, verify=False, timeout=10)
                if start_res.status_code == 401:
                    init_data = asyncio.run(refresh_init_data())
                    headers = make_headers(init_data)
                    continue

                if start_res.status_code == 200:
                    sess_data = start_res.json()
                    session_id = sess_data.get('session_id')
                    session_token = sess_data.get('session_token')
                    heartbeat_interval = int(sess_data.get('heartbeat_interval_seconds', 5))
                    sess_ok = True
                else:
                    time.sleep(3)
                    break
            except Exception:
                tier_info = check_internet_and_tier()

        if not sess_ok:
            continue

        sequence = 1
        position = 0
        target_watch_seconds = 35

        render_dashboard("Vazifa bajarilmoqda", title, 0, target_watch_seconds, tier_info)

        while position < target_watch_seconds:
            time.sleep(heartbeat_interval)
            position += heartbeat_interval
            sequence += 1

            heartbeat_proof = compute_proof('heartbeat', [
                session_id,
                int(sequence),
                int(position),
                int(duration)
            ])

            hb_payload = {
                'proof': heartbeat_proof,
                'session_id': session_id,
                'session_token': session_token,
                'sequence': sequence,
                'player_position_seconds': position,
                'video_duration_seconds': duration,
                'interval_playing': True,
                'interval_visible': True,
                'ended': position >= target_watch_seconds,
                'supports_superseded': True
            }

            hb_sent = False
            while not hb_sent:
                try:
                    hb_res = requests.post(f"{BASE_URL}/view/session/heartbeat", headers=headers, json=hb_payload, verify=False, timeout=10)
                    if hb_res.status_code == 200:
                        hb_data = hb_res.json()
                        CURRENT_BALANCE = float(hb_data.get('reward_balance', CURRENT_BALANCE))
                        EARNED_THIS_SESSION = CURRENT_BALANCE - INITIAL_BALANCE
                        render_dashboard("Hisoblanmoqda...", title, position, target_watch_seconds, tier_info)
                        if hb_data.get('terminal') or position >= target_watch_seconds:
                            VIDEOS_COMPLETED += 1
                            render_dashboard("✅ Vazifa yakunlandi!", title, target_watch_seconds, target_watch_seconds, tier_info)
                            break
                        hb_sent = True
                    else:
                        break
                except Exception:
                    tier_info = check_internet_and_tier()

        time.sleep(2)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[✓] Dastur to'xtatildi. Jami ishlangan: +$" + f"{EARNED_THIS_SESSION:.4f}")
