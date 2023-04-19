"""ARRL plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable

from PyQt5 import QtWidgets

name = "ARRL DX SSB"
cabrillo_name = "ARRL-DX-SSB"
mode = "SSB"  # CW SSB BOTH RTTY
columns = [0, 1, 2, 3, 4, 10, 11, 14, 15]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.hide()
    self.field4.show()
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Power")


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.field1.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field2.findChild(QtWidgets.QLineEdit): self.field4.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field4.findChild(QtWidgets.QLineEdit): self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.field4.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field2.findChild(QtWidgets.QLineEdit): self.field1.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field4.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["Power"] = self.other_2.text().upper()
    self.contact["NR"] = self.other_2.text().upper()
    self.contact["SentNr"] = self.contest_settings.get("SentExchange", 0)


def prefill(self):
    """Fill CQ Zone"""
    # if len(self.other_2.text()) == 0:
    #     self.other_2.setText(str(self.contact.get("ZN", "")))
    self.other_1.setText(str(self.contest_settings.get("SentExchange", 0)))


def points(self):
    """Calc point"""
    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        for item in result.items():
            mycountry = item[1].get("entity", "")
            # mycontinent = item[1].get("continent", "")
    result = self.cty_lookup(self.contact.get("Call", ""))
    if result:
        for item in result.items():
            entity = item[1].get("entity", "")
            # continent = item[1].get("continent", "")
            if mycountry in ["K", "VE"]:
                if entity in ["K", "VE"]:
                    return 0
                return 3
            if entity in ["K", "VE"]:
                return 3
            return 0
    return 0


def show_mults(self):
    """Return display string for mults"""
    result = self.database.fetch_arrldx_country_band_count()
    if result:
        return int(result.get("cb_count", 0))
    return 0


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def get_points(self):
    """Return raw points before mults"""
    result = self.database.fetch_points()
    if result:
        return int(result.get("Points", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        contest_points = int(score)
        mults = show_mults(self)
        return contest_points * mults
    return 0


def adif(self):
    """
    Creates an ADIF file of the contacts made.
    """


def cabrillo(self):
    """Generates Cabrillo file. Maybe."""


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
    # f"select count(*) as wpx_count from dxlog where  TS < '{time_stamp}' and WPXPrefix = '{wpx}'
    # and ContestNR = {self.current_contest};"

    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        time_stamp = contact.get("TS")
        entity = contact.get("CountryPrefix")
        query = (
            f"select count(*) as prefix_count from dxlog where  TS < '{time_stamp}' "
            f"and CountryPrefix = '{entity}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        result = self.database.exec_sql(query)
        count = result.get("prefix_count", 1)
        if count == 0 and contact.get("Points", 0) == 3:
            contact["IsMultiplier1"] = 1
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)
