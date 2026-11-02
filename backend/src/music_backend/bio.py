"""The real name and the dates of birth and death of a person, which Genius has only as the first words of
the description: "Kendrick Lamar Duckworth (born June 17, 1987) is ...", "Lola Mitchell (August 7, 1979
- January 1, 2023) was ..." or, in Russian, "Оралов Фёдор Юрьевич (родился 18 апреля 1993 года в Уфе) — ...".
Places are told in free sentences and are not taken."""

# ruff: noqa: RUF001  # Russian words that look like Latin ones, and the dashes of real descriptions

import re
from dataclasses import dataclass
from datetime import date, datetime

from music_backend.enums import DatePrecision

_MONTH = r"[A-Z][a-z]{2,8}\.?"
_DAY = r"\d{1,2}(?:st|nd|rd|th)?"
_DATE = rf"(?:{_MONTH} {_DAY},? \d{{4}}|{_DAY} {_MONTH},? \d{{4}}|{_MONTH},? \d{{4}}|\d{{4}})"
_BIO = re.compile(
    rf"^(?P<name>[^()\n]{{2,80}}?)\s*"
    rf"\((?:(?:born:?|b\.)\s*(?:on\s+)?)?(?P<born>{_DATE})(?:\s*[–—-]\s*(?P<died>{_DATE}))?"
    # "born June 17, 1987, in Compton, California": the place is not taken
    rf"(?:,?\s+in\s+[^()]*)?\)"
)
# The Russian bio: "(родился 18 апреля 1993 года в Уфе)", "(18 апреля 1993, Уфа — 5 мая 2020, Москва)", "(род. 1993)".
_RU_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
_RU_MONTH = "(?:" + "|".join(_RU_MONTHS) + ")"
_RU_DATE = rf"(?:\d{{1,2}} {_RU_MONTH} \d{{4}}|\d{{4}})(?: года| г\.)?"
# The place after a date: ", Уфа" or " в Уфе" (a hyphen inside is a part of the name, a dash is the end of it).
_RU_PLACE = r"(?:,\s*[^()–—]+?|\s+(?:в|во)\s+[^()–—]+?)?"
_BIO_RU = re.compile(
    rf"^(?P<name>[^()\n]{{2,80}}?)\s*"
    rf"\((?:(?:родился|родилась|род\.|р\.)\s*)?(?P<born>{_RU_DATE}){_RU_PLACE}"
    rf"(?:\s*[–—]\s*(?P<died>{_RU_DATE}){_RU_PLACE})?\)"
)
# A name is capitalised words; a lowercase word means the match is a sentence, not a name.
_PARTICLES = {
    "de",
    "da",
    "di",
    "del",
    "van",
    "von",
    "der",
    "bin",
    "ibn",
    "al",
    "el",
    "la",
    "le",
    "dos",
    "y",
}
# From the most to the least complete; the precision is what the format keeps.
_FORMATS = (
    ("%B %d %Y", DatePrecision.DAY),
    ("%b %d %Y", DatePrecision.DAY),
    ("%d %B %Y", DatePrecision.DAY),
    ("%d %b %Y", DatePrecision.DAY),
    ("%B %Y", DatePrecision.MONTH),
    ("%b %Y", DatePrecision.MONTH),
    ("%Y", DatePrecision.YEAR),
)

type PartialDate = tuple[date, DatePrecision]


@dataclass(slots=True, frozen=True)
class Bio:
    real_name: str
    born: PartialDate
    died: PartialDate | None


def _parse_date(text: str) -> PartialDate | None:
    if russian := re.fullmatch(
        rf"(?:(\d{{1,2}}) ({_RU_MONTH}) )?(\d{{4}})(?: года| г\.)?", text.strip()
    ):
        day, month, year = russian.groups()
        if month is None:
            return date(int(year), 1, 1), DatePrecision.YEAR
        return date(int(year), _RU_MONTHS.index(month) + 1, int(day)), DatePrecision.DAY
    text = re.sub(r"(?<=\d)(?:st|nd|rd|th)", "", text).replace(".", "").replace(",", "")
    for pattern, precision in _FORMATS:
        try:
            return datetime.strptime(text, pattern).date(), precision
        except ValueError:
            continue
    return None


def parse_bio(description: str | None) -> Bio | None:
    """The bio at the very start of the description, or None when it does not start with one."""
    if not description:
        return None
    text = description.strip()
    if not (found := _BIO.match(text) or _BIO_RU.match(text)):
        return None
    born = _parse_date(found["born"])
    died = _parse_date(found["died"]) if found["died"] else None
    if born is None or (found["died"] and died is None):
        return None
    name = found["name"].strip()
    if any(
        not (word[0].isupper() or word[0] in "“\"'(" or word in _PARTICLES) for word in name.split()
    ):
        return None
    return Bio(name, born, died)
