#!/usr/bin/env python3

"""
tiktuk-osint – Advanced TikTok OSINT Tool
Designed for Kali Linux / Kali NetHunter (Termux)
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
    print(Fore.CYAN + " tiktuk-osint – Advanced TikTok OSINT Tool")
    print(Fore.CYAN + " " * 20 + f"Version: {VERSION}")
    print(Fore.CYAN + "=" * 70)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Advanced TikTok OSINT Tool: Extract account information and OSINT data"
    )
    parser.add_argument(
        "-u", "--username", required=True,
        help="TikTok username to investigate (e.g. selcherbny)"
    )
    parser.add_argument(
        "-f", "--file",
        help="File containing list of TikTok usernames (one per line)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (CSV/JSON/HTML). Example: tiktok_results.csv"
    )
    parser.add_argument(
        "-r", "--report",
        action="store_true",
        help="Generate a complete report (JSON + CSV + HTML)"
    )
    parser.add_argument(
        "-p", "--proxy",
        help="Proxy server (e.g. http://127.0.0.1:8080)"
    )
    parser.add_argument(
        "-t", "--tor",
        action="store_true",
        help="Use Tor (requires torsocks or SOCKS5 on 127.0.0.1:9050)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    return parser.parse_args()

def get_tiktok_profile(username, tor=False, proxy=None, verbose=False):
    """
    Scrape TikTok profile for:
    - email, phone, website
    - followers, likes, videos (if available in HTML)
    - creation date, region, language (basic extraction)
    """
    base_url = f"https://www.tiktok.com/@{username}"

    if tor:
        try:
            import socks
            import socket
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socket.socket = socks.socksocket
        except ImportError:
            print(Fore.RED + "[-] socks module not installed; run: pip3 install PySocks")

    if proxy:
        proxies = {"http": proxy, "https": proxy}
    else:
        proxies = None

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "https://www.tiktok.com/",
    }

    if verbose:
        print(Fore.YELLOW + f"[+] Scraping TikTok profile for: {username}")

    try:
        response = requests.get(base_url, headers=headers, proxies=proxies, timeout=15)
    except Exception as e:
        print(Fore.RED + f"[-] Error connecting to TikTok: {e}")
        return None

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Email
        email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}", soup.text)
        email = email[0] if email else None

        # 2. Phone number
        phone = re.findall(r"+?d{9,15}", soup.text)
        phone = phone[0] if phone else None

        # 3. External links (website)
        links = re.findall(r"https?://[^'"<> ]+", soup.text[:3000])
        website = [ln for ln in links if "tiktok.com" not in ln]
        website = website[0] if website else None

        # 4. Account info (basic extraction)
        followers = None
        likes = None
        videos = None
        creation_date = None
        region = None
        language = None
        interactive_videos = None

        # 5. Try to find followers, likes, videos (TikTok HTML may change)
        # You can adjust these regex patterns later:
        followers_text = re.search(r"Followerss*[:s]*(S+)", soup.text, re.IGNORECASE)
        if followers_text:
            followers = followers_text.group(1)

        likes_text = re.search(r"Likess*[:s]*(S+)", soup.text, re.IGNORECASE)
        if likes_text:
            likes = likes_text.group(1)

        videos_text = re.search(r"Videoss*[:s]*(S+)", soup.text, re.IGNORECASE)
        if videos_text:
            videos = videos_text.group(1)

        # 6. Basic profile object
        profile = {
            "username": username,
            "followers": followers,
            "likes": likes,
            "videos": videos,
            "creation_date": creation_date,
            "region": region,
            "language": language,
            "interactive_videos": interactive_videos,
            "email": email,
            "phone": phone,
            "website": website,
            "scraped_at": str(datetime.now())
        }

        if verbose:
            print(Fore.GREEN + f"[+] Profile scraped for: {username}")

        return profile

    else:
        print(Fore.RED + f"[-] Profile not found or rate limited for: {username}")
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

def write_report_html(data):
    if not data:
        return

    table_start = "<table border='1' cellpadding='5' cellspacing='0'>"
    header = "<thead><tr>"
    for key in data[0].keys():
        header += f"<th>{key}</th>"
    header += "</tr></thead>"

    rows = "<tbody>"
    for row in data:
        rows += "<tr>"
        for key in row.keys():
            rows += f"<td>{row[key]}</td>"
        rows += "</tr>"
    rows += "</tbody></table>"

    html = f"""
    <!DOCTYPE html><html><head>
    <title>TikTok OSINT Report – tiktuk-osint</title>
    <style>body {{ font-family: Arial, sans-serif; margin: 20px; }}
    th {{ background-color: #f2f2f2; text-align: left; padding: 8px; }}
    td {{ padding: 6px; }}table {{ border-collapse: collapse; width: 100%; }}
    </style></head><body><h1>TikTok OSINT Report</h1>
    {table_start}{header}{rows}
    </body></html>
    """

    filename = "tiktuk-osint_report.html"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(html)
    print(Fore.GREEN + f"[+] HTML report written to: {filename}")

def main():
    banner()
    args = parse_args()

    # Single username
    if args.username:
        profile = get_tiktok_profile(
            username=args.username,
            tor=args.tor,
            proxy=args.proxy,
            verbose=args.verbose
        )
        if profile:
            print(Fore.GREEN + "
" + "-" * 50)
            print(Fore.CYAN + " TikTok OSINT Advanced Results")
            print(Fore.GREEN + "-" * 50)
            for key, value in profile.items():
                print(f"{key.capitalize()}: {value}")

            if args.output:
                write_json([profile], args.output)
            elif args.report:
                write_json([profile], "tiktok_osint_results.json")
                write_report_html([profile])

    # Multiple usernames from file
    if args.file:
        all_profiles = []
        with open(args.file, "r", encoding="utf-8") as file:
            usernames = [line.strip() for line in file if line.strip()]

        for username in usernames:
            profile = get_tiktok_profile(
                username=username,
                tor=args.tor,
                proxy=args.proxy,
                verbose=args.verbose
            )
            if profile:
                all_profiles.append(profile)

        if all_profiles:
            if args.output and args.output.endswith(".csv"):
                write_csv(all_profiles, args.output)
            elif args.output and args.output.endswith(".json"):
                write_json(all_profiles, args.output)
            elif args.report:
                write_csv(all_profiles, "tiktok_osint_results.csv")
                write_json(all_profiles, "tiktok_osint_results.json")
                write_report_html(all_profiles)

if __name__ == "__main__":
    main()
