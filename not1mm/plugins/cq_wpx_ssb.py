"""CQ WPX SSB plugin"""
from PyQt5 import QtWidgets

name = "CQ WPX SSB"
carillo_name = "CQWPXSSB"
mode = "SSB"  # CW SSB BOTH RTTY

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 4


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
    self.field3.show()
    self.field4.show()
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("SentNR")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("RcvNR")


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.field1.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.field2.findChild(
            QtWidgets.QLineEdit
        ),
        self.field2.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field4.findChild(
            QtWidgets.QLineEdit
        ),
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
        self.field4.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = self.other_2.text()
    if self.contact.get("WPXPrefix"):
        result = self.database.fetch_wpx_exists(self.contact.get("WPXPrefix", ""))
        if result.get("wpx_count"):
            self.contact["IsMultiplier1"] = 0
        else:
            self.contact["IsMultiplier1"] = 1


def prefill(self):
    """Fill SentNR"""
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1"))
    field = self.field3.findChild(QtWidgets.QLineEdit)
    if len(field.text()) == 0:
        field.setText(serial_nr)


def points(self):
    """Calc point"""
    result = self.cty_lookup(self.pref.get("callsign", ""))
    if result:
        for item in result.items():
            mycountry = item[1].get("entity", "")
            mycontinent = item[1].get("continent", "")
    result = self.cty_lookup(self.contact.get("Call", ""))
    band = int(int(float(self.contact.get("Freq"))) / 1000)
    if result:
        for item in result.items():
            entity = item[1].get("entity", "")
            continent = item[1].get("continent", "")
            if mycountry.upper() == entity.upper():
                return 1
            if mycontinent and continent == "NA":
                if band in [28, 21, 14]:
                    return 2
                return 4
            if mycontinent == continent:
                if band in [28, 21, 14]:
                    return 1
                return 2
            if band in [28, 21, 14]:
                return 3
            return 6
    return 0


def show_mults(self):
    """Return display string for mults"""
    result = self.database.fetch_wpx_count()
    return int(result.get("wpx_count", 0))


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    return int(result.get("qsos", 0))


def get_points(self):
    """Return raw points before mults"""
    result = self.database.fetch_points()
    return int(result.get("Points", 0))


def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()
    contest_points = int(result.get("Points", 0))
    result = self.database.fetch_wpx_count()
    mults = int(result.get("wpx_count", 0))
    return contest_points * mults
