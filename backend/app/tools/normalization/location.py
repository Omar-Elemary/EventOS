"""Normalize Egyptian (and common) location strings to a canonical city."""

from __future__ import annotations

from dataclasses import dataclass


ALIASES: dict[str, str] = {
    "cairo": "Cairo",
    "القاهرة": "Cairo",
    "قاهره": "Cairo",
    "giza": "Giza",
    "الجيزة": "Giza",
    "الجيزه": "Giza",
    "الجيزة.": "Giza",
    "alexandria": "Alexandria",
    "alex": "Alexandria",
    "alexendria": "Alexandria",
    "الإسكندرية": "Alexandria",
    "الاسكندرية": "Alexandria",
    "اسكندرية": "Alexandria",
    "اسكندريه": "Alexandria",
    "new cairo": "New Cairo",
    "التجمع": "New Cairo",
    "التجمع الخامس": "New Cairo",
    "cairo festival": "New Cairo",
    "nasr city": "Nasr City",
    "مدينة نصر": "Nasr City",
    "مدينه نصر": "Nasr City",
    "heliopolis": "Heliopolis",
    "مصر الجديدة": "Heliopolis",
    "مصر الجديده": "Heliopolis",
    "6th of october": "6th of October",
    "sixth of october": "6th of October",
    "السادس من أكتوبر": "6th of October",
    "السادس من اكتوبر": "6th of October",
    "october": "6th of October",
    "sharm": "Sharm El-Sheikh",
    "sharm el sheikh": "Sharm El-Sheikh",
    "شرم الشيخ": "Sharm El-Sheikh",
    "hurghada": "Hurghada",
    "الغردقة": "Hurghada",
    "luxor": "Luxor",
    "الأقصر": "Luxor",
    "الاقصر": "Luxor",
    "sahel": "North Coast",
    "north coast": "North Coast",
    "الساحل": "North Coast",
}


@dataclass(frozen=True)
class CanonicalLocation:
    city: str
    country: str = "Egypt"
    raw: str = ""

    @property
    def label(self) -> str:
        return f"{self.city}, {self.country}"


def normalize_location(raw: str | None) -> CanonicalLocation:
    text = (raw or "").strip()
    if not text:
        return CanonicalLocation(city="", raw=text)
    key = text.lower().replace("  ", " ")
    if key in ALIASES:
        return CanonicalLocation(city=ALIASES[key], raw=text)
    for needle, city in sorted(ALIASES.items(), key=lambda kv: -len(kv[0])):
        if needle and needle in key:
            return CanonicalLocation(city=city, raw=text)
    return CanonicalLocation(city=text.title(), country="Egypt", raw=text)


def bilingual_queries(kind: str, location: str, extra: str = "") -> list[str]:
    loc = normalize_location(location)
    city = loc.city or location
    en = f"{kind} {city} Egypt {extra}".strip()
    ar_city = {
        "Cairo": "القاهرة",
        "Giza": "الجيزة",
        "Alexandria": "الإسكندرية",
        "New Cairo": "التجمع الخامس",
        "Nasr City": "مدينة نصر",
        "Heliopolis": "مصر الجديدة",
        "6th of October": "السادس من أكتوبر",
        "Hurghada": "الغردقة",
        "Sharm El-Sheikh": "شرم الشيخ",
        "Luxor": "الأقصر",
        "North Coast": "الساحل الشمالي",
    }.get(city, city)
    ar_kind = {
        "conference venue": "قاعة مؤتمرات",
        "event venue": "قاعة مناسبات",
        "catering": "كاترينج",
        "av": "صوتيات وإضاءة",
        "security": "أمن مناسبات",
    }.get(kind, kind)
    ar = f"{ar_kind} {ar_city} {extra}".strip()
    return [en, ar]
