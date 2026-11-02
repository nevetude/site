"""Splits a Genius display name into the name, its variant and its alternative-language name."""

import re
import unicodedata
from dataclasses import dataclass

# A group with one of these words is a version of the work, never an alternative-language name.
VARIANT_WORDS = re.compile(
    r"\b(feat|ft|prod|remix|mix|edit|live|demo|deluxe|remaster(ed)?|freestyle|acoustic|instrumental|"
    r"version|reprise|skit|interlude|intro|outro|bonus|explicit|clean|radio|extended|original|"
    r"pt|part|vol|volume)\b\.?",
    re.IGNORECASE,
)


@dataclass(slots=True, frozen=True)
class SplitName:
    base_name: str
    variant: str | None
    disambiguator: str | None


def _letters(text: str) -> list[str]:
    return [c for c in text if c.isalpha()]


def _is_latin_letter(char: str) -> bool:
    return unicodedata.name(char, "").startswith("LATIN")


def _groups(name: str) -> tuple[str, list[str]]:
    """The name without the parenthesised groups at its end, and the groups (each with its parentheses and the groups
    inside it). The groups run to the end of the name with only spaces between them; text after the last one, nothing
    before the first one, or parentheses that do not close mean there are none."""
    depth = 0
    chain: int | None = None  # the start of the groups that reach the end
    last_end = 0
    starts: list[tuple[int, int]] = []  # the top-level groups (start, end)
    for i, char in enumerate(name):
        if char == "(":
            if depth == 0:
                if chain is None or name[last_end:i].strip():
                    chain, starts = i, []  # text between two groups starts a new chain
                starts.append((i, -1))
            depth += 1
        elif char == ")" and depth:
            depth -= 1
            if depth == 0:
                last_end = i + 1
                starts[-1] = (starts[-1][0], last_end)
    if depth or chain is None or name[last_end:].strip() or not name[:chain].strip():
        return name, []
    return name[:chain].strip(), [name[start:end] for start, end in starts]


def split_name(name: str) -> SplitName:
    """The groups in parentheses at the end are the variant, without their outer parentheses (a group inside a group
    stays in it) and joined with commas; one of them may be the alternative-language name instead: the first Latin
    one on a name that is not Latin, when it has no version word.

    "Warlord (This Record Is Dedicated to the Memory of B. (6/25/1987 - 4/8/2015))"
    -> ("Warlord", "This Record Is Dedicated to the Memory of B. (6/25/1987 - 4/8/2015)", None)
    "Надоела (Freestyle) (Tired of you)" -> ("Надоела", "Freestyle", "Tired of you")
    """
    base, groups = _groups(name.strip())
    base_is_non_latin = not all(_is_latin_letter(c) for c in _letters(base))
    variants: list[str] = []
    disambiguator = None
    for group in groups:
        inner = group[1:-1].strip()
        letters = _letters(inner)
        if (
            disambiguator is None
            and base_is_non_latin
            and letters
            and all(_is_latin_letter(c) for c in letters)
            and not VARIANT_WORDS.search(inner)
        ):
            disambiguator = inner
        else:
            variants.append(inner)
    return SplitName(base, ", ".join(variants) or None, disambiguator)


# --- the first way, kept for the moment (it may go): the groups were peeled one by one with a regular expression that
# knows no group inside a group.
#
# import re
# import unicodedata
# from dataclasses import dataclass
# # A parenthesized group with one of these words is a version of the work, not an alternative-language name.
# VARIANT_WORDS = re.compile(
#     r"\b(feat|ft|prod|remix|mix|edit|live|demo|deluxe|remaster(ed)?|freestyle|acoustic|instrumental|"
#     r"version|reprise|skit|interlude|intro|outro|bonus|explicit|clean|radio|extended|original|"
#     r"pt|part|vol|volume)\b\.?",
#     re.IGNORECASE,
# )
# TRAILING_GROUP = re.compile(r"\s*\(([^()]*)\)\s*$")
# @dataclass(slots=True, frozen=True)
# class SplitName:
#     base_name: str
#     variant: str | None
#     disambiguator: str | None
# def _letters(text: str) -> list[str]:
#     return [c for c in text if c.isalpha()]
# def _is_latin_letter(char: str) -> bool:
#     return unicodedata.name(char, "").startswith("LATIN")
# def split_name(name: str) -> SplitName:
#     """Split a Genius-style display name into base name, variant and alternative-language name.
#     "Надоела (Freestyle) (Tired of you)" -> ("Надоела", "Freestyle", "Tired of you")
#     """
#     base, groups = name.strip(), []
#     while (match := TRAILING_GROUP.search(base)) and match.start() > 0:
#         groups.append(match.group(1).strip())
#         base = base[: match.start()].strip()
#     groups.reverse()
#     base_is_non_latin = not all(_is_latin_letter(c) for c in _letters(base))
#     variants: list[str] = []
#     disambiguator = None
#     for group in groups:
#         letters = _letters(group)
#         is_alt_name = (
#             disambiguator is None
#             and base_is_non_latin
#             and bool(letters)
#             and all(_is_latin_letter(c) for c in letters)
#             and not VARIANT_WORDS.search(group)
#         )
#         if is_alt_name:
#             disambiguator = group
#         else:
#             variants.append(group)
#     return SplitName(base, ", ".join(variants) or None, disambiguator)
