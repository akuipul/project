from playwright.sync_api import Playwright, sync_playwright
import time
from datetime import datetime
import pytz
import requests
import os
import sys

def baca_file(file_name: str) -> str:
    with open(file_name, 'r') as file:
        return file.read().strip()

def baca_file_list(file_name: str) -> list:
    with open(file_name, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def kirim_telegram_log(pesan: str):
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    print(pesan)
    if telegram_token and telegram_chat_id:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                data={
                    "chat_id": telegram_chat_id,
                    "text": pesan,
                    "parse_mode": "Markdown"
                }
            )
            if response.status_code != 200:
                print(f"⚠️ Gagal kirim ke Telegram. Status: {response.status_code}")
                print(f"Respon Telegram: {response.text}")
        except Exception as e:
            print(f"⚠️ Error kirim Telegram: {e}")
    else:
        print("⚠️ Token atau Chat ID Telegram tidak tersedia.")

def parse_nomorbet(nomorbet: str):
    try:
        kombinasi = nomorbet.split('*')
        return len(kombinasi)
    except:
        return 0

def wib():
    return datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M WIB")

def run(playwright: Playwright) -> int:
    sites = baca_file_list("site.txt")
    pw_env = os.getenv("pw")
    ada_error = False

    for entry in sites:
        try:
            site, userid_site, bet, file_nomorbet = entry.split(':')
            full_url = f"https://{site}/lite"
            label = f"[{site.upper()}]"

            if not os.path.exists(file_nomorbet):
                print(f"❌ File nomorbet '{file_nomorbet}' tidak ditemukan untuk {userid_site}, dilewati.")
                continue

            nomor_saja = baca_file(file_nomorbet)
            nomorbet = nomor_saja + "#" + bet
            jumlah_kombinasi = parse_nomorbet(nomor_saja)
            total_bet_rupiah = int(bet) * jumlah_kombinasi

            print(f"🌐 Membuka browser untuk {site}...")
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(**playwright.devices["Pixel 7"])
            page = context.new_page()

            page.goto(full_url)
            page.locator("#entered_login").fill(userid_site)
            page.locator("#entered_password").fill(pw_env)
            page.get_by_role("button", name="Login").click()

            print(f"🔐 Login ke {site} berhasil, masuk menu Pools > HOKIDRAW > 4D Classic")
            page.get_by_role("link", name="Pools").click()
            page.get_by_role("link", name="HOKIDRAW").click()
            time.sleep(2)
            page.get_by_role("button", name="4D Classic").click()
            time.sleep(2)

            print(f"🧾 Mengisi form taruhan di {site}...")
            page.get_by_role("cell", name="BET FULL").click()
            page.locator("#tebak").fill(nomorbet)
            page.once("dialog", lambda dialog: dialog.accept())

            print(f"📨 Mengirim taruhan di {site}...")
            page.get_by_role("button", name="KIRIM").click()
            page.wait_for_selector("text=Bet Sukses!!", timeout=15000)

            page.get_by_role("link", name="Back to Menu").click()
            page.reload()
            time.sleep(2)
            try:
                saldo = page.locator("#bal-text").inner_text()
            except:
                saldo = "tidak diketahui"

            pesan_sukses = (
                f"[SUKSES]\n"
                f"{userid_site}\n"
                f"🎯 TOTAL {jumlah_kombinasi} HARGA Rp. {bet}\n"
                f"💸 BAYAR Rp. {total_bet_rupiah}\n"
                f"💰 SALDO Rp. {saldo}\n"
                f"⌚ {wib()}"
            )
            kirim_telegram_log(pesan_sukses)

            context.close()
            browser.close()

        except Exception as e:
            ada_error = True
            print(f"❌ Error di {entry}: {e}")
            try:
                saldo = page.locator("#bal-text").inner_text()
            except:
                saldo = "tidak diketahui"

            pesan_gagal = (
                f"[GAGAL]\n"
                f"{userid_site}\n"
                f"❌ TOTAL {jumlah_kombinasi} HARGA Rp. {bet}\n"
                f"💸 BAYAR Rp. {total_bet_rupiah}\n"
                f"💰 SALDO Rp. {saldo}\n"
                f"⌚ {wib()}"
            )
            kirim_telegram_log(pesan_gagal)

            try:
                context.close()
                browser.close()
            except:
                pass
            continue

    return 1 if ada_error else 0

if __name__ == "__main__":
    with sync_playwright() as playwright:
        exit_code = run(playwright)
        sys.exit(exit_code)
