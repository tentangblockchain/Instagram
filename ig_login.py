import os, sys, json, time
os.environ['DISPLAY'] = ':99'

from playwright.sync_api import sync_playwright

COOKIES_FILE = os.path.join(os.path.dirname(__file__), 'instagram_cookies.txt')

def save_cookies(cookies):
    """Save cookies in Netscape format (for yt-dlp)"""
    with open(COOKIES_FILE, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# Instagram cookies for yt-dlp\n\n")
        for c in cookies:
            domain = c.get('domain', '')
            if 'instagram' not in domain and 'facebook' not in domain:
                continue
            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = c.get('path', '/')
            secure = 'TRUE' if c.get('secure') else 'FALSE'
            expires = str(int(c.get('expires', 0)))
            name = c.get('name', '')
            value = c.get('value', '')
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
    print(f"✅ Cookies saved to {COOKIES_FILE} ({len([c for c in cookies if 'instagram' in c.get('domain','')])} entries)")

def main():
    print("=" * 60)
    print("  Instagram Login - ONE TIME SETUP")
    print("=" * 60)
    print()
    print("Bot akan buka Chrome, kamu tinggal login Instagram.")
    print("Setelah login, cookies otomatis tersimpan.\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel='chrome')
        context = browser.new_context(viewport={'width': 1200, 'height': 800})
        page = context.new_page()
        
        page.goto('https://www.instagram.com/accounts/login/', timeout=60000)
        print("\n🔄 Login ke Instagram di Chrome yang terbuka...")
        print("   Setelah berhasil login, balik ke terminal ini dan tekan Enter.\n")
        
        # Wait for user to press Enter (meaning they've logged in)
        input("   ⏎ Tekan Enter setelah login selesai...")
        
        # Save all cookies
        cookies = context.cookies()
        save_cookies(cookies)
        
        # Verify login by checking if session is valid
        page.goto('https://www.instagram.com/', timeout=30000)
        if 'login' not in page.url.lower():
            print("✅ Session Instagram valid!")
        else:
            print("⚠️ Gagal login. Coba lagi.")
        
        browser.close()

if __name__ == '__main__':
    main()
