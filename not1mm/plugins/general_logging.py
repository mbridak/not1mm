from PyQt5 import QtWidgets

name = "General Logging"
mode = "BOTH"  # CW SSB BOTH RTTY

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 4


def interface(self):
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("Name")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Comment")
    ...
