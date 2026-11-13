import os
import sys
import time
import json
import hashlib
import asyncio
import datetime
import requests
import urllib.parse
import urllib3
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

urllib3.disable_warnings()

BASE_URL = "https://157-180-25-63.sslip.io"
VP_PROOF_SALT = "vp20261108k3p9x2m7q4w8r1t6y0"
PROXIES_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'us_tier1_proxies.json')
INIT_DATA_FILE = os.path.join(os.path.dirname(__file__), 'init_data.txt')
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)

# Statistika o'zgaruvchilari
SESSION_START_TIME = time.time()
INITIAL_BALANCE = None
CURRENT_BALANCE = 0.0
EARNED_THIS_SESSION = 0.0
VIDEOS_COMPLETED = 0

def format_duration(seconds: float) -> str:
    """Soniyani HH:MM:SS formatiga o'tkazish"""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def clear_console():
    """Konsolni tozalash"""
    os.system('cls' if os.name == 'nt' else 'clear')

def render_dashboard(status: str, video_title: str = "", video_pos: int = 0, video_dur: int = 0, tier_info: dict = None):
    """Real-time jonli status paneli"""
    uptime = format_duration(time.time() - SESSION_START_TIME)
    tier_num = tier_info.get('tier', 3) if tier_info else 3
    country = tier_info.get('country_code', 'Unknown') if tier_info else 'Unknown'
    rate = tier_info.get('reward_per_second', 0.0023) if tier_info else 0.0023
    hourly_rate = float(rate) * 3600

    tier_badge = f"Tier {tier_num} ({country}) [★ MAX TIER 1]" if tier_num == 1 else f"Tier {tier_num} ({country}) [! TIER 3]"
    title_short = (video_title[:38] + '...') if len(video_title) > 38 else video_title

    clear_console()
    print("=" * 64)
    print("        ⚡ VIDIPAY MRBEAST AUTO-EARNER DASHBOARD ⚡        ")
    print("=" * 64)
    print(f" ⏱  Ishlash vaqti:      {uptime:<12} | 📶 Holat: {status}")
    print(f" 🛡  Hudud va Tier:     {tier_badge}")
    print(f" ⚡  Daromad stavkasi:   {rate} $/s (~${hourly_rate:.2f} / soat)")
    print("-" * 64)
    print(f" 💰  Boshlang'ich balans: ${INITIAL_BALANCE:.4f} USD")
    print(f" 📈  Sessiyada ishlandi: +${EARNED_THIS_SESSION:.4f} USD")
    print(f" 💵  Joriy Balans:       ${CURRENT_BALANCE:.4f} USD")
    print("-" * 64)
    print(f" 🎬  Jami ko'rildi:      {VIDEOS_COMPLETED} ta video")
    if video_title:
        progress = f"{video_pos}s / {video_dur}s"
        pct = int((video_pos / max(1, video_dur)) * 100) if video_dur > 0 else 0
        bar_len = 20
        filled = int(bar_len * (pct / 100))
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f" 📺  Hozirgi video:      {title_short}")
        print(f" ⏱  Jarayon:             [{bar}] {progress} ({pct}%)")
    print("=" * 64)
    print("  [Ctrl+C] - Dasturni xavfsiz to'xtatish")
    print("=" * 64)

def compute_proof(kind: str, fields: list) -> str:
    """SHA-256 xavfsizlik imzosini hisoblash"""
    raw = f"{VP_PROOF_SALT}|{kind}|{'|'.join(str(f) for f in fields)}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def get_best_us_proxy():
    """AQSH Tier 1 proksisini yuklash"""
    if os.path.exists(PROXIES_CACHE_FILE):
        try:
            with open(PROXIES_CACHE_FILE, 'r') as f:
                saved = json.load(f)
            if saved and len(saved) > 0:
                p = saved[0].get("proxy")
                return {"http": f"http://{p}", "https": f"http://{p}"}, p
        except Exception:
            pass
    return None, None

def check_internet_and_tier(session):
    """
    Internet va Tier 1 nazorati:
    1. Internet uzilsa yoki MB tugasa, qayta ulanguncha kutadi.
    2. Tier 1 bo'lmasa, Tier 1 VPN ulanguncha ishlamay kutib turadi.
    """
    first_warn = True
    while True:
        try:
            r = session.get(f"{BASE_URL}/tier/status", verify=False, timeout=6)
            if r.status_code == 200:
                data = r.json()
                tier = data.get('tier', 3)
                if tier == 1:
                    return data
                else:
                    if first_warn:
                        clear_console()
                        print("\n" + "!" * 64)
                        print("  [!] DIQQAT: TIER 1 (AQSH/UK/DE...) VPN ULANMAGAN!")
                        print(f"      Hozirgi IP: {data.get('ip')} | Hudud: {data.get('country_code')} (Tier {tier})")
                        print("      Tier 3 stavkasida pul ishlash to'xtatildi (zarar ko'rmaslik uchun).")
                        print("      Iltimos, Tier 1 bo'lgan VPN ga ulaning (USA/AQSH).")
                        print("!" * 64)
                        first_warn = False
                    print(f"\r[*] Tier 1 VPN ulanishi kutilmoqda... [{datetime.datetime.now().strftime('%H:%M:%S')}]", end='', flush=True)
                    time.sleep(4)
            else:
                time.sleep(4)
        except Exception:
            clear_console()
            print("\n" + "-" * 64)
            print("  [!] INTERNET UZILDI YOKI MB TUGADI!")
            print("      Internetga qayta ulanishi avtomatik kutilmoqda...")
            print(f"      Tekshirilmoqda... [{datetime.datetime.now().strftime('%H:%M:%S')}]")
            print("-" * 64)
            time.sleep(5)

async def fetch_fresh_init_data_telethon():
    """userbot.session orqali yangi initData olish"""
    try:
        from telethon import TelegramClient, functions
        app_id = int(os.getenv('APP_ID', '0'))
        app_hash = os.getenv('APP_HASH', '')
        if not app_id or not app_hash:
            return None

        session_path = os.path.join(os.path.dirname(__file__), 'userbot')
        client = TelegramClient(session_path, app_id, app_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return None

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
    except Exception as e:
        print(f"[!] InitData olishda xatolik: {e}")
        return None

def get_valid_init_data():
    """InitData olish va agar eskirgan bo'lsa yangilash"""
    init_data = ""
    if os.path.exists(INIT_DATA_FILE):
        with open(INIT_DATA_FILE, 'r', encoding='utf-8') as f:
            init_data = f.read().strip()
        if '%3D' in init_data or '%26' in init_data:
            init_data = urllib.parse.unquote(init_data)

    is_fresh = False
    if init_data:
        try:
            for part in init_data.split('&'):
                if part.startswith('auth_date='):
                    ts = int(part.split('=')[1])
                    if time.time() - ts < 3 * 3600:
                        is_fresh = True
                    break
        except Exception:
            pass

    if not is_fresh or not init_data:
        print("[*] Telegram WebApp kaliti (initData) yangilanmoqda...")
        fresh = asyncio.run(fetch_fresh_init_data_telethon())
        if fresh:
            return fresh

    return init_data

def get_mrbeast_videos(session):
    """MrBeast videolarini YouTube RSS dan olish"""
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCX6OQ3DkcsbYNE6H8uQQuVA"
    try:
        r = session.get(url, timeout=10)
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

    clear_console()
    print("=" * 64)
    print("       ⚡ VIDIPAY MRBEAST AUTO-EARNER TIZIMI ISHGA TUSHMOQDA ⚡       ")
    print("=" * 64)

    # 1. InitData olish
    init_data = get_valid_init_data()
    if not init_data:
        print("[-] Telegram initData olinmadi. Avval 'python login.py' ni ishga tushiring.")
        sys.exit(1)

    # 2. AQSH proksi ulanishi
    proxies, proxy_host = get_best_us_proxy()
    session = requests.Session()
    if proxies:
        session.proxies = proxies

    def make_headers(auth_str):
        return {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': auth_str,
            'Origin': BASE_URL,
            'Referer': f"{BASE_URL}/app"
        }

    headers = make_headers(init_data)

    # 3. Internet va Tier 1 tekshirish
    tier_info = check_internet_and_tier(session)

    # 4. Profil ma'lumotlarini yuklash
    while True:
        try:
            user_resp = session.post(f"{BASE_URL}/user/sync", headers=headers, json={}, verify=False, timeout=8)
            if user_resp.status_code == 401:
                init_data = asyncio.run(fetch_fresh_init_data_telethon())
                headers = make_headers(init_data)
                continue
            if user_resp.status_code == 200:
                user_info = user_resp.json().get('user', {})
                CURRENT_BALANCE = float(user_info.get('balance', 0))
                if INITIAL_BALANCE is None:
                    INITIAL_BALANCE = CURRENT_BALANCE
                break
        except Exception:
            tier_info = check_internet_and_tier(session)

    render_dashboard("Tayyor, videolar yuklanmoqda...", "", 0, 0, tier_info)

    videos = get_mrbeast_videos(session)

    # 5. Asosiy ko'rish sikli
    video_idx = 0
    while True:
        video = videos[video_idx % len(videos)]
        video_idx += 1

        vid_id = video['id']
        title = video['title']
        duration = video['duration']

        # Har bir yangi video oldidan Tier 1 va internet tekshiriladi
        tier_info = check_internet_and_tier(session)

        start_proof = compute_proof('start', [vid_id, int(duration)])
        start_payload = {
            'proof': start_proof,
            'video_source': 'mrbeast_uploads',
            'video_id': vid_id,
            'video_duration_seconds': duration,
            'player_position_seconds': 0,
            'player_state': 1
        }

        # Sessiya ochish
        sess_ok = False
        while not sess_ok:
            try:
                start_res = session.post(f"{BASE_URL}/view/session/start", headers=headers, json=start_payload, verify=False, timeout=10)
                if start_res.status_code == 401:
                    init_data = asyncio.run(fetch_fresh_init_data_telethon())
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
                tier_info = check_internet_and_tier(session)

        if not sess_ok:
            continue

        sequence = 1
        position = 0
        target_watch_seconds = 35

        render_dashboard("Tomosha qilinmoqda (Video boshlandi)", title, 0, target_watch_seconds, tier_info)

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
                    hb_res = session.post(f"{BASE_URL}/view/session/heartbeat", headers=headers, json=hb_payload, verify=False, timeout=10)
                    if hb_res.status_code == 200:
                        hb_data = hb_res.json()
                        CURRENT_BALANCE = float(hb_data.get('reward_balance', CURRENT_BALANCE))
                        EARNED_THIS_SESSION = CURRENT_BALANCE - INITIAL_BALANCE
                        render_dashboard("Pul hisoblanmoqda...", title, position, target_watch_seconds, tier_info)
                        if hb_data.get('terminal') or position >= target_watch_seconds:
                            VIDEOS_COMPLETED += 1
                            render_dashboard("✅ Video yakunlandi!", title, target_watch_seconds, target_watch_seconds, tier_info)
                            break
                        hb_sent = True
                    else:
                        break
                except Exception:
                    tier_info = check_internet_and_tier(session)

        time.sleep(2)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[✓] Dastur to'xtatildi. Jami ishlangan: +$" + f"{EARNED_THIS_SESSION:.4f}")
