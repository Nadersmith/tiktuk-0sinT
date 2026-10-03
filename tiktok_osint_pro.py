#!/usr/bin/env python3

"""
TikTok OSINT Pro v2.1 - Advanced Intelligence Gathering Tool
Enhanced: browser-grade headers, rehydration-JSON parsing,
yt-dlp fallback, cookie support, Tor via socks5.
"""

import os
import re
import sys
import json
import csv
import time
import random
import logging
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import colorama
from colorama import Fore, Style
from bs4 import BeautifulSoup
import sqlite3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==================== CONFIGURATION ====================

colorama.init(autoreset=True)

VERSION = "2.1 Enhanced"
CACHE_DB = "osint_cache.db"
LOG_FILE = "osint_logs.txt"
RATE_LIMIT_DELAY = 3
REQUEST_TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BROWSER_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# ==================== DATABASE ====================

class CacheManager:
    def __init__(self, db_path=CACHE_DB):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    username TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_cached(self, username, max_age_hours=24):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data, timestamp FROM profiles WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            if result:
                data, timestamp = result
                cache_time = datetime.fromisoformat(timestamp)
                if datetime.now() - cache_time < timedelta(hours=max_age_hours):
                    return json.loads(data)
        return None

    def save_cache(self, username, data):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO profiles (username, data) VALUES (?, ?)",
                (username, json.dumps(data))
            )
            conn.commit()

# ==================== HTTP CLIENT ====================

class OsintClient:
    """Browser-fingerprinted HTTP client with cookie + proxy support."""

    def __init__(self, proxy=None, use_tor=False, cookies_file=None):
        self.session = requests.Session()
        self.proxy = proxy
        self.use_tor = use_tor
        self.cookies_file = cookies_file
        self.setup_session()

    def setup_session(self):
        retry_strategy = Retry(
            total=2,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "User-Agent": random.choice(BROWSER_UAS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "sec-ch-ua": '"Chromium";v="126", "Google Chrome";v="126", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        })

        if self.use_tor:
            self.session.proxies = {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050",
            }
            logger.info("Tor proxy activated (socks5h://127.0.0.1:9050)")
        elif self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}
            logger.info(f"Proxy set to: {self.proxy}")

        if self.cookies_file and os.path.exists(self.cookies_file):
            try:
                from http.cookiejar import MozillaCookieJar
                jar = MozillaCookieJar(self.cookies_file)
                jar.load(ignore_discard=True, ignore_expires=True)
                self.session.cookies.update(jar)
                logger.info(f"Cookies loaded from: {self.cookies_file}")
            except Exception as e:
                logger.warning(f"Could not load cookies: {e}")

    def get(self, url, headers=None):
        h = dict(self.session.headers)
        if headers:
            h.update(headers)
        try:
            response = self.session.get(url, headers=h, timeout=REQUEST_TIMEOUT)
            return response
        except requests.exceptions.ProxyError as e:
            logger.error(f"Proxy error ({url}): {e} - check Tor/proxy is running")
            return None
        except requests.exceptions.SSLError as e:
            logger.error(f"TLS error ({url}): {e} - TikTok may be blocking your IP/fingerprint")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection failed ({url}): {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ({url}) after {REQUEST_TIMEOUT}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

# ==================== EXTRACTION ====================

class TikTokExtractor:
    def __init__(self, client):
        self.client = client

    def extract(self, username):
        """Try direct scrape first, fall back to yt-dlp."""
        data = self._scrape(username)
        if not data:
            data = self._fetch_ytdlp(username)
        if data:
            data["username"] = username
            data["profile_url"] = f"https://www.tiktok.com/@{username}"
            data["scraped_at"] = datetime.now().isoformat()
        return data

    # ---- Method 1: parse embedded rehydration JSON ----
    def _scrape(self, username):
        url = f"https://www.tiktok.com/@{username}"
        logger.info(f"Fetching profile: {username}")
        resp = self.client.get(url)
        if not resp:
            return None

        if resp.status_code in (403, 404):
            logger.warning(f"HTTP {resp.status_code} for @{username} (blocked or not found)")
            return None

        if "captcha" in resp.text.lower() or "verify" in resp.url.lower():
            logger.warning("TikTok served a captcha/verify page - IP is likely flagged. Use Tor or a proxy.")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        data = {}

        script = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
        if script and script.string:
            try:
                raw = json.loads(script.string)
                scope = raw.get("__DEFAULT_SCOPE__", {})
                user_detail = scope.get("webapp.user-detail", {})
                user_info = user_detail.get("userInfo") or {}
                user = user_info.get("user") or {}
                stats = user_info.get("stats") or {}
                stats_v2 = user_info.get("statsV2") or {}

                def pick(*vals):
                    for v in vals:
                        if v is not None and v != "":
                            return v
                    return None

                data.update({
                    "user_id": pick(user.get("id"), user.get("uid")),
                    "nickname": pick(user.get("nickname")),
                    "bio": pick(user.get("signature")),
                    "verified": bool(user.get("verified")),
                    "private": bool(user.get("privateAccount")),
                    "region": pick(user.get("region")),
                    "language": pick(user.get("language")),
                    "avatar_url": pick(user.get("avatarLarger"), user.get("avatarMedium")),
                    "followers": pick(stats_v2.get("followerCount"), stats.get("followerCount")),
                    "following": pick(stats_v2.get("followingCount"), stats.get("followingCount")),
                    "likes": pick(stats_v2.get("heartCount"), stats.get("heartCount")),
                    "videos": pick(stats_v2.get("videoCount"), stats.get("videoCount")),
                })

                ct = user.get("createTime")
                if ct:
                    try:
                        data["account_created"] = datetime.fromtimestamp(int(ct)).isoformat()
                    except Exception:
                        pass

                bio_link = user.get("bioLink") or {}
                if bio_link.get("link"):
                    data["bio_link"] = bio_link["link"]

                if user_detail.get("statusMsg") and not user:
                    logger.warning(f"TikTok API status: {user_detail['statusMsg']}")
            except json.JSONDecodeError:
                logger.warning("Could not parse rehydration JSON")

        # Meta tags fallback
        if not data.get("nickname"):
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                data["nickname"] = og["content"]
        if not data.get("bio"):
            og = soup.find("meta", property="og:description")
            if og and og.get("content"):
                data["bio"] = og["content"]
        if not data.get("avatar_url"):
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                data["avatar_url"] = og["content"]

        # Public bio email/phone extraction (only what the user published)
        if data.get("bio"):
            found = self.extract_contact_from_text(data["bio"])
            if found.get("emails"):
                data["public_emails_in_bio"] = found["emails"]
            if found.get("phones"):
                data["public_phones_in_bio"] = found["phones"]

        return data if data.get("user_id") or data.get("nickname") else None

    # ---- Method 2: yt-dlp fallback ----
    def _fetch_ytdlp(self, username):
        try:
            import yt_dlp
        except ImportError:
            return None
        url = f"https://www.tiktok.com/@{username}"
        logger.info("Trying yt-dlp fallback...")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": REQUEST_TIMEOUT,
            "retries": 3,
        }
        if self.client.use_tor:
            opts["proxy"] = "socks5://127.0.0.1:9050"
        elif self.client.proxy:
            opts["proxy"] = self.client.proxy

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                return None
            return {
                "user_id": info.get("channel_id") or info.get("uploader_id"),
                "nickname": info.get("uploader") or info.get("title"),
                "bio": info.get("description"),
                "followers": info.get("channel_follower_count"),
                "avatar_url": info.get("uploader_avatar") or info.get("thumbnail"),
                "source": "yt-dlp",
            }
        except Exception as e:
            logger.warning(f"yt-dlp fallback failed: {e}")
            return None

    @staticmethod
    def extract_contact_from_text(text):
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
        phones = re.findall(r'(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){9,14}', text)
        return {
            "emails": sorted(set(emails)),
            "phones": sorted(set(p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 9)),
        }

# ==================== REPORTING ====================

class ReportGenerator:
    @staticmethod
    def to_json(data, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"JSON report saved: {output_file}")

    @staticmethod
    def to_csv(data_list, output_file):
        if not data_list:
            return
        keys = sorted({k for row in data_list for k in row.keys()})
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            for row in data_list:
                writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
        logger.info(f"CSV report saved: {output_file}")

    @staticmethod
    def to_html(data_list, output_file):
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>TikTok OSINT Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
.container {{ max-width: 1100px; margin: 0 auto; }}
h1 {{ color: #ff0050; }}
.profile {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.field {{ margin: 8px 0; }}
.label {{ font-weight: bold; color: #333; }}
.value {{ color: #666; word-break: break-all; }}
img.avatar {{ max-width: 120px; border-radius: 50%; }}
</style></head><body><div class="container">
<h1>TikTok OSINT Report</h1>
<p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
"""
        for p in data_list:
            html += f'<div class="profile"><h2>@{p.get("username", "Unknown")}</h2>'
            if p.get("avatar_url"):
                html += f'<img class="avatar" src="{p["avatar_url"]}" alt="avatar">'
            for key, value in p.items():
                if key in ("username", "avatar_url") or value in (None, "", []):
                    continue
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                html += f'<div class="field"><span class="label">{key.replace("_", " ").title()}:</span> <span class="value">{value}</span></div>'
            html += "</div>"
        html += "</div></body></html>"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"HTML report saved: {output_file}")

# ==================== MAIN APP ====================

class TikTokOsintPro:
    def __init__(self, proxy=None, use_tor=False, cookies_file=None, verbose=False):
        self.client = OsintClient(proxy=proxy, use_tor=use_tor, cookies_file=cookies_file)
        self.extractor = TikTokExtractor(self.client)
        self.cache = CacheManager()
        self.verbose = verbose

    def investigate_user(self, username, use_cache=True):
        username = username.lstrip("@").strip()
        if use_cache:
            cached = self.cache.get_cached(username)
            if cached:
                logger.info(f"Using cached data for: {username}")
                return cached
        profile = self.extractor.extract(username)
        if profile:
            self.cache.save_cache(username, profile)
        time.sleep(RATE_LIMIT_DELAY + random.uniform(0, 2))
        return profile

    def investigate_batch(self, usernames, use_cache=True):
        results = []
        for i, username in enumerate(usernames, 1):
            print(f"\n{Fore.CYAN}[{i}/{len(usernames)}] Investigating: @{username.lstrip('@')}")
            profile = self.investigate_user(username, use_cache)
            if profile:
                results.append(profile)
                self._display_profile(profile)
            else:
                print(f"{Fore.RED}[-] Failed to retrieve profile")
        return results

    def _display_profile(self, profile):
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"{Fore.CYAN}Profile: @{profile.get('username', 'Unknown')}")
        print(f"{Fore.GREEN}{'='*60}")
        order = ["user_id", "nickname", "bio", "verified", "private", "followers",
                 "following", "likes", "videos", "region", "language",
                 "account_created", "bio_link", "public_emails_in_bio",
                 "public_phones_in_bio", "avatar_url", "source", "scraped_at"]
        for key in order:
            value = profile.get(key)
            if value not in (None, "", []):
                print(f"{Fore.YELLOW}{key.replace('_',' ').title()}: {Fore.WHITE}{value}")
        print(f"{Fore.GREEN}{'='*60}\n")

def banner():
    print(f"""{Fore.CYAN}
    ╔══════════════════════════════════════════════════════════╗
    ║        TikTok OSINT Pro v{VERSION}                 ║
    ║      Advanced Intelligence Gathering Tool              ║
    ║                                                          ║
    ║  Professional • Fast • Reliable • Privacy-Focused       ║
    ╚══════════════════════════════════════════════════════════╝
    {Style.RESET_ALL}""")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="TikTok OSINT Pro - Advanced profile investigation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tiktok_osint_pro_v21.py -u axia.selsherbny
  python3 tiktok_osint_pro_v21.py -u axia.selsherbny --tor -o report.json --html report.html
  python3 tiktok_osint_pro_v21.py -u axia.selsherbny -p http://127.0.0.1:8080
  python3 tiktok_osint_pro_v21.py -f usernames.txt -o report.csv
  python3 tiktok_osint_pro_v21.py -u axia.selsherbny -c cookies.txt
        """
    )
    parser.add_argument("-u", "--username", help="Single TikTok username")
    parser.add_argument("-f", "--file", help="File with usernames (one per line)")
    parser.add_argument("-o", "--output", help="Output file (.json or .csv)")
    parser.add_argument("--html", help="Generate HTML report file")
    parser.add_argument("-p", "--proxy", help="Proxy (http://ip:port or socks5://ip:port)")
    parser.add_argument("--tor", action="store_true", help="Use Tor (socks5h://127.0.0.1:9050)")
    parser.add_argument("-c", "--cookies", help="Netscape-format cookies.txt from browser")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cache")
    return parser.parse_args()

def main():
    banner()
    args = parse_arguments()

    if args.tor:
        try:
            import socks  # noqa: F401  (requests[socks])
        except ImportError:
            print(f"{Fore.RED}[-] Tor requires: sudo pip3 install requests[socks]")
            print(f"{Fore.YELLOW}[i] And make sure Tor service is running: sudo service tor start")
            sys.exit(1)

    osint = TikTokOsintPro(proxy=args.proxy, use_tor=args.tor,
                           cookies_file=args.cookies, verbose=args.verbose)

    if args.username:
        usernames = [args.username]
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                usernames = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"{Fore.RED}[-] File not found: {args.file}")
            sys.exit(1)
    else:
        print(f"{Fore.RED}[-] Provide username (-u) or file (-f)")
        sys.exit(1)

    results = osint.investigate_batch(usernames, use_cache=not args.no_cache)

    if results:
        if args.output:
            if args.output.endswith('.csv'):
                ReportGenerator.to_csv(results, args.output)
            else:
                ReportGenerator.to_json(results, args.output)
        if args.html:
            ReportGenerator.to_html(results, args.html)
        print(f"\n{Fore.GREEN}[+] Done! Retrieved {len(results)} profile(s)")
    else:
        print(f"\n{Fore.RED}[-] No profiles retrieved")
        print(f"{Fore.YELLOW}[i] Likely causes: your IP is blocked by TikTok, or no Tor/proxy running.")
        print(f"{Fore.YELLOW}[i] Try: --tor   |   -p http://PROXY:PORT   |   -c cookies.txt")
        sys.exit(2)

if __name__ == "__main__":
    main()
