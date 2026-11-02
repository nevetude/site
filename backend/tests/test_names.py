import pytest

from music_backend.names import SplitName, split_name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (
            "Warlord (This Record Is Dedicated to the Memory of Barron Alexander Machat (6/25/1987 - 4/8/2015))",
            SplitName(
                "Warlord",
                "This Record Is Dedicated to the Memory of Barron Alexander Machat (6/25/1987 - 4/8/2015)",
                None,
            ),
        ),
        ("Надоела (Freestyle) (Tired of you)", SplitName("Надоела", "Freestyle", "Tired of you")),
        ("Надоела (Tired of you) (Freestyle)", SplitName("Надоела", "Freestyle", "Tired of you")),
        ("Группа крови (Blood Type)", SplitName("Группа крови", None, "Blood Type")),
        ("КИНО (KINO)", SplitName("КИНО", None, "KINO")),
        ("Русский (In Russian)", SplitName("Русский", None, "In Russian")),
        ("Creep (Live)", SplitName("Creep", "Live", None)),
        ("Album (2020)", SplitName("Album", "2020", None)),
        ("Canal St. (feat. A$AP Rocky)", SplitName("Canal St.", "feat. A$AP Rocky", None)),
        ("Надоела (Remix)", SplitName("Надоела", "Remix", None)),
        (
            "Mr. Brightside (Jacques Lu Cont's Thin White Duke Mix)",
            SplitName("Mr. Brightside", "Jacques Lu Cont's Thin White Duke Mix", None),
        ),
        # no group at the end, or nothing before the first one, or the parentheses do not close: left whole
        (
            "(What's the Story) Morning Glory?",
            SplitName("(What's the Story) Morning Glory?", None, None),
        ),
        ("Song (Part) Name", SplitName("Song (Part) Name", None, None)),
        ("Song (Live", SplitName("Song (Live", None, None)),
        ("Don’t F**k Around", SplitName("Don’t F**k Around", None, None)),
    ],
)
def test_split_name(name: str, expected: SplitName) -> None:
    assert split_name(name) == expected
