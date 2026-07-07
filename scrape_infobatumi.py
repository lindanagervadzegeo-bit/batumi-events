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

⚠️ მნიშვნელოვანი: ეს საიტი აშენებულია Elementor-ზე (WordPress page builder),
სადაც კლასების სახელები (მაგ. elementor-element-4e99338) არასტაბილურია.
ამის მაგივრად ვეყრდნობით data-widget_type ატრიბუტს (heading.default,
text-editor.default), რომელიც სტაბილურია. თუ საიტის სტრუქტურა შეიცვლება
მომავალში, საჭირო იქნება ამ სელექტორების ხელახალი გადამოწმება:
  1. გახსენი https://www.infobatumi.ge/events/ ბრაუზერში
  2. მარჯვენა ღილაკი ივენთის ბარათზე → "Inspect" / "დათვალიერება"
  3. ნახე შეცვლილა თუ არა data-widget_type ან data-element_type ატრიბუტები
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
    """
    გასაღები აღმოჩენა (ბრაუზერის Inspect-ის მეშვეობით): თითოეული ივენთის
    მთელი ბარათი გახვეულია div.ts-preview კონტეინერში — ეს არის სტაბილური
    კლასი (არა elementor-ის შემთხვევითი ჰეშ-კოდი). საიტი თითო ივენთს
    დუბლირებულად აჩვენებს DOM-ში (responsive mobile/desktop ვერსიები),
    ამიტომ url-ების მიხედვით ვშლით დუბლიკატებს.
    """
    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen_urls = set()

    cards = soup.select("div.ts-preview")

    # თარიღის ნიმუშები: "16 ივლისი" ან დიაპაზონი "4 ივნისი – 23 ივლისი"
    date_pattern = re.compile(r'(\d{1,2}\s+[ა-ჰ]+)(?:\s*[-–]\s*(\d{1,2}\s+[ა-ჰ]+))?')
    recurring_keywords = ["ყოველდღე", "ყოველკვირეულად"]

    for card in cards:
        link_el = card.select_one('a[href*="/events/"]')
        if not link_el:
            continue
        url = link_el.get("href", "")
        if not url.startswith("http"):
            url = "https://www.infobatumi.ge" + url
        if url.rstrip('/').endswith('/events') or url in seen_urls:
            continue
        seen_urls.add(url)

        heading_el = card.select_one('[data-widget_type="heading.default"]')
        title = heading_el.get_text(strip=True) if heading_el else ""
        if not title:
            img_el = card.select_one("img")
            title = (img_el.get("alt", "").strip() if img_el else "") or "უცნობი სათაური"

        full_text = card.get_text(separator=" | ", strip=True)

        # თარიღის ამოცნობა
        date_match = date_pattern.search(full_text)
        date_label = ""
        iso_date = ""
        if date_match:
            date_label = date_match.group(0)
            iso_date = parse_date(date_match.group(1)) or ""
        else:
            for kw in recurring_keywords:
                if kw in full_text:
                    date_label = kw
                    break

        # ვენიუს ამოცნობა — ბოლო უნიკალური სეგმენტი, რომელიც არ არის თარიღი/სათაური
        segments = [s.strip() for s in full_text.split("|")]
        venue = "ბათუმი"
        seen_seg = set()
        unique_segments = []
        for s in segments:
            if s and s not in seen_seg:
                seen_seg.add(s)
                unique_segments.append(s)
        for s in reversed(unique_segments):
            if s != title and not date_pattern.search(s) and not any(kw in s for kw in recurring_keywords) \
               and s not in ("დღეს",) and len(s) > 2:
                venue = s
                break

        category = guess_category(title + " " + full_text)

        events.append({
            "title": title,
            "cat": category,
            "venue": venue,
            "date": iso_date,
            "dateLabel": date_label,
            "url": url,
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
