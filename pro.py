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

VERSION = "1.1 (Patched)"

def banner():
    print(Fore.CYAN + "=" * 70)
    print(Fore.CYAN + " Profile OSINT Tool – Advanced Profile Information Gathering")
    print(Fore.CYAN + " " * 20 + f"Version: {VERSION}")
    print(Fore.CYAN + "=" * 70)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Profile OSINT Tool - Extract information from social media profile URL"
    )
    parser.add_argument("-u", "--url", required=True, help="Full URL of the profile page")
    parser.add_argument("-o", "--output", help="Output file (JSON/CSV). Example: result.json")
    parser.add_argument("-p", "--proxy", help="Proxy server (http://proxy:port)")
    parser.add_argument("-t", "--tor", action="store_true", help="Use Tor (SOCKS5 on 127.0.0.1:9050)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser.parse_args()

def get_profile_info(url, tor=False, proxy=None, verbose=False):
    if tor:
        try:
            import socks
            import socket
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socket.socket = socks.socksocket
            if verbose: print(Fore.YELLOW + "[+] Tor Proxy Activated.")
        except ImportError:
            print(Fore.RED + "[-] socks module not installed; run: pip3 install PySocks")

    proxies = {"http": proxy, "https": proxy} if proxy else None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    if verbose: print(Fore.YELLOW + f"[+] Scraping profile from: {url}")

    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(Fore.RED + f"[-] Error: {e}")
        return None

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        # تنظيف النص لضمان فحص دقيق
        text = soup.get_text(separator=' ') 

        # 1. استخراج اسم المستخدم (Username)
        username = "Unknown"
        patterns = [
            r"instagram\.com/([^/?#]+)",
            r"tiktok\.com/@([^/?#]+)",
            r"x\.com/([^/?#]+)",
            r"youtube\.com/@([^/?#]+)",
            r"facebook\.com/([^/?#]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                username = match.group(1)
                break

        # 2. تحسين Regex الإيميل
        email_list = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        email = email_list[0] if email_list else "Not Found"

        # 3. تصحيح Regex رقم الهاتف (كان يحتوي على خطأ في صياغة d)
        phone_list = re.findall(r"\+?\d{9,15}", text)
        phone = phone_list[0] if phone_list else "Not Found"

        # 4. تصحيح Regex الروابط الخارجية
        links = re.findall(r"https?://[^\s'\"<>]+", text[:5000])
        
        # تصفية الروابط لاستخراج الموقع الشخصي فقط
        exclude = ["instagram.com", "tiktok.com", "x.com", "youtube.com", "facebook.com", "t.co", "bit.ly"]
        website = "Not Found"
        for ln in links:
            if not any(dom in ln for dom in exclude):
                website = ln
                break

        # 5. بناء التقرير
        profile = {
            "platform": "Unknown",
            "username": username,
            "email": email,
            "phone": phone,
            "website": website,
            "scraped_at": str(datetime.now())
        }

        # تحديد المنصة
        for platform in ["Instagram", "TikTok", "YouTube", "Facebook"]:
            if platform.lower() in url:
                profile["platform"] = platform
        if "x.com" in url or "twitter.com" in url: profile["platform"] = "X (Twitter)"

        return profile
    return None

def main():
    banner()
    args = parse_args()

    profile = get_profile_info(args.url, args.tor, args.proxy, args.verbose)

    if profile:
        print(f"\n{Fore.GREEN}" + "-" * 50)
        print(f"{Fore.CYAN} Profile OSINT Results")
        print(f"{Fore.GREEN}" + "-" * 50)
        for key, value in profile.items():
            print(f"{Fore.YELLOW}{key.capitalize()}: {Fore.WHITE}{value}")
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=4)
            print(f"\n{Fore.GREEN}[+] Data saved to {args.output}")

if __name__ == "__main__":
    main()
