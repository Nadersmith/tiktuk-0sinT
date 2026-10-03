#!/usr/bin/env python3

"""
TikTok OSINT Pro - Advanced Intelligence Gathering Tool
Version: 2.0 Professional Edition
Author: Your Name
License: MIT
"""

import os
import re
import json
import csv
import time
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

VERSION = "2.0 Pro"
CACHE_DB = "osint_cache.db"
LOG_FILE = "osint_logs.txt"
RATE_LIMIT_DELAY = 2  # seconds between requests
REQUEST_TIMEOUT = 15

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== DATABASE UTILITIES ====================

class CacheManager:
    """Manages local caching of profiles to avoid redundant requests"""
    
    def __init__(self, db_path=CACHE_DB):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize SQLite database"""
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
        """Get cached profile if exists and not expired"""
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
        """Save profile to cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO profiles (username, data) VALUES (?, ?)",
                (username, json.dumps(data))
            )
            conn.commit()

# ==================== HTTP CLIENT ====================

class OsintClient:
    """Robust HTTP client with retry logic and proper headers"""
    
    def __init__(self, proxy=None, use_tor=False):
        self.session = requests.Session()
        self.proxy = proxy
        self.use_tor = use_tor
        self.setup_session()
    
    def setup_session(self):
        """Setup session with retry strategy"""
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Setup Tor if requested
        if self.use_tor:
            self.session.proxies = {
                "http": "socks5://127.0.0.1:9050",
                "https": "socks5://127.0.0.1:9050"
            }
            logger.info("Tor proxy activated")
        elif self.proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
            logger.info(f"Proxy set to: {self.proxy}")
    
    def get(self, url, headers=None):
        """Make GET request with proper headers"""
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        if headers:
            default_headers.update(headers)
        
        try:
            response = self.session.get(url, headers=default_headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

# ==================== DATA EXTRACTION ====================

class TikTokExtractor:
    """Extract information from TikTok profiles"""
    
    def __init__(self, client):
        self.client = client
    
    def extract_from_url(self, username):
        """Extract profile information from TikTok URL"""
        url = f"https://www.tiktok.com/@{username}"
        
        logger.info(f"Fetching profile: {username}")
        response = self.client.get(url)
        
        if not response:
            return None
        
        if response.status_code != 200:
            logger.warning(f"HTTP {response.status_code} for {username}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        profile_data = {
            "username": username,
            "profile_url": url,
            "scraped_at": datetime.now().isoformat()
        }
        
        # Extract from meta tags
        profile_data.update(self._extract_meta_tags(soup))
        
        # Extract bio info
        profile_data.update(self._extract_bio_info(soup))
        
        # Extract structured data
        profile_data.update(self._extract_json_ld(soup))
        
        # Extract social links from bio
        profile_data["social_links"] = self._extract_links(soup)
        
        return profile_data
    
    def _extract_meta_tags(self, soup):
        """Extract information from meta tags"""
        data = {}
        
        # Open Graph tags
        og_tags = {
            "og:title": "display_name",
            "og:description": "bio",
            "og:image": "avatar_url"
        }
        
        for meta_name, key in og_tags.items():
            tag = soup.find("meta", property=meta_name)
            if tag and tag.get("content"):
                data[key] = tag.get("content")
        
        return data
    
    def _extract_bio_info(self, soup):
        """Extract information from bio section"""
        data = {}
        
        # Look for verification badge
        data["verified"] = bool(soup.find("svg", {"data-e2e": "verified"}))
        
        # Extract follower/following counts from JSON-LD or structured data
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict):
                    if "interactionStatistic" in json_data:
                        for stat in json_data["interactionStatistic"]:
                            if "UserFollows" in stat.get("interactionType", ""):
                                data["followers"] = stat.get("userInteractionCount")
                            elif "UserLikes" in stat.get("interactionType", ""):
                                data["likes"] = stat.get("userInteractionCount")
            except:
                continue
        
        return data
    
    def _extract_json_ld(self, soup):
        """Extract JSON-LD structured data"""
        data = {}
        
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict) and json_data.get("@type") == "Person":
                    data["name"] = json_data.get("name")
                    data["description"] = json_data.get("description")
                    data["image"] = json_data.get("image")
            except:
                continue
        
        return data
    
    def _extract_links(self, soup):
        """Extract external links from profile"""
        links = []
        
        # Find all links in the page
        all_links = soup.find_all("a", href=True)
        
        excluded_domains = ["tiktok.com", "instagram.com", "twitter.com", "facebook.com", "t.co", "bit.ly"]
        
        for link in all_links:
            href = link.get("href", "")
            if href.startswith("http"):
                domain = urlparse(href).netloc
                if not any(exc in domain for exc in excluded_domains):
                    links.append({
                        "text": link.get_text(strip=True),
                        "url": href
                    })
        
        return links[:5]  # Limit to 5 links
    
    def extract_email_phone(self, text):
        """Extract email and phone from text (with better patterns)"""
        data = {}
        
        # Email pattern
        emails = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            text
        )
        data["emails"] = list(set(emails)) if emails else []
        
        # Phone pattern (international)
        phones = re.findall(
            r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            text
        )
        data["phones"] = [''.join(p) for p in phones] if phones else []
        
        return data

# ==================== REPORTING ====================

class ReportGenerator:
    """Generate reports in multiple formats"""
    
    @staticmethod
    def to_json(data, output_file):
        """Export to JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"JSON report saved: {output_file}")
    
    @staticmethod
    def to_csv(data_list, output_file):
        """Export to CSV"""
        if not data_list:
            return
        
        keys = data_list[0].keys()
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data_list)
        logger.info(f"CSV report saved: {output_file}")
    
    @staticmethod
    def to_html(data_list, output_file):
        """Export to HTML report"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>TikTok OSINT Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                h1 { color: #ff0050; }
                .profile { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .field { margin: 10px 0; }
                .label { font-weight: bold; color: #333; }
                .value { color: #666; word-break: break-all; }
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #ff0050; color: white; }
                tr:nth-child(even) { background-color: #f9f9f9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎵 TikTok OSINT Report</h1>
                <p>Generated: {}</p>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        for profile in data_list:
            html += """
                <div class="profile">
                    <h2>@{}</h2>
            """.format(profile.get("username", "Unknown"))
            
            for key, value in profile.items():
                if key not in ["username", "scraped_at"] and value:
                    if isinstance(value, list):
                        value = ", ".join([str(v) for v in value])
                    html += f"""
                    <div class="field">
                        <span class="label">{key.replace('_', ' ').title()}:</span>
                        <span class="value">{value}</span>
                    </div>
                    """
            
            html += "</div>"
        
        html += """
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"HTML report saved: {output_file}")

# ==================== MAIN APPLICATION ====================

class TikTokOsintPro:
    """Main application class"""
    
    def __init__(self, proxy=None, use_tor=False, verbose=False):
        self.client = OsintClient(proxy=proxy, use_tor=use_tor)
        self.extractor = TikTokExtractor(self.client)
        self.cache = CacheManager()
        self.verbose = verbose
    
    def investigate_user(self, username, use_cache=True):
        """Investigate a single TikTok user"""
        
        # Check cache first
        if use_cache:
            cached = self.cache.get_cached(username)
            if cached:
                logger.info(f"Using cached data for: {username}")
                return cached
        
        # Extract fresh data
        profile = self.extractor.extract_from_url(username)
        
        if profile:
            # Save to cache
            self.cache.save_cache(username, profile)
        
        # Add rate limiting
        time.sleep(RATE_LIMIT_DELAY)
        
        return profile
    
    def investigate_batch(self, usernames, use_cache=True):
        """Investigate multiple users"""
        results = []
        
        for i, username in enumerate(usernames, 1):
            print(f"\n{Fore.CYAN}[{i}/{len(usernames)}] Investigating: @{username}")
            profile = self.investigate_user(username, use_cache)
            
            if profile:
                results.append(profile)
                self._display_profile(profile)
            else:
                print(f"{Fore.RED}[-] Failed to retrieve profile")
        
        return results
    
    def _display_profile(self, profile):
        """Display profile information in terminal"""
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"{Fore.CYAN}Profile: @{profile.get('username', 'Unknown')}")
        print(f"{Fore.GREEN}{'='*60}")
        
        display_fields = [
            ("Display Name", "display_name"),
            ("Bio", "bio"),
            ("Verified", "verified"),
            ("Followers", "followers"),
            ("Likes", "likes"),
            ("Avatar", "avatar_url"),
            ("Social Links", "social_links"),
            ("Scraped At", "scraped_at")
        ]
        
        for label, key in display_fields:
            value = profile.get(key)
            if value:
                if isinstance(value, list):
                    value = "\n  - " + "\n  - ".join([str(v) for v in value])
                print(f"{Fore.YELLOW}{label}: {Fore.WHITE}{value}")
        
        print(f"{Fore.GREEN}{'='*60}\n")

def banner():
    """Display ASCII banner"""
    print(f"""{Fore.CYAN}
    ╔══════════════════════════════════════════════════════════╗
    ║        TikTok OSINT Pro v{VERSION}                   ║
    ║      Advanced Intelligence Gathering Tool              ║
    ║                                                          ║
    ║  Professional • Fast • Reliable • Privacy-Focused       ║
    ╚══════════════════════════════════════════════════════════╝
    {Style.RESET_ALL}
    """)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="TikTok OSINT Pro - Advanced profile investigation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single user investigation
  python3 tiktok_osint_pro.py -u username
  
  # Batch investigation with report
  python3 tiktok_osint_pro.py -f usernames.txt -o report.json
  
  # Using Tor for privacy
  python3 tiktok_osint_pro.py -u username --tor
  
  # Generate HTML report
  python3 tiktok_osint_pro.py -u username --html report.html
        """
    )
    
    parser.add_argument("-u", "--username", help="Single TikTok username")
    parser.add_argument("-f", "--file", help="File with usernames (one per line)")
    parser.add_argument("-o", "--output", help="Output file (json/csv)")
    parser.add_argument("--html", help="Generate HTML report")
    parser.add_argument("-p", "--proxy", help="Proxy server (http://ip:port)")
    parser.add_argument("--tor", action="store_true", help="Use Tor SOCKS5 proxy")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-cache", action="store_true", help="Don't use cached data")
    
    return parser.parse_args()

def main():
    """Main function"""
    banner()
    args = parse_arguments()
    
    # Initialize OSINT tool
    osint = TikTokOsintPro(proxy=args.proxy, use_tor=args.tor, verbose=args.verbose)
    
    usernames = []
    
    # Get usernames
    if args.username:
        usernames = [args.username]
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                usernames = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"{Fore.RED}[-] File not found: {args.file}")
            return
    else:
        print(f"{Fore.RED}[-] Please provide username (-u) or file (-f)")
        return
    
    # Investigate users
    results = osint.investigate_batch(usernames, use_cache=not args.no_cache)
    
    # Generate reports
    if results:
        if args.output:
            if args.output.endswith('.csv'):
                ReportGenerator.to_csv(results, args.output)
            else:
                ReportGenerator.to_json(results, args.output)
        
        if args.html:
            ReportGenerator.to_html(results, args.html)
        
        print(f"\n{Fore.GREEN}[+] Investigation complete! Found {len(results)} profiles")
    else:
        print(f"\n{Fore.RED}[-] No profiles retrieved")

if __name__ == "__main__":
    main()
