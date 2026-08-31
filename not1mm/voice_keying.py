"""
Not1MM Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: Voice
Purpose: A voice keying class to handle playing soundfiles and activating PTT
         Run in it's own thread.
"""

import logging
from pathlib import Path

try:
    import sounddevice as sd
except OSError as exception:
    print(exception)
    print("portaudio is not installed")
    sd = None
import soundfile as sf
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from not1mm.lib.preferences import Preferences

logger = logging.getLogger("voice_keying")


def has_output_device(sounddevice_name="default") -> bool:
    """Return True when the selected output audio device is available."""
    if sd is None:
        return False
    try:
        sd.check_output_settings(device=sounddevice_name)
    except (sd.PortAudioError, ValueError, TypeError):
        return False
    return True


class Voice(QObject):
    """Voice class"""

    ptt_on = pyqtSignal()
    ptt_off = pyqtSignal()
    data_path = None
    sounddevice = None
    nonblocking = False
    voicings = []  # noqa: RUF012

    def __init__(self) -> None:
        super().__init__()
        """setup interface"""
        self.pref = Preferences.data()

    def run(self):
        while True:
            keyed = False
            while len(self.voicings):
                if not has_output_device(self.sounddevice):
                    logger.warning("No available output sound device for voice keying.")
                    self.voicings.clear()
                    break
                if not keyed:
                    self.ptt_on.emit()
                    keyed = True
                filename = self.voicings.pop(0)
                self.nonblocking = len(self.voicings)
                if Path(filename).is_file():
                    logger.debug("Voicing: %s", filename)
                    data, _fs = sf.read(filename, dtype="float32")
                    try:
                        sd.default.device = self.sounddevice
                        sd.default.samplerate = 44100.0
                        sd.play(data, blocking=False)
                        if self.nonblocking > 0:
                            sd.wait()
                        # https://snyk.io/advisor/python/sounddevice/functions/sounddevice.PortAudioError
                    except sd.PortAudioError as err:
                        logger.warning("%s", f"{err}")
            try:
                while sd.get_stream().active:
                    QThread.msleep(100)
            except (RuntimeError, AttributeError):
                pass
            if keyed:
                self.ptt_off.emit()
            QThread.msleep(100)

    def stop_voice(self) -> None:
        """
        empty the voicings list and call sd.stop().


        Returns
        -------
        None
        """
        if sd is None:
            return
        self.voicings.clear()
        if self.nonblocking == 0:
            sd.stop()

    def voice_string(self, the_string: str) -> None:
        """
        voices string using nato phonetics.

        Parameters
        ----------
        the_string : str
        String to voicify.

        Returns
        -------
        None
        """

        logger.debug("Voicing: %s", the_string)
        if sd is None:
            logger.warning("Sounddevice/portaudio not installed.")
            return
        if not has_output_device(self.sounddevice):
            logger.warning("No available output sound device for voice keying.")
            return
        op_path = self.data_path / self.pref.get("current_op", "").replace("/", "-")

        char_iterator = iter(the_string.lower())

        for char in char_iterator:
            if char == "[":
                substring = ""
                for sub_char in char_iterator:
                    if sub_char == "]":
                        break
                    substring += sub_char
                filename = f"{op_path!s}/{substring}.wav"
                if Path(filename).is_file():
                    self.voicings.append(filename)
            if char in "abcdefghijklmnopqrstuvwxyz 1234567890[]":
                if char == " ":
                    char = "space"
                filename = f"{op_path!s}/{char}.wav"
                if Path(filename).is_file():
                    logger.debug("Voicing: %s", filename)
                    self.voicings.append(filename)
