"""Scheduled FOMC announcement days (last day of each scheduled meeting), 1994-2027, from federalreserve.gov.

Sources: https://www.federalreserve.gov/monetarypolicy/fomchistorical{YYYY}.htm (1994-2020) and
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (2021-2027). Conference calls, notation votes and
meetings marked "(unscheduled)" are excluded (not known in advance). A scheduled meeting that was later
cancelled (March 17-18, 2020) is kept: it was on the published schedule at the time of the decisions before it.
Output: fomc_scheduled.csv (columns: year, label, day0, source).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent / "fomc_scheduled.csv"
H = {"User-Agent": "Mozilla/5.0 (academic research; daily FOMC calendar)"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                      "nov", "dec"], start=1)}


def _month(tok: str) -> int:
    return MONTHS[tok.strip().lower()[:3]]


def _last_day(year: int, month_txt: str, days_txt: str) -> pd.Timestamp:
    """month_txt like 'April' or 'April/May' or 'Apr/May'; days_txt like '30-1', '16-17', '9'."""
    months = [_month(m) for m in month_txt.split("/")]
    days = [int(x) for x in re.findall(r"\d+", days_txt)]
    m_last = months[-1]
    d_last = days[-1]
    y = year
    return pd.Timestamp(year=y, month=m_last, day=d_last)


def historical(year: int) -> list[dict]:
    url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
    r = requests.get(url, timeout=60, headers=H)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "lxml")
    rows = []
    for el in s.find_all(["h5", "h4", "h3"]):
        t = el.get_text(" ", strip=True)
        m = re.match(r"^([A-Za-z]+(?:/[A-Za-z]+)?)\s+([\d\-]+)\s*(.*?)\s*-\s*(\d{4})$", t)
        if not m:
            continue
        mon, days, kind, yy = m.groups()
        kl = kind.lower()
        if "meeting" not in kl or "unscheduled" in kl or "conference" in kl or "notation" in kl:
            continue
        rows.append({"year": int(yy), "label": t, "day0": _last_day(int(yy), mon, days), "source": url})
    return rows


def current() -> list[dict]:
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    r = requests.get(url, timeout=60, headers=H)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "lxml")
    rows = []
    for p in s.find_all("div", class_="panel"):
        hd = p.find(class_="panel-heading")
        if hd is None:
            continue
        m = re.match(r"(\d{4}) FOMC Meetings", hd.get_text(" ", strip=True))
        if not m:
            continue
        year = int(m.group(1))
        for row in p.find_all(class_="fomc-meeting"):
            mo = row.find(class_="fomc-meeting__month")
            da = row.find(class_="fomc-meeting__date")
            if mo is None or da is None:
                continue
            dtxt = da.get_text(" ", strip=True)
            if re.search(r"notation|unscheduled|conference", dtxt, re.I):
                continue
            rows.append({"year": year, "label": f"{mo.get_text(' ', strip=True)} {dtxt} - {year}",
                         "day0": _last_day(year, mo.get_text(" ", strip=True), dtxt.replace("*", "")),
                         "source": url})
    return rows


def main() -> None:
    rows = []
    for y in range(1994, 2021):
        rows += historical(y)
    rows += [r for r in current() if r["year"] >= 2021]
    df = pd.DataFrame(rows).sort_values("day0").drop_duplicates("day0").reset_index(drop=True)
    # two "Meeting" headings within 3 days (2003-09-15 and 2003-09-16): keep the later, the statement day
    gap_next = df["day0"].shift(-1) - df["day0"]
    dropped = df[gap_next <= pd.Timedelta(days=3)]
    if len(dropped):
        print("dropped (followed by another meeting heading within 3 days):", dropped["label"].tolist())
    df = df[~(gap_next <= pd.Timedelta(days=3))].reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print(df.groupby("year").size().to_string())
    print(len(df), "scheduled meetings ->", OUT)


if __name__ == "__main__":
    main()
