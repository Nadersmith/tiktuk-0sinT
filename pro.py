#!/usr/bin/env python3

"""
Profile OSINT Tool
Input: a URL to any social media profile
Output: gather OSINT details (email, phone, website, etc.)
Written for Kali Linux / Kali NetHunter (Termux)
"""

import os
import re
import json
import csv
import argparse
import requests
import colorama
from bs4 import BeautifulSoup
from datetime import datetime
from colorama import Fore

# Initialize colorama
colorama.init(autoreset=True)

VERSION = "1.0"

def banner():
    print(Fore.CYAN + "=" * 70)
    print(Fore.CYAN + " Profile OSINT Tool – Advanced Profile Information Gathering")
    print(Fore.CYAN + " " * 20 + f"Version: {VERSION}")
    print(Fore.CYAN + "=" * 70)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Profile OSINT Tool - Extract information from social media profile URL"
    )
    parser.add_argument(
        "-u", "--url", required=True,
        help="Full URL of the profile page (Instagram, TikTok, X, YouTube, etc.)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (JSON/CSV). Example: result.json"
    )
    parser.add_argument(
        "-p", "--proxy",
        help="Proxy server (http://proxy:port)"
    )
    parser.add_argument(
        "-t", "--tor",
        action="store_true",
        help="Use Tor (SOCKS5 on 127.0.0.1:9050)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    return parser.parse_args()

def get_profile_info(url, tor=False, proxy=None, verbose=False):
    """
    Gather OSINT information from any profile URL
    Supports TikTok, Instagram, X/Twitter, YouTube, Facebook...
    """
    # If Tor is enabled
    if tor:
        try:
            import socks
            import socket
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socket.socket = socks.socksocket
        except ImportError:
            print(Fore.RED + "[-] socks module not installed; run: pip3 install PySocks")

    # Set proxy
    if proxy:
        proxies = {"http": proxy, "https": proxy}
    else:
        proxies = None

    # Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    if verbose:
        print(Fore.YELLOW + f"[+] Scraping profile from: {url}")

    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
    except Exception as e:
        print(Fore.RED + f"[-] Error connecting to profile: {e}")
        return None

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.text  # Full text of page

        # 1. Extract username (from URL)
        username = None
        patterns = [
            r"instagram.com/([^/?]+)",
            r"tiktok.com/@([^/?]+)",
            r"x.com/([^/?]+)",
            r"youtube.com/@([^/?]+)",
            r"facebook.com/([^/?]+)",
            r"clubhouse.com/@([^/?]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                username = match.group(1)
                break

        # 2. Email
        email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}", text)
        email = email[0] if email else None

        # 3. Phone number
        phone = re.findall(r"+?d{9,15}", text)
        phone = phone[0] if phone else None

        # 4. Website / External links
        links = re.findall(r"https?://[^"'<>s]+", text[:3000])
        website = [ln for ln in links if not any(dom in ln for dom in ["instagram.com", "tiktok.com", "x.com", "youtube.com", "facebook.com"])]
        website = website[0] if website else None

        # 5. Social accounts links (possible related accounts)
        socials = []
        for domain in ["instagram.com", "tiktok.com", "x.com", "youtube.com", "facebook.com", "linkedin.com", "twitter.com"]:
            for ln in links:
                if domain in ln:
                    socials.append(ln)

        # 6. Build profile data
        profile = {
            "url": url,
            "platform": "Unknown",  # Can be improved later
            "username": username,
            "email": email,
            "phone": phone,
            "website": website,
            "social_accounts": socials,
            "scraped_at": str(datetime.now())
        }

        # Improve platform detection
        if "instagram.com" in url:
            profile["platform"] = "Instagram"
        elif "tiktok.com" in url:
            profile["platform"] = "TikTok"
        elif "x.com" in url or "twitter.com" in url:
            profile["platform"] = "X (Twitter)"
        elif "youtube.com" in url:
            profile["platform"] = "YouTube"
        elif "facebook.com" in url:
            profile["platform"] = "Facebook"
        elif "clubhouse.com" in url:
            profile["platform"] = "Clubhouse"

        if verbose:
            print(Fore.GREEN + f"[+] Profile info extracted from: {url}")

        return profile

    else:
        print(Fore.RED + f"[-] Page not found or rate limited for: {url}")
        return None

def write_csv(data, filename):
    if not data:
        return
    keys = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as file:
        dict_writer = csv.DictWriter(file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)
    print(Fore.GREEN + f"[+] Results written to: {filename}")

def write_json(data, filename):
    if not data:
        return
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    print(Fore.GREEN + f"[+] Results written to: {filename}")

def main():
    banner()
    args = parse_args()

    profile = get_profile_info(
        url=args.url,
        tor=args.tor,
        proxy=args.proxy,
        verbose=args.verbose
    )

    if profile:
        print(Fore.GREEN + "
" + "-" * 50)
        print(Fore.CYAN + " Profile OSINT Results")
        print(Fore.GREEN + "-" * 50)
        for key, value in profile.items():
            print(f"{key.capitalize()}: {value}")

        if args.output:
            write_json([profile], args.output)

if __name__ == "__main__":
    main()
