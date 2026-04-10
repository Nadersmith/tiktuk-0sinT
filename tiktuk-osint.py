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
    base_url = f"https://www.tiktok.com/@{username}"

    if tor:
        try:
            import socks
            import socket
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socket.socket = socks.socksocket
        except ImportError:
            print(Fore.RED + "[-] socks module not installed; run: pip3 install PySocks")

    proxies = {"http": proxy, "https": proxy} if proxy else None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
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
        text = soup.get_text()

        # Regex corrections
        email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        email = email[0] if email else "Not Found"

        phone = re.findall(r"\+?\d{9,15}", text)
        phone = phone[0] if phone else "Not Found"

        links = re.findall(r"https?://[^\s'\"<>]+", text[:5000])
        website = [ln for ln in links if "tiktok.com" not in ln]
        website = website[0] if website else "Not Found"

        profile = {
            "username": username,
            "email": email,
            "phone": phone,
            "website": website,
            "scraped_at": str(datetime.now())
        }

        if verbose:
            print(Fore.GREEN + f"[+] Profile scraped for: {username}")
        return profile
    else:
        print(Fore.RED + f"[-] Profile not found or rate limited (Status: {response.status_code})")
        return None

def write_report_html(data):
    if not data: return
    
    table_content = ""
    for row in data:
        table_content += "<tr>"
        for val in row.values():
            table_content += f"<td>{val}</td>"
        table_content += "</tr>"

    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>TikTok OSINT Report</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #f4f4f4; }}
        table {{ border-collapse: collapse; width: 100%; background: white; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #ff0050; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>TikTok OSINT Report</h1>
    <table>
        <thead>
            <tr>{" ".join([f"<th>{k.upper()}</th>" for k in data[0].keys()])}</tr>
        </thead>
        <tbody>
            {table_content}
        </tbody>
    </table>
</body>
</html>"""

    with open("tiktuk-osint_report.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print(Fore.GREEN + "[+] HTML report written to: tiktuk-osint_report.html")

def main():
    banner()
    args = parse_args()
    results = []

    if args.username:
        profile = get_tiktok_profile(args.username, args.tor, args.proxy, args.verbose)
        if profile:
            results.append(profile)
            print(Fore.GREEN + "\n" + "-"*30)
            for k, v in profile.items(): print(f"{Fore.CYAN}{k.capitalize()}: {Fore.WHITE}{v}")
            print(Fore.GREEN + "-"*30)

    if args.report and results:
        write_report_html(results)

if __name__ == "__main__":
    main()
