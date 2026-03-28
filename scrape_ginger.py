"""
scrape_ginger.py
Fetches daily ginger 5kg prices from two markets:
  - Cape Town Market (HEGI, Carton 5kg, Grade 1)
  - Joburg Market (commodity=156, cid=25)
Appends results to prices.csv.
"""

import csv
import os
import re
from datetime import date

import requests
from bs4 import BeautifulSoup

CSV_FILE = "prices.csv"
FIELDNAMES = ["date", "price_date", "market", "container", "low", "high", "average"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-ZA,en;q=0.9",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_html(url, session=None):
    requester = session or requests
    resp = requester.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_date_dmy(html):
    m = re.search(r"(\d{2}/\d{2}/\d{4})", html)
    if m:
        d, mo, yr = m.group(1).split("/")
        return f"{yr}-{mo}-{d}"
    return None


def extract_date_words(html):
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }
    m = re.search(
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})",
        html, re.IGNORECASE
    )
    if m:
        return f"{m.group(3)}-{months[m.group(2).lower()]}-{m.group(1).zfill(2)}"
    return None


def already_recorded(today_str, market):
    if not os.path.exists(CSV_FILE):
        return False
    with open(CSV_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("date") == today_str and row.get("market") == market:
                return True
    return False


def append_to_csv(entry):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


# ── Cape Town Market ──────────────────────────────────────────────────────────

CT_URL = "https://www.ctmarket.co.za/daily-prices/"


def scrape_ct_market(today):
    if already_recorded(today, "Cape Town"):
        print("CT Market: already recorded for today, skipping.")
        return

    print("CT Market: fetching...")
    html = get_html(CT_URL)
    price_date = extract_date_dmy(html)
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        raise ValueError("CT Market: price table not found.")

    for row in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 9:
            continue
        item_code = cells[0].upper()
        container = cells[2].lower()
        grade = cells[4].strip()
        if item_code == "HEGI" and "carton" in container and "5" in container and grade == "1":
            entry = {
                "date": today,
                "price_date": price_date or "unknown",
                "market": "Cape Town",
                "container": "Carton (5kg)",
                "low": cells[6],
                "high": cells[7],
                "average": cells[8],
            }
            append_to_csv(entry)
            print(
                f"CT Market: saved | price date: {entry['price_date']} | "
                f"Low: R{entry['low']} | High: R{entry['high']} | Avg: R{entry['average']}"
            )
            return

    raise ValueError("CT Market: HEGI Carton (5kg) Grade 1 not found in today's prices.")


# ── Joburg Market ─────────────────────────────────────────────────────────────

JHB_URL = "https://joburgmarket.co.za/jhb-market/dailyprices.php?commodity=156&cid=25"


def scrape_joburg_market(today):
    if already_recorded(today, "Joburg"):
        print("Joburg Market: already recorded for today, skipping.")
        return

    print("Joburg Market: fetching...")

    session = requests.Session()
    try:
        session.get("https://joburgmarket.co.za/", headers=HEADERS, timeout=15)
    except Exception:
        pass

    html = get_html(JHB_URL, session=session)
    price_date = extract_date_dmy(html) or extract_date_words(html)

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("Joburg Market: price table not found on page.")

    # ── DEBUG: print every row so we can see the real structure ──
    print("DEBUG Joburg table rows:")
    for i, row in enumerate(table.find_all("tr")):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if cells:
            print(f"  row {i}: {cells}")
    # ── END DEBUG ──

    for row in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 3:
            continue
        numeric = [c for c in cells if re.match(r"^\d[\d,\.]*$", c.replace(" ", ""))]
        if len(numeric) < 2:
            continue

        def clean(s):
            return s.replace(",", "").replace(" ", "")

        try:
            if len(cells) >= 5:
                low = clean(cells[-3])
                high = clean(cells[-2])
                avg = clean(cells[-1])
            else:
                low = clean(cells[-2])
                high = clean(cells[-1])
                avg = clean(cells[-1])
            float(low); float(high); float(avg)
        except (ValueError, IndexError):
            continue

        entry = {
            "date": today,
            "price_date": price_date or "unknown",
            "market": "Joburg",
            "container": "Box (5kg)",
            "low": low,
            "high": high,
            "average": avg,
        }
        append_to_csv(entry)
        print(
            f"Joburg Market: saved | price date: {entry['price_date']} | "
            f"Low: R{entry['low']} | High: R{entry['high']} | Avg: R{entry['average']}"
        )
        return

    raise ValueError("Joburg Market: could not parse a price row from the table.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today = str(date.today())
    errors = []

    try:
        scrape_ct_market(today)
    except Exception as e:
        print(f"CT Market ERROR: {e}")
        errors.append(f"CT Market: {e}")

    try:
        scrape_joburg_market(today)
    except Exception as e:
        print(f"Joburg Market ERROR: {e}")
        errors.append(f"Joburg Market: {e}")

    if errors:
        raise SystemExit("One or more markets failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    main()
