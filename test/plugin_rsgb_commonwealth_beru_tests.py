import pytest

from not1mm.plugins import rsgb_commonwealth_beru as beru


class FakeField:
    """Minimal stand-in for a QLineEdit."""

    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text


class FakeDatabase:
    """Minimal stand-in for DataBase."""

    def __init__(self, bonus_count=0):
        self.bonus_count = bonus_count
        self.queries = []
        self.saved = []

    def exec_sql(self, query):
        self.queries.append(query)
        return {"bonus_count": self.bonus_count}

    def fetch_all_contacts_asc(self):
        return self.contacts

    def change_contact(self, contact):
        self.saved.append(dict(contact))


CTY = {
    "K": {
        "entity": "United States of America",
        "continent": "NA",
        "primary_pfx": "K",
    },
    "VE": {"entity": "Canada", "continent": "NA", "primary_pfx": "VE"},
    "VK": {"entity": "Australia", "continent": "OC", "primary_pfx": "VK"},
    "ZS": {"entity": "South Africa", "continent": "AF", "primary_pfx": "ZS"},
    "G": {"entity": "England", "continent": "EU", "primary_pfx": "G"},
    "GM": {"entity": "Scotland", "continent": "EU", "primary_pfx": "GM"},
    "F": {"entity": "France", "continent": "EU", "primary_pfx": "F"},
    "JA": {"entity": "Japan", "continent": "AS", "primary_pfx": "JA"},
    "ZL": {"entity": "New Zealand", "continent": "OC", "primary_pfx": "ZL"},
    "VU": {"entity": "India", "continent": "AS", "primary_pfx": "VU"},
}


def make_self(
    my_call,
    their_call,
    rcv_nr="001",
    dupe=False,
    bonus_count=0,
    band=14.0,
    ts="2025-03-08 12:00:00",
):
    """Build a fake MainWindow sufficient for the functions under test."""

    class FakeSelf:
        pass

    fake = FakeSelf()
    fake.station = {"Call": my_call}
    fake.contact = {
        "Call": their_call,
        "Band": band,
        "TS": ts,
        "NR": "",
        "SNT": "",
        "RCV": "",
        "SentNr": "",
        "IsMultiplier1": 0,
        "IsMultiplier2": 0,
    }
    fake.contact_is_dupe = 1 if dupe else 0
    fake.pref = {"contest": "1"}
    fake.callsign = FakeField(their_call)
    fake.sent = FakeField("599")
    fake.receive = FakeField("599")
    fake.other_1 = FakeField("023")
    fake.other_2 = FakeField(rcv_nr)
    fake.database = FakeDatabase(bonus_count)

    def cty_lookup(call):
        base = beru.get_base_call(call)
        prefix = base[:2]
        if prefix not in CTY:
            prefix = base[:1]
        if prefix in CTY:
            return {base: CTY[prefix]}
        return None

    fake.cty_lookup = cty_lookup
    return fake


@pytest.mark.parametrize(
    "call,expected",
    [
        ("G4ABC", "G4ABC"),
        ("G4ABC/P", "G4ABC"),
        ("VP8/G4ABC", "VP8"),
        ("VE3/G4ABC", "VE3"),
        ("G4ABC/MM", "G4ABC"),
        ("G4ABC/7", "G4ABC"),
        ("", ""),
    ],
)
def test_get_base_call(call, expected):
    assert beru.get_base_call(call) == expected


@pytest.mark.parametrize(
    "exchange,expected",
    [
        ("001", False),
        ("001 HQ", True),
        ("HQ", True),
        ("hq", True),
        ("12HQ3", False),
        ("", False),
    ],
)
def test_is_hq_station(exchange, expected):
    assert beru.is_hq_station(exchange) is expected


@pytest.mark.parametrize(
    "call,expected",
    [
        ("VE3ABC", "VE3"),
        ("VO1XYZ", "VO1"),
        ("VY1ZZZ", "VY1"),
        ("VK3DEF", "VK3"),
        ("VK9CABC", "VK9C"),
        ("ZS5HIJ", "ZS5"),
        ("ZL1KL", "ZL1"),
    ],
)
def test_get_commonwealth_area_multi_area_countries(call, expected):
    fake = make_self("K5TUX", call)
    assert beru.get_commonwealth_area(fake, call) == expected


def test_points_same_continent_commonwealth():
    fake = make_self("K5TUX", "VE3ABC")
    fake.contact["IsMultiplier2"] = 0
    assert beru.points(fake) == 5


def test_points_different_continent_commonwealth():
    fake = make_self("K5TUX", "ZL1KL")
    fake.contact["IsMultiplier2"] = 0
    assert beru.points(fake) == 10


def test_points_non_commonwealth_zero():
    fake = make_self("K5TUX", "JAIABC")
    assert beru.points(fake) == 0
    fake = make_self("G4ABC", "FABCD")
    assert beru.points(fake) == 0


def test_points_own_call_area_zero():
    fake = make_self("VE3ABC", "VE3XYZ")
    assert beru.points(fake) == 0
    fake = make_self("VK3DEF", "VK3GHI")
    assert beru.points(fake) == 0


def test_points_different_call_area_same_entity_ok():
    fake = make_self("VE3ABC", "VE2XYZ")
    assert beru.points(fake) == 5
    fake = make_self("VK3DEF", "VK5GHI")
    assert beru.points(fake) == 5  # both Australia, same continent


def test_points_home_nations_zero():
    fake = make_self("G4ABC", "GM3XYZ")
    assert beru.points(fake) == 0


def test_points_hq_in_own_call_area():
    fake = make_self("VE3ABC", "VE3HQ", rcv_nr="001 HQ")
    beru.set_contact_vars(fake)
    # Own area, but HQ stations are always worth points.
    assert fake.contact["IsMultiplier2"] == 1
    assert beru.points(fake) == 25


def test_points_dupe():
    fake = make_self("K5TUX", "VE3ABC", dupe=True)
    assert beru.points(fake) == 0


def test_bonus_flag_first_three_per_band():
    fake = make_self("K5TUX", "VE3ABC", bonus_count=0)
    beru.set_contact_vars(fake)
    assert fake.contact["IsMultiplier2"] == 1
    assert beru.points(fake) == 25

    fake = make_self("K5TUX", "VE3ABC", bonus_count=2)
    beru.set_contact_vars(fake)
    assert fake.contact["IsMultiplier2"] == 1
    assert beru.points(fake) == 25

    fake = make_self("K5TUX", "VE3ABC", bonus_count=3)
    beru.set_contact_vars(fake)
    assert fake.contact["IsMultiplier2"] == 0
    assert beru.points(fake) == 5


def test_no_bonus_for_non_commonwealth():
    fake = make_self("K5TUX", "JAIABC", bonus_count=0)
    beru.set_contact_vars(fake)
    assert fake.contact["IsMultiplier2"] == 0
    assert beru.points(fake) == 0


def test_set_contact_vars_stores_exchange():
    fake = make_self("K5TUX", "VU2XYZ", rcv_nr="047", bonus_count=0)
    beru.set_contact_vars(fake)
    assert fake.contact["SNT"] == "599"
    assert fake.contact["RCV"] == "599"
    assert fake.contact["SentNr"] == "023"
    assert fake.contact["NR"] == "047"
    assert fake.contact["IsMultiplier2"] == 1
    assert fake.database.queries, "bonus count query was not issued"


def test_recalculate_mults_caps_three_bonuses_per_band():
    fake = make_self("K5TUX", "VE3ABC")

    def make_contact(idx, call, band):
        return {
            "Call": call,
            "Band": band,
            "TS": f"2025-03-08 12:00:0{idx}",
            "NR": "001",
            "IsMultiplier1": 1,
            "IsMultiplier2": 1,
            "Points": 999,
        }

    fake.database.contacts = [
        make_contact(1, "VE1AAA", 14.0),
        make_contact(2, "VE2BBB", 14.0),
        make_contact(3, "VE3CCC", 14.0),
        make_contact(4, "VE4DDD", 14.0),  # 4th on 20m: no bonus
        make_contact(5, "VK1EEE", 14.0),  # non-bonus? still Commonwealth, past cap
        make_contact(6, "ZL1FFF", 7.0),  # different band: bonus again
    ]
    beru.recalculate_mults(fake)
    saved = fake.database.saved
    flags = [contact["IsMultiplier2"] for contact in saved]
    assert flags == [1, 1, 1, 0, 0, 1]
    assert all(contact["IsMultiplier1"] == 0 for contact in saved)
    points_list = [contact["Points"] for contact in saved]
    # NA->NA is 5 pts; NA->OC (VK/ZL) is 10 pts; bonus adds 20.
    assert points_list == [25, 25, 25, 5, 10, 30]


def test_show_mults_and_score():
    fake = make_self("K5TUX", "VE3ABC")

    class DB(FakeDatabase):
        def fetch_qso_count(self):
            return {"qsos": 42}

        def fetch_points(self):
            return {"Points": 330}

    fake.database = DB()
    assert beru.show_mults(fake) == 0
    assert beru.show_qso(fake) == 42
    assert beru.calc_score(fake) == 330
