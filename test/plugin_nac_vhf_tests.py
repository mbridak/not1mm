import pytest

from not1mm.plugins import nac_vhf as nac


class FakeDatabase:
    """Minimal stand-in for DataBase."""

    def __init__(self, current_contest="1", existing=()):
        self.current_contest = current_contest
        self.contacts = list(existing)
        self.saved = []

    def exec_sql(self, query, params=()):
        # Simulate the large-square counting query used by bonus_for_square.
        if "like ?" in query.lower():
            square = str(params[1]).rstrip("%")
            count = sum(
                1
                for c in self.contacts
                if str(c.get("Exchange1", "")).upper().startswith(square)
            )
            return {"cnt": count}
        return {"cnt": 0}

    def fetch_all_contacts_asc(self):
        return self.contacts

    def change_contact(self, contact):
        self.saved.append(dict(contact))


class FakeSelf:
    """Minimal stand-in for MainWindow."""


def make_self(
    my_grid="JO59",
    their_grid="JO49",
    dupe=False,
    band="2M",
    existing=(),
):
    fake = FakeSelf()
    fake.station = {"GridSquare": my_grid}
    fake.contact = {
        "Exchange1": their_grid,
        "SNT": "59",
        "RCV": "59",
        "SentNr": "001",
        "NR": "59",
    }
    fake.contact_is_dupe = 1 if dupe else 0
    fake.contest_settings = {"BandCategory": band}
    fake.database = FakeDatabase(existing=existing)
    return fake


@pytest.mark.parametrize(
    "grid,expected",
    [
        ("JO49", "JO49"),
        ("jo49jf", "JO49"),
        ("JO59JC", "JO59"),
        ("", ""),
        ("JN58", "JN58"),
        (None, ""),
    ],
)
def test_large_square(grid, expected):
    assert nac.large_square(grid) == expected


@pytest.mark.parametrize(
    "band,expected",
    [
        ("ALL", "ALL"),
        ("6M", "50 MHz"),
        ("2M", "144 MHz"),
        ("432", "432 MHz"),
        ("1.2G", "1,3 GHz"),
        ("2.3G", "2,3 GHz"),
        ("3.4G", "3,4 GHz"),
        ("47G", "47 GHz"),
        ("75G", "75 GHz"),
    ],
)
def test_bandinMHz_maps_ui_band_categories(band, expected):
    assert nac.bandinMHz(band) == expected


def test_bandinMHz_never_returns_literal_error():
    # Unmapped / blank bands must not produce the bogus "Invalid input" literal.
    for band in ("LIGHT", "VHF-3-BAND", "VHF-FM-ONLY", ""):
        assert "Invalid" not in nac.bandinMHz(band)


@pytest.mark.parametrize(
    "band,expected",
    [
        ("2M", 1),
        ("6M", 1),
        ("432", 1),
        ("1.2G", 1),
        ("2.3G", 2),
        ("3.4G", 3),
        ("5.7G", 4),
        ("10G", 5),
        ("24G", 6),
        ("47G", 7),
        ("UnknownBand", 1),
    ],
)
def test_ghz_multiplier(band, expected):
    fake = make_self(band=band)
    assert nac.ghz_multiplier(fake) == expected


def test_points_dupe_zero():
    fake = make_self(dupe=True)
    assert nac.points(fake) == 0


def test_points_includes_new_large_square_bonus():
    # A new large square should include the +500 bonus on top of distance.
    fake = make_self(my_grid="JO59", their_grid="JO49")
    # Distance JO59 -> JO49 is known; just verify the 500 bonus is present.
    pts = nac.points(fake)
    assert pts >= 500


def test_points_no_new_large_square_bonus_when_already_worked():
    existing = [
        {
            "Exchange1": "JO49XX",
            "Points": 999,
        }
    ]
    fake = make_self(existing=existing)
    pts = nac.points(fake)
    assert pts < 500


def test_points_band_multiplier_applied():
    # On 2.3 GHz+ the distance points are multiplied by the GHz multiplier.
    low = nac.points(make_self(my_grid="JO59", their_grid="JO49", band="2M"))
    high = nac.points(make_self(my_grid="JO59", their_grid="JO49", band="2.3G"))
    # Same distance: 2M gives (km*1 + bonus), 2.3G gives (km*2 + bonus)
    assert high > low
    # Difference is exactly the extra km (2x-1x)
    km = nac.distance("JO59", "JO49")
    assert high - low == km


def test_show_mults_counts_distinct_large_squares():
    fake = make_self()
    fake.database.contacts = [
        {"Exchange1": "JO49XX"},
        {"Exchange1": "JO49YY"},
        {"Exchange1": "JO59ZZ"},
        {"Exchange1": ""},
        {},
    ]
    assert nac.show_mults(fake) == 2


def test_recalculate_mults_awards_bonus_only_once_per_square():
    fake = make_self(my_grid="JO59")
    fake.database.contacts = [
        {"Exchange1": "JO49XX", "Points": 999},
        {"Exchange1": "JO49YY", "Points": 999},
        {"Exchange1": "JO59ZZ", "Points": 999},
    ]
    nac.recalculate_mults(fake)
    saved = fake.database.saved
    # First JO49 contact gets the new-large-square bonus; the second does not.
    assert saved[0]["Points"] >= 500
    assert saved[1]["Points"] < 500
    assert saved[2]["Points"] >= 500
