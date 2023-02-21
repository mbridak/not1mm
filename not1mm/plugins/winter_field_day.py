from PyQt5 import QtWidgets

name = "Winter Field Day"


def interface(self):
    self.field1.hide()
    self.field2.hide()
    self.field3.show()
    self.field4.show()
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("Class")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Section")
