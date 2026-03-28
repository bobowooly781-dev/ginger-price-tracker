"""
scrape_ginger.py
Fetches the daily HEGI Ginger Carton (5kg) Grade 1 price from Cape Town Market
and appends it to prices.csv.
"""

import csv
import os
import sys
from datetime import date

import requests
from bs4 import BeautifulSoup

URL = "https://www.ctmarket.co.za/daily-prices/"
CSV_FILE = "prices.csv"
FIELDNAMES = ["date", "price_date", "low", "high", "average"]


def fetch_prices():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GingerPriceBot/1.0)"}
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_ginger_price(html):
    soup = BeautifulSoup(html, "html.parser")

    # Extract the price date from the heading, e.g. "Daily Statistical Prices For 27/03/2026"
    price_date = None
    for tag in soup.find_all(["h1", "h2", "h3", "p", "div"]):
        text = tag.get_text()
        if "Daily Statistical Prices For" in text:
            import re
            m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
            if m:
                d, mo, yr = m.group(1).split("/")
                price_date = f"{yr}-{mo}-{d}"
            break

    # Find the table and look for HEGI, Carton (5kg), Grade 1
    table = soup.find("table")
    if not table:
        raise ValueError("Price table not found on page.")

    for row in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 9:
            continue
        item_code = cells[0].upper()
        container = cells[2].lower()
        grade = cells[4].strip()
        if item_code == "HEGI" and "carton" in container and "5" in container and grade == "1":
            return {
                "date": str(date.today()),
                "price_date": price_date or "unknown",
                "low": cells[6],
                "high": cells[7],
                "average": cells[8],
            }

    raise ValueError("HEGI Ginger Carton (5kg) Grade 1 not found in today's prices.")


def already_recorded(today_str):
    if not os.path.exists(CSV_FILE):
        return False
    with open(CSV_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date") == today_str:
                return True
    return False


def append_to_csv(entry):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


def main():
    today = str(date.today())

    if already_recorded(today):
        print(f"Already recorded an entry for {today}. Skipping.")
        return

    print("Fetching CT Market daily prices...")
    html = fetch_prices()

    print("Parsing ginger price...")
    entry = parse_ginger_price(html)

    append_to_csv(entry)
    print(
        f"✅ Saved: {entry['date']} | Price date: {entry['price_date']} | "
        f"Low: R{entry['low']} | High: R{entry['high']} | Avg: R{entry['average']}"
    )


if __name__ == "__main__":
    main()
