from PyQt5 import QtWidgets

name = "ARRL DX Phone"
mode = "BOTH"  # CW SSB BOTH RTTY

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 4


def interface(self):
    ...


def set_tab_next(self):
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
