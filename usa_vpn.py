import os
import sys
import json
import winreg
import ctypes
import requests
import urllib3
import concurrent.futures

urllib3.disable_warnings()

TARGET_URL = "https://157-180-25-63.sslip.io/tier/status"
PROXIES_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'us_tier1_proxies.json')

def apply_windows_proxy(enable: bool, proxy_server: str = ""):
    """Windows tizim proksi sozlamasini o'zgartiradi va tizimni yangilaydi"""
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
            0,
            winreg.KEY_ALL_ACCESS
        )
        winreg.SetValueEx(reg_key, 'ProxyEnable', 0, winreg.REG_DWORD, 1 if enable else 0)
        if enable and proxy_server:
            winreg.SetValueEx(reg_key, 'ProxyServer', 0, winreg.REG_SZ, proxy_server)
        winreg.CloseKey(reg_key)

        # WinINet sozlamalarini yangilash
        wininet = ctypes.windll.wininet
        wininet.InternetSetOptionW(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
        wininet.InternetSetOptionW(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH
        return True
    except Exception as e:
        print(f"[-] Proksi sozlashda xatolik: {e}")
        return False

def get_current_status():
    """Hozirgi tizim proksi holatini tekshiradi"""
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
            0,
            winreg.KEY_READ
        )
        enabled, _ = winreg.QueryValueEx(reg_key, 'ProxyEnable')
        try:
            server, _ = winreg.QueryValueEx(reg_key, 'ProxyServer')
        except FileNotFoundError:
            server = ""
        winreg.CloseKey(reg_key)
        return bool(enabled), server
    except Exception:
        return False, ""

def test_tier(proxy: str = None, timeout: float = 4.0):
    """VidiPay /tier/status endpointini tekshiradi"""
    proxies = None
    if proxy:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    try:
        r = requests.get(TARGET_URL, proxies=proxies, verify=False, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def find_fast_us_proxies():
    """Yangi va tezkor US proksilarni qidiradi va saralaydi"""
    print("[*] Yangi US Tier 1 proksilar qidirilmoqda...")
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=us&ssl=all&anonymity=all"
    candidates = []
    try:
        r = requests.get(url, timeout=7)
        candidates.extend([p.strip() for p in r.text.splitlines() if p.strip() and ':' in p])
    except Exception:
        pass

    # Qo'shimcha manba
    extra_sources = [
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_US.txt",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    ]
    for src in extra_sources:
        try:
            r = requests.get(src, timeout=5)
            candidates.extend([p.strip() for p in r.text.splitlines() if p.strip() and ':' in p])
        except Exception:
            pass

    candidates = list(dict.fromkeys(candidates))
    print(f"[*] Tekshirish uchun {len(candidates)} ta proksi topildi.")

    found = []
    def check_candidate(p):
        data = test_tier(p, timeout=4.0)
        if data and (data.get("country_code") == "US" or data.get("tier") == 1):
            return {"proxy": p, "data": data}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(check_candidate, p) for p in candidates[:100]]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                found.append(res)
                print(f"[+] Ishlaydigan US proksi topildi: {res['proxy']} (Tier: {res['data'].get('tier')})")
                if len(found) >= 3:
                    break

    if found:
        with open(PROXIES_CACHE_FILE, 'w') as f:
            json.dump(found, f, indent=2)
        print(f"[+] {len(found)} ta US proksi saqlandi.")
    return found

def get_best_us_proxy():
    """Mavjud ro'yxatdan ishlaydigan US proksini qaytaradi"""
    if os.path.exists(PROXIES_CACHE_FILE):
        try:
            with open(PROXIES_CACHE_FILE, 'r') as f:
                saved = json.load(f)
            for item in saved:
                p = item.get("proxy")
                data = test_tier(p, timeout=3.5)
                if data and (data.get("country_code") == "US" or data.get("tier") == 1):
                    return p, data
        except Exception:
            pass

    # Agar keshda yo'q bo'lsa yangilarini qidiradi
    new_found = find_fast_us_proxies()
    if new_found:
        return new_found[0]["proxy"], new_found[0]["data"]
    return None, None

def connect_usa():
    print("=" * 55)
    print("           USA VPN / PROXY ULAGICH (VidiPay Tier 1)")
    print("=" * 55)
    proxy, data = get_best_us_proxy()
    if not proxy:
        print("[-] Hozircha ishlaydigan US proksi topilmadi!")
        return False

    print(f"[*] Tanlangan US Proksi: {proxy}")
    print(f"    - Mamlakat: {data.get('country_code')} (USA)")
    print(f"    - Tier darajasi: Tier {data.get('tier')} (Yuqori daromad!)")
    print(f"    - Mukofot stavkasi: {data.get('reward_per_second')} $/sekund")

    if apply_windows_proxy(True, proxy):
        print("\n[✓] Windows tizim proksisi muvaffaqiyatli USA ga ulandi!")
        print("    Endi brauzer va barcha ilovalar AQSH (USA) tarmog'i orqali ishlaydi.")
        print("    VidiPay webapp ochilganda Tier 1 (0.0023 $/s) faollashadi.")
        return True
    return False

def disconnect_vpn():
    print("=" * 55)
    print("           USA VPN / PROXINI O'CHIRISH")
    print("=" * 55)
    apply_windows_proxy(False, "")
    print("[✓] Windows proksisi o'chirildi. To'g'ridan-to'g'ri internetga qaytildi.")

def show_status():
    enabled, server = get_current_status()
    print("=" * 55)
    print("                 STATUS MA'LUMOTLARI")
    print("=" * 55)
    print(f"Tizim proksisi holati: {'YOQILGAN [ON]' if enabled else 'O\'CHIRILGAN [OFF]'}")
    if enabled:
        print(f"Ulangan server: {server}")
    
    print("\nVidiPay serveriga ulanish tekshirilmoqda...")
    info = test_tier()
    if info:
        print(f"  - Sizning IP: {info.get('ip')}")
        print(f"  - Aniqlangan mamlakat: {info.get('country_code')} ({info.get('country_name')})")
        print(f"  - Joriy Tier: Tier {info.get('tier')}")
        print(f"  - Sekundiga daromad: {info.get('reward_per_second')} $")
        if info.get('tier') == 1:
            print("  [★] TIER 1 FAOLLASHTIRILGAN! (Maksimal daromad)")
        else:
            print("  [!] Hali Tier 1 emas (O'zbekiston/boshqa hudud). Ulanish uchun 'python usa_vpn.py on' bosing.")
    else:
        print("  [-] VidiPay serveriga ulanib bo'lmadi.")

if __name__ == '__main__':
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else 'help'
    if arg in ['on', 'connect', 'start']:
        connect_usa()
    elif arg in ['off', 'disconnect', 'stop']:
        disconnect_vpn()
    elif arg in ['status', 'check']:
        show_status()
    elif arg in ['find', 'refresh']:
        find_fast_us_proxies()
    else:
        print("Foydalanish bo'yicha qo'llanma:")
        print("  python usa_vpn.py on      -> USA proksisiga ulanish (Tier 1)")
        print("  python usa_vpn.py off     -> Proksini o'chirish (asl holatga qaytish)")
        print("  python usa_vpn.py status  -> Hozirgi IP va Tier holatini tekshirish")
        print("  python usa_vpn.py find    -> Yangi US proksilarni qidirish va yangilash")
