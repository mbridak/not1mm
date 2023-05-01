"""Settings Dialog Class"""

import logging
from PyQt5 import QtWidgets, uic
import sounddevice as sd


class Settings(QtWidgets.QDialog):
    """Settings dialog"""

    def __init__(self, WORKING_PATH, CONFIG_PATH, pref, parent=None):
        """initialize dialog"""
        super().__init__(parent)
        self.logger = logging.getLogger("__main__")
        self.config_path = CONFIG_PATH
        uic.loadUi(WORKING_PATH + "/data/configuration.ui", self)
        self.buttonBox.accepted.connect(self.save_changes)
        self.preference = pref
        self.devices = sd.query_devices()
        self.setup()

    def setup(self):
        """setup dialog"""
        for device in self.devices:
            if device.get("max_output_channels"):
                self.sounddevice.addItem(device.get("name"))
        value = self.preference.get("sounddevice", "default")
        index = self.sounddevice.findText(value)
        if index != -1:
            self.sounddevice.setCurrentIndex(index)
        self.useqrz_radioButton.setChecked(bool(self.preference.get("useqrz")))
        # self.usehamdb_radioButton.setChecked(bool(self.preference.get("usehamdb")))
        self.usehamqth_radioButton.setChecked(bool(self.preference.get("usehamqth")))
        self.lookup_user_name_field.setText(
            str(self.preference.get("lookupusername", ""))
        )
        self.lookup_password_field.setText(
            str(self.preference.get("lookuppassword", ""))
        )
        self.rigcontrolip_field.setText(str(self.preference.get("CAT_ip", "")))
        self.rigcontrolport_field.setText(str(self.preference.get("CAT_port", "")))
        self.userigctld_radioButton.setChecked(bool(self.preference.get("userigctld")))
        self.useflrig_radioButton.setChecked(bool(self.preference.get("useflrig")))

        self.cwip_field.setText(str(self.preference.get("cwip", "")))
        self.cwport_field.setText(str(self.preference.get("cwport", "")))
        self.usecwdaemon_radioButton.setChecked(
            bool(self.preference.get("cwtype") == 1)
        )
        self.usepywinkeyer_radioButton.setChecked(
            bool(self.preference.get("cwtype") == 2)
        )
        self.connect_to_server.setChecked(bool(self.preference.get("useserver")))
        self.multicast_group.setText(str(self.preference.get("multicast_group", "")))
        self.multicast_port.setText(str(self.preference.get("multicast_port", "")))
        self.interface_ip.setText(str(self.preference.get("interface_ip", "")))

        self.send_n1mm_packets.setChecked(
            bool(self.preference.get("send_n1mm_packets"))
        )
        self.n1mm_station_name.setText(
            str(self.preference.get("n1mm_station_name", ""))
        )
        self.n1mm_operator.setText(str(self.preference.get("n1mm_operator", "")))
        self.n1mm_ip.setText(str(self.preference.get("n1mm_ip", "")))
        self.n1mm_radioport.setText(str(self.preference.get("n1mm_radioport", "")))
        self.n1mm_contactport.setText(str(self.preference.get("n1mm_contactport", "")))
        self.n1mm_lookupport.setText(str(self.preference.get("n1mm_lookupport", "")))
        self.n1mm_scoreport.setText(str(self.preference.get("n1mm_scoreport", "")))
        self.cluster_server_field.setText(
            str(self.preference.get("cluster_server", "dxc.nc7j.com"))
        )
        self.cluster_port_field.setText(str(self.preference.get("cluster_port", 7373)))

    def save_changes(self):
        """
        Write preferences to json file.
        """
        self.preference["sounddevice"] = self.sounddevice.currentText()
        self.preference["useqrz"] = self.useqrz_radioButton.isChecked()
        # self.preference["usehamdb"] = self.usehamdb_radioButton.isChecked()
        self.preference["usehamqth"] = self.usehamqth_radioButton.isChecked()
        self.preference["lookupusername"] = self.lookup_user_name_field.text()
        self.preference["lookuppassword"] = self.lookup_password_field.text()
        self.preference["CAT_ip"] = self.rigcontrolip_field.text()
        try:
            self.preference["CAT_port"] = int(self.rigcontrolport_field.text())
        except ValueError:
            ...
        self.preference["userigctld"] = self.userigctld_radioButton.isChecked()
        self.preference["useflrig"] = self.useflrig_radioButton.isChecked()
        self.preference["cwip"] = self.cwip_field.text()
        try:
            self.preference["cwport"] = int(self.cwport_field.text())
        except ValueError:
            ...
        self.preference["cwtype"] = 0
        if self.usecwdaemon_radioButton.isChecked():
            self.preference["cwtype"] = 1
        if self.usepywinkeyer_radioButton.isChecked():
            self.preference["cwtype"] = 2
        self.preference["useserver"] = self.connect_to_server.isChecked()
        self.preference["multicast_group"] = self.multicast_group.text()
        self.preference["multicast_port"] = self.multicast_port.text()
        self.preference["interface_ip"] = self.interface_ip.text()

        self.preference["send_n1mm_packets"] = self.send_n1mm_packets.isChecked()
        self.preference["n1mm_station_name"] = self.n1mm_station_name.text()
        self.preference["n1mm_operator"] = self.n1mm_operator.text()
        self.preference["n1mm_ip"] = self.n1mm_ip.text()
        self.preference["n1mm_radioport"] = self.n1mm_radioport.text()
        self.preference["n1mm_contactport"] = self.n1mm_contactport.text()
        self.preference["n1mm_lookupport"] = self.n1mm_lookupport.text()
        self.preference["n1mm_scoreport"] = self.n1mm_scoreport.text()
        self.preference["cluster_server"] = self.cluster_server_field.text()
        self.preference["cluster_port"] = int(self.cluster_port_field.text())
