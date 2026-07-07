"""
InfoBatumi.ge ივენთების სქრეიპერი (განახლებული ვერსია)
=========================================================
წამოიღებს ღონისძიებების სიას infobatumi.ge-დან და შეინახავს
infobatumi_events.json ფაილში — იმ ფორმატში, რომელსაც საიტი მოელის:
  {title, cat, venue, date (YYYY-MM-DD), dateLabel, url}

ეს ფაილი შემდეგ merge_events.py-ს მიერ ერწყმის manual_events.json-ს
და გამოდის საბოლოო events.json.

როგორ გავუშვათ:
    pip install requests beautifulsoup4
    python scrape_infobatumi.py

⚠️ მნიშვნელოვანი: CSS სელექტორები ქვემოთ (`.event-card` და ა.შ.) სავარაუდოა.
გვერდის რეალური სტრუქტურის დასათვალიერებლად:
  1. გახსენი https://www.infobatumi.ge/events/ ბრაუზერში
  2. მარჯვენა ღილაკი ივენთის ბარათზე → "Inspect" / "დათვალიერება"
  3. ნახე რეალური კლასების სახელები და განაახლე ქვემოთ
"""

import re
import json
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.infobatumi.ge/events/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# კატეგორიის დადგენა სათაურში/ტექსტში საკვანძო სიტყვებით (საორიენტაციო, საჭიროებისამებრ დაამატე სიტყვები)
CATEGORY_KEYWORDS = {
    "თეატრი": ["თეატრი", "სპექტაკლი", "დრამ"],
    "საბავშვო": ["საბავშვო", "თოჯინ", "ბავშვ"],
    "ფესტივალი": ["ფესტივალი", "фест"],
    "სპორტი": ["სპორტი", "ტურნირი", "ფეხბურთ"],
    "კლუბი": ["mono hall", "geography", "night club", "dj ", "club"],
}
DEFAULT_CATEGORY = "კონცერტი"

MONTHS_KA = {
    "იანვარი": 1, "თებერვალი": 2, "მარტი": 3, "აპრილი": 4, "მაისი": 5, "ივნისი": 6,
    "ივლისი": 7, "აგვისტო": 8, "სექტემბერი": 9, "ოქტომბერი": 10, "ნოემბერი": 11, "დეკემბერი": 12,
}


def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"შეცდომა გვერდის წამოღებისას {url}: {e}")
        return None


def guess_category(text):
    text_lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return DEFAULT_CATEGORY


def parse_date(raw_date, year=2026):
    """
    ცდილობს ქართული თარიღის ტექსტიდან (მაგ. '16 ივლისი') ISO ფორმატის აღდგენას.
    თუ ვერ ხერხდება — აბრუნებს None-ს (მაშინ dateLabel მაინც შენარჩუნდება).
    """
    match = re.search(r'(\d{1,2})\s+([ა-ჰ]+)', raw_date)
    if not match:
        return None
    day = int(match.group(1))
    month_name = match.group(2)
    month = MONTHS_KA.get(month_name)
    if not month:
        return None
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_events(html):
    soup = BeautifulSoup(html, "html.parser")
    events = []

    # ⚠️ შეცვალე რეალური კლასების მიხედვით შემდეგ, რაც დაათვალიერებ გვერდს
    cards = soup.select(".event-card, article.event, .events-list-item")

    for card in cards:
        title_el = card.select_one(".event-title, h3, h2")
        date_el = card.select_one(".event-date, .date, time")
        venue_el = card.select_one(".event-venue, .venue, .location")
        link_el = card.select_one("a")

        if not title_el or not link_el:
            continue

        title = title_el.get_text(strip=True)
        date_raw = date_el.get_text(strip=True) if date_el else ""
        venue = venue_el.get_text(strip=True) if venue_el else "ბათუმი"
        link = link_el.get("href", "")
        if link and not link.startswith("http"):
            link = "https://www.infobatumi.ge" + link

        iso_date = parse_date(date_raw) or ""
        category = guess_category(title + " " + venue)

        events.append({
            "title": title,
            "cat": category,
            "venue": venue,
            "date": iso_date,
            "dateLabel": date_raw,
            "url": link,
        })

    return events


def main():
    print("ვწამოღებ ივენთების გვერდს infobatumi.ge-დან...")
    html = fetch_page(BASE_URL)
    if not html:
        print("ვერ მოხერხდა გვერდის წამოღება. სცადე მოგვიანებით.")
        return

    events = parse_events(html)
    print(f"ნაპოვნია {len(events)} ივენთი.")

    # თარიღის გარეშე ჩანაწერები გამოვარჩიოთ, რომ იცოდე რომელი საჭიროებს ხელით შემოწმებას
    missing_date = [e for e in events if not e["date"]]
    if missing_date:
        print(f"⚠️  {len(missing_date)} ივენთს არ ჩამოეყალიბა ISO თარიღი ავტომატურად — "
              f"საჭიროა ხელით შემოწმება infobatumi_events.json ფაილში.")

    with open("infobatumi_events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print("შენახულია infobatumi_events.json ფაილში.")


if __name__ == "__main__":
    main()
