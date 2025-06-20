"""Settings Dialog Class"""

import logging
from PyQt6 import QtWidgets, uic

try:
    import sounddevice as sd
except OSError:
    sd = None


class Settings(QtWidgets.QDialog):
    """Settings dialog"""

    def __init__(self, app_data_path, pref, parent=None):
        """initialize dialog"""
        super().__init__(parent)
        self.logger = logging.getLogger("settings")
        uic.loadUi(app_data_path / "configuration.ui", self)
        # self.tabWidget.setTabVisible(5, False)
        # self.group_tab.hide()
        self.buttonBox.accepted.connect(self.save_changes)
        self.usecwdaemon_radioButton.clicked.connect(self.set_cwdaemon_port_hint)
        self.usepywinkeyer_radioButton.clicked.connect(self.set_winkeyer_port_hint)
        self.usecwviacat_radioButton.clicked.connect(self.set_catforcw_port_hint)
        self.cwport_field.setToolTip(
            "Usually 6789 for cwdaemon and 8000 for pywinkeyer."
        )
        self.rigcontrolport_field.setToolTip(
            "Usually 4532 for rigctld and 12345 for flrig."
        )
        self.preference = pref
        if sd:
            self.devices = sd.query_devices()
        else:
            self.devices = []
        self.setup()

    def setup(self):
        """setup dialog"""

        self.send_rtc_scores.setChecked(
            bool(self.preference.get("send_rtc_scores", False))
        )

        value = self.preference.get("rtc_url", "")
        index = self.rtc_url.findText(value)
        if index != -1:
            self.rtc_url.setCurrentIndex(index)

        self.rtc_user.setText(str(self.preference.get("rtc_user", "")))
        self.rtc_pass.setText(str(self.preference.get("rtc_pass", "")))
        self.rtc_interval.setText(str(self.preference.get("rtc_interval", "2")))

        self.auto_cq_delay.setText(str(self.preference.get("auto_cq_interval", "15")))

        self.connect_to_server.setChecked(bool(self.preference.get("useserver", False)))

        self.use_call_history.setChecked(
            bool(self.preference.get("use_call_history", False))
        )

        self.qsy_on_change.setChecked(bool(self.preference.get("sandpqsy", False)))

        self.use_esm.setChecked(bool(self.preference.get("use_esm", False)))

        value = self.preference.get("esm_agn", "DISABLED")
        index = self.esm_agn.findText(value)
        if index != -1:
            self.esm_agn.setCurrentIndex(index)

        value = self.preference.get("esm_cq", "DISABLED")
        index = self.esm_cq.findText(value)
        if index != -1:
            self.esm_cq.setCurrentIndex(index)

        value = self.preference.get("esm_exch", "DISABLED")
        index = self.esm_exch.findText(value)
        if index != -1:
            self.esm_exch.setCurrentIndex(index)

        value = self.preference.get("esm_hiscall", "DISABLED")
        index = self.esm_hiscall.findText(value)
        if index != -1:
            self.esm_hiscall.setCurrentIndex(index)

        value = self.preference.get("esm_mycall", "DISABLED")
        index = self.esm_mycall.findText(value)
        if index != -1:
            self.esm_mycall.setCurrentIndex(index)

        value = self.preference.get("esm_qrz", "DISABLED")
        index = self.esm_qrz.findText(value)
        if index != -1:
            self.esm_qrz.setCurrentIndex(index)

        value = self.preference.get("esm_qsob4", "DISABLED")
        index = self.esm_qsob4.findText(value)
        if index != -1:
            self.esm_qsob4.setCurrentIndex(index)

        for device in self.devices:
            if device.get("max_output_channels"):
                self.sounddevice.addItem(device.get("name"))
        value = self.preference.get("sounddevice", "default")
        index = self.sounddevice.findText(value)
        if index != -1:
            self.sounddevice.setCurrentIndex(index)
        self.useqrz_radioButton.setChecked(bool(self.preference.get("useqrz")))
        self.usehamqth_radioButton.setChecked(bool(self.preference.get("usehamqth")))
        self.lookup_user_name_field.setText(
            str(self.preference.get("lookupusername", ""))
        )
        self.lookup_password_field.setText(
            str(self.preference.get("lookuppassword", ""))
        )
        self.rigcontrolip_field.setText(str(self.preference.get("CAT_ip", "")))
        self.rigcontrolport_field.setText(str(self.preference.get("CAT_port", "")))
        self.catpoll_field.setText(str(self.preference.get("CAT_polldelta", 500)))
        self.userigctld_radioButton.setChecked(bool(self.preference.get("userigctld")))
        self.useflrig_radioButton.setChecked(bool(self.preference.get("useflrig")))

        self.rotctld_address.setText(str(self.preference.get("rotctld_address", "")))
        self.rotctld_port.setText(str(self.preference.get("rotctld_port", "")))

        self.cwip_field.setText(str(self.preference.get("cwip", "")))
        if self.preference.get("cwport", ""):
            self.cwport_field.setText(str(self.preference.get("cwport", "")))
        else:
            self.cwport_field.setText("")
        self.usecwdaemon_radioButton.setChecked(
            bool(self.preference.get("cwtype") == 1)
        )
        self.usepywinkeyer_radioButton.setChecked(
            bool(self.preference.get("cwtype") == 2)
        )
        self.usecwviacat_radioButton.setChecked(
            bool(self.preference.get("cwtype") == 3)
        )
        if self.preference.get("cwtype") == 1:
            self.set_cwdaemon_port_hint()
        elif self.preference.get("cwtype") == 2:
            self.set_winkeyer_port_hint()
        elif self.preference.get("cwtype") == 3:
            self.set_catforcw_port_hint()
        self.cwpaddingchar_field.setText(self.preference.get("cwpaddingchar", "T"))
        self.cwpaddinglength_field.setText(
            str(self.preference.get("cwpaddinglength", "3"))
        )

        self.connect_to_server.setChecked(bool(self.preference.get("useserver", False)))
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
        self.n1mm_radioport.setText(str(self.preference.get("n1mm_radioport", "")))
        self.n1mm_contactport.setText(str(self.preference.get("n1mm_contactport", "")))
        self.n1mm_lookupport.setText(str(self.preference.get("n1mm_lookupport", "")))
        self.n1mm_scoreport.setText(str(self.preference.get("n1mm_scoreport", "")))
        self.send_n1mm_radio.setChecked(bool(self.preference.get("send_n1mm_radio")))
        self.send_n1mm_contact.setChecked(
            bool(self.preference.get("send_n1mm_contact"))
        )
        self.send_n1mm_lookup.setChecked(bool(self.preference.get("send_n1mm_lookup")))
        self.send_n1mm_score.setChecked(bool(self.preference.get("send_n1mm_score")))

        self.cluster_server_field.setText(
            str(self.preference.get("cluster_server", "dxc.nc7j.com"))
        )
        self.cluster_port_field.setText(str(self.preference.get("cluster_port", 7373)))
        self.cluster_password_field.setText(
            str(self.preference.get("cluster_password", ""))
        )
        self.cluster_filter.setText(self.preference.get("cluster_filter", ""))
        value = self.preference.get("cluster_mode", "")
        index = self.cluster_mode.findText(value)
        if index != -1:
            self.cluster_mode.setCurrentIndex(index)

        self.activate_160m.setChecked(bool("160" in self.preference.get("bands", [])))
        self.activate_80m.setChecked(bool("80" in self.preference.get("bands", [])))
        self.activate_60m.setChecked(bool("60" in self.preference.get("bands", [])))
        self.activate_40m.setChecked(bool("40" in self.preference.get("bands", [])))
        self.activate_30m.setChecked(bool("30" in self.preference.get("bands", [])))
        self.activate_20m.setChecked(bool("20" in self.preference.get("bands", [])))
        self.activate_17m.setChecked(bool("17" in self.preference.get("bands", [])))
        self.activate_15m.setChecked(bool("15" in self.preference.get("bands", [])))
        self.activate_12m.setChecked(bool("12" in self.preference.get("bands", [])))
        self.activate_10m.setChecked(bool("10" in self.preference.get("bands", [])))
        self.activate_6m.setChecked(bool("6" in self.preference.get("bands", [])))
        self.activate_4m.setChecked(bool("4" in self.preference.get("bands", [])))
        self.activate_2m.setChecked(bool("2" in self.preference.get("bands", [])))
        self.activate_1dot25.setChecked(
            bool("1.25" in self.preference.get("bands", []))
        )
        self.activate_70cm.setChecked(bool("70cm" in self.preference.get("bands", [])))
        self.activate_33cm.setChecked(bool("33cm" in self.preference.get("bands", [])))
        self.activate_23cm.setChecked(bool("23cm" in self.preference.get("bands", [])))

    def set_cwdaemon_port_hint(self):
        """Sets placeholder hint for the CW interface."""
        self.cwip_field.setPlaceholderText("127.0.0.1")
        self.cwport_field.setPlaceholderText("6789")

    def set_winkeyer_port_hint(self):
        """Sets placeholder hint for the CW interface."""
        self.cwip_field.setPlaceholderText("127.0.0.1")
        self.cwport_field.setPlaceholderText("8000")

    def set_catforcw_port_hint(self):
        """Sets placeholder hint for the CW interface."""
        self.cwip_field.setPlaceholderText("")
        self.cwport_field.setPlaceholderText("")

    def save_changes(self):
        """
        Write preferences to json file.
        """
        self.preference["useserver"] = self.connect_to_server.isChecked()
        self.preference["send_rtc_scores"] = self.send_rtc_scores.isChecked()
        self.preference["rtc_url"] = self.rtc_url.currentText()
        self.preference["rtc_user"] = self.rtc_user.text()
        self.preference["rtc_pass"] = self.rtc_pass.text()
        try:
            self.preference["rtc_interval"] = int(self.rtc_interval.text())
        except ValueError:
            self.preference["rtc_interval"] = 2

        try:
            self.preference["auto_cq_interval"] = int(self.auto_cq_delay.text())
        except ValueError:
            self.preference["auto_cq_interval"] = 15

        self.auto_cq_delay.setText(str(self.preference.get("auto_cq_interval", "15")))

        self.preference["use_call_history"] = self.use_call_history.isChecked()

        self.preference["sandpqsy"] = self.qsy_on_change.isChecked()

        self.preference["use_esm"] = self.use_esm.isChecked()
        self.preference["esm_cq"] = self.esm_cq.currentText()
        self.preference["esm_agn"] = self.esm_agn.currentText()
        self.preference["esm_exch"] = self.esm_exch.currentText()
        self.preference["esm_hiscall"] = self.esm_hiscall.currentText()
        self.preference["esm_mycall"] = self.esm_mycall.currentText()
        self.preference["esm_qrz"] = self.esm_qrz.currentText()
        self.preference["esm_qsob4"] = self.esm_qsob4.currentText()

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
        try:
            self.preference["CAT_polldelta"] = int(self.catpoll_field.text())
        except ValueError:
            ...
        self.preference["userigctld"] = self.userigctld_radioButton.isChecked()
        self.preference["useflrig"] = self.useflrig_radioButton.isChecked()

        self.preference["rotctld_address"] = self.rotctld_address.text()
        try:
            self.preference["rotctld_port"] = int(self.rotctld_port.text())
        except ValueError:
            self.preference["rotctld_port"] = 4533

        self.preference["cwip"] = self.cwip_field.text()
        try:
            self.preference["cwport"] = int(self.cwport_field.text())
        except ValueError:
            self.preference["cwport"] = None
            ...
        self.preference["cwpaddingchar"] = self.cwpaddingchar_field.text()
        try:
            self.preference["cwpaddinglength"] = int(self.cwpaddinglength_field.text())
        except ValueError:
            self.preference["cwpaddinglength"] = 3
        self.preference["cwtype"] = 0
        if self.usecwdaemon_radioButton.isChecked():
            self.preference["cwtype"] = 1
        elif self.usepywinkeyer_radioButton.isChecked():
            self.preference["cwtype"] = 2
        elif self.usecwviacat_radioButton.isChecked():
            self.preference["cwtype"] = 3
        self.preference["useserver"] = self.connect_to_server.isChecked()
        self.preference["multicast_group"] = self.multicast_group.text()
        self.preference["multicast_port"] = self.multicast_port.text()
        self.preference["interface_ip"] = self.interface_ip.text()

        self.preference["send_n1mm_packets"] = self.send_n1mm_packets.isChecked()

        self.preference["send_n1mm_radio"] = self.send_n1mm_radio.isChecked()
        self.preference["send_n1mm_contact"] = self.send_n1mm_contact.isChecked()
        self.preference["send_n1mm_lookup"] = self.send_n1mm_lookup.isChecked()
        self.preference["send_n1mm_score"] = self.send_n1mm_score.isChecked()

        self.preference["n1mm_station_name"] = self.n1mm_station_name.text()
        self.preference["n1mm_operator"] = self.n1mm_operator.text()
        # self.preference["n1mm_ip"] = self.n1mm_ip.text()
        self.preference["n1mm_radioport"] = self.n1mm_radioport.text()
        self.preference["n1mm_contactport"] = self.n1mm_contactport.text()
        self.preference["n1mm_lookupport"] = self.n1mm_lookupport.text()
        self.preference["n1mm_scoreport"] = self.n1mm_scoreport.text()
        self.preference["cluster_server"] = self.cluster_server_field.text()
        try:
            self.preference["cluster_port"] = int(self.cluster_port_field.text())
        except:
            ...
        self.preference["cluster_password"] = self.cluster_password_field.text()
        self.preference["cluster_filter"] = self.cluster_filter.text()
        self.preference["cluster_mode"] = self.cluster_mode.currentText()
        bandlist = list()
        if self.activate_160m.isChecked():
            bandlist.append("160")
        if self.activate_80m.isChecked():
            bandlist.append("80")
        if self.activate_60m.isChecked():
            bandlist.append("60")
        if self.activate_40m.isChecked():
            bandlist.append("40")
        if self.activate_30m.isChecked():
            bandlist.append("30")
        if self.activate_20m.isChecked():
            bandlist.append("20")
        if self.activate_17m.isChecked():
            bandlist.append("17")
        if self.activate_15m.isChecked():
            bandlist.append("15")
        if self.activate_12m.isChecked():
            bandlist.append("12")
        if self.activate_10m.isChecked():
            bandlist.append("10")
        if self.activate_6m.isChecked():
            bandlist.append("6")
        if self.activate_4m.isChecked():
            bandlist.append("4")
        if self.activate_2m.isChecked():
            bandlist.append("2")
        if self.activate_1dot25.isChecked():
            bandlist.append("1.25")
        if self.activate_70cm.isChecked():
            bandlist.append("70cm")
        if self.activate_33cm.isChecked():
            bandlist.append("33cm")
        if self.activate_23cm.isChecked():
            bandlist.append("23cm")
        self.preference["bands"] = bandlist
