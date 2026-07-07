"""
ივენთების გაერთიანების სკრიპტი
=================================
აერთიანებს ორ წყაროს ერთ საბოლოო ფაილში, რომელსაც საიტი (index.html) კითხულობს:

1. manual_events.json  — ხელით კურირებული ივენთები (tkt.ge, batumievents.com, სხვა
   JS-რენდერირებადი საიტებიდან, სადაც ავტომატური სქრეიპინგი ძნელია).
   ეს ფაილს შენ პირადად ან მე გავმართავთ დროდადრო.

2. infobatumi_events.json — ავტომატურად გენერირებული scrape_infobatumi.py-ს მიერ
   (ეს ფაილი ყოველ ჯერზე ხელახლა იწერება სქრეიპერის გაშვებისას).

გამოსავალი: events.json — ორივეს გაერთიანებული და თარიღით დალაგებული სია,
რომელსაც კითხულობს საიტი.

გაშვება:
    python merge_events.py
"""

import json
from pathlib import Path

MANUAL_FILE = Path("manual_events.json")
INFOBATUMI_FILE = Path("infobatumi_events.json")
OUTPUT_FILE = Path("events.json")


def load_json(path):
    if not path.exists():
        print(f"⚠️  {path} ვერ მოიძებნა — ცარიელ სიად ჩაითვლება.")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    manual = load_json(MANUAL_FILE)
    infobatumi = load_json(INFOBATUMI_FILE)

    combined = manual + infobatumi

    # დუბლიკატების მოცილება ბმულის მიხედვით (თუ იგივე ივენთი ორივეგან მოხვდა)
    seen = set()
    unique = []
    for ev in combined:
        key = ev.get("url", ev.get("title"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(ev)

    # დალაგება თარიღის მიხედვით
    unique.sort(key=lambda e: e.get("date", ""))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"✅ გაერთიანდა {len(manual)} ხელით დამატებული + {len(infobatumi)} ავტომატური = "
          f"{len(unique)} უნიკალური ივენთი → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
