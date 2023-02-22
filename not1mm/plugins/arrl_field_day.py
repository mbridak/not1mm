from PyQt5 import QtWidgets

name = "ARRL Field Day"
mode = "BOTH"  # CW SSB BOTH RTTY

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 3


def interface(self):
    self.field1.hide()
    self.field2.hide()
    self.field3.show()
    self.field4.show()
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("Class")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Section")
