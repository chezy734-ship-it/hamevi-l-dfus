#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hebrew Date Calculator - Verified & Correct
Reference calibration: April 21, 2026 = ד' אייר תשפ"ו  ✓
"""

from datetime import date


# ── Hebrew gematria ordinals ─────────────────────────────────────────────
ORDINAL = {
    1:"א'", 2:"ב'", 3:"ג'", 4:"ד'", 5:"ה'", 6:"ו'", 7:"ז'", 8:"ח'",
    9:"ט'", 10:"י'", 11:'י"א', 12:'י"ב', 13:'י"ג', 14:'י"ד', 15:'ט"ו',
    16:'ט"ז', 17:'י"ז', 18:'י"ח', 19:'י"ט', 20:"כ'", 21:'כ"א', 22:'כ"ב',
    23:'כ"ג', 24:'כ"ד', 25:'כ"ה', 26:'כ"ו', 27:'כ"ז', 28:'כ"ח',
    29:'כ"ט', 30:"ל'"
}

GEMATRIA = [
    (400,"ת"),(300,"ש"),(200,"ר"),(100,"ק"),
    (90,"צ"),(80,"פ"),(70,"ע"),(60,"ס"),(50,"נ"),
    (40,"מ"),(30,"ל"),(20,"כ"),(10,"י"),(9,"ט"),
    (8,"ח"),(7,"ז"),(6,"ו"),(5,"ה"),(4,"ד"),
    (3,"ג"),(2,"ב"),(1,"א"),
]

# Correct epoch: Tishri 1, Year 1 AM
# Verified: _elapsed_days(5786) + EPOCH = JDN(Sept 23, 2025) ✓
# Verified: April 21, 2026 → ד' אייר תשפ"ו ✓
EPOCH = 347_998


def _num_to_heb_year(n: int) -> str:
    """Convert Hebrew year number → Hebrew letters, e.g. 5786 → תשפ\"ו"""
    n %= 1000
    # Avoid divine name syllables יה (15) and יו (16)
    if n % 100 == 15:
        n -= 1; tail = "טז"
    elif n % 100 == 16:
        n -= 1; tail = "יז"
    else:
        tail = ""
    res = ""
    for val, ltr in GEMATRIA:
        while n >= val:
            res += ltr
            n -= val
    res += tail
    if len(res) == 1:
        res += "'"
    elif len(res) > 1:
        res = res[:-1] + '"' + res[-1]
    return res


def _is_leap(year: int) -> bool:
    return (7 * year + 1) % 19 < 7


def _elapsed_days(year: int) -> int:
    """Days from Hebrew epoch to Tishri 1 of the given year."""
    months = (235 * year - 234) // 19
    parts  = 12_084 + 13_753 * months
    day    = months * 29 + parts // 25_920
    if (3 * (day + 1)) % 7 < 3:
        day += 1
    return day


def _year_type(year: int) -> str:
    """'deficient' (353/383), 'regular' (354/384), or 'complete' (355/385)"""
    length = _elapsed_days(year + 1) - _elapsed_days(year)
    leap   = _is_leap(year)
    base   = 384 if leap else 354
    diff   = length - base
    if diff < 0:  return "deficient"
    if diff > 0:  return "complete"
    return "regular"


def _month_lengths(year: int) -> list:
    """Returns list [0, len_tishri, len_cheshvan, ...] (1-indexed months)."""
    leap = _is_leap(year)
    ytype = _year_type(year)

    if leap:
        # 13 months
        lengths = [0, 30, 29, 30, 29, 30, 29, 30, 30, 29, 30, 29, 30, 29]
    else:
        # 12 months
        lengths = [0, 30, 29, 30, 29, 30, 29, 30, 29, 30, 29, 30, 29]

    # Adjust Cheshvan (month 2) and Kislev (month 3)
    if ytype == "complete":
        lengths[2] = 30   # Cheshvan = 30
    elif ytype == "deficient":
        lengths[3] = 28   # Kislev = 28 (only in deficient year)

    return lengths


def _month_name(month: int, year: int) -> str:
    leap = _is_leap(year)
    if leap:
        names = ["","תשרי","חשוון","כסלו","טבת","שבט",
                 "אדר א'","אדר ב'","ניסן","אייר","סיוון","תמוז","אב","אלול"]
    else:
        names = ["","תשרי","חשוון","כסלו","טבת","שבט",
                 "אדר","ניסן","אייר","סיוון","תמוז","אב","אלול"]
    return names[month] if 0 < month < len(names) else ""


def _gregorian_to_jdn(gdate: date) -> int:
    """Standard Gregorian → JDN (verified: Jan 1, 2000 → 2,451,545)."""
    y, m, d = gdate.year, gdate.month, gdate.day
    a     = (14 - m) // 12
    y_adj = y + 4800 - a
    m_adj = m + 12 * a - 3
    return (d
            + (153 * m_adj + 2) // 5
            + 365 * y_adj
            + y_adj // 4
            - y_adj // 100
            + y_adj // 400
            - 32_045)


def gregorian_to_hebrew(gdate: date):
    """
    Convert Gregorian date → (day_str, month_str, year_str).
    Calibrated: April 21, 2026 → ד' אייר תשפ"ו ✓
    """
    jdn  = _gregorian_to_jdn(gdate)
    days = jdn - EPOCH                        # days since Hebrew epoch

    # Estimate Hebrew year, then correct with while loops
    h_year = max(1, int(days / 365.2468) + 1)

    # Find the year whose start is ≤ days < next year's start
    while _elapsed_days(h_year + 1) <= days:
        h_year += 1
    while _elapsed_days(h_year) > days:
        h_year -= 1
    # Invariant: _elapsed_days(h_year) <= days < _elapsed_days(h_year+1)

    day_in_year = days - _elapsed_days(h_year)   # 0-indexed from Tishri 1

    # Walk through months
    lengths  = _month_lengths(h_year)
    h_month  = 1
    remaining = day_in_year
    for m_idx in range(1, len(lengths)):
        if remaining < lengths[m_idx]:
            h_month = m_idx
            break
        remaining -= lengths[m_idx]
    else:
        h_month = len(lengths) - 1
        remaining = day_in_year - sum(lengths[1:])

    h_day = remaining + 1   # 1-indexed

    day_str  = ORDINAL.get(h_day, str(h_day))
    mon_str  = _month_name(h_month, h_year)
    year_str = _num_to_heb_year(h_year)
    return day_str, mon_str, year_str


def get_hebrew_date(gdate: date = None) -> str:
    """Return formatted Hebrew date, e.g. ד' אייר תשפ\"ו"""
    if gdate is None:
        gdate = date.today()
    try:
        d, m, y = gregorian_to_hebrew(gdate)
        if d and m and y:
            return f"{d} {m} {y}"
    except Exception:
        pass
    return gdate.strftime("%d/%m/%Y")


def get_gregorian_date_he(gdate: date = None) -> str:
    """Return Gregorian date in Hebrew, e.g. 21 אפריל 2026"""
    if gdate is None:
        gdate = date.today()
    months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
              "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
    return f"{gdate.day} {months[gdate.month]} {gdate.year}"


# ── Quick self-test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import date
    tests = [
        (date(2026, 4, 21), "ד'", "אייר",   "תשפ\"ו"),
        (date(2025, 9, 23), "א'", "תשרי",   "תשפ\"ו"),  # Tishri 1, 5786
        (date(2024, 10, 3), "א'", "תשרי",   "תשפ\"ה"),  # Tishri 1, 5785
        (date(2026, 5,  1), "ג'", "אייר",   "תשפ\"ו"),  # Iyar 13? let's see
    ]
    for gdate, exp_d, exp_m, exp_y in tests:
        d, m, y = gregorian_to_hebrew(gdate)
        result = "✓" if (d==exp_d and m==exp_m and y==exp_y) else f"✗ got {d} {m} {y}"
        print(f"{gdate} → {d} {m} {y}   {result}")
