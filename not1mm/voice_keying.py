#!/usr/bin/env python3

"""
Not1MM Contest logger
Email: michael.bridak@gmail.com
GPL V3
Class: Voice
Purpose: A voice keying class to handle playing soundfiles and activating PTT
         Run in it's own thread.
"""

# pylint: disable=unused-import, c-extension-no-member, no-member, invalid-name, too-many-lines
# pylint: disable=logging-fstring-interpolation, line-too-long, no-name-in-module

import logging
from pathlib import Path

try:
    import sounddevice as sd
except OSError as exception:
    print(exception)
    print("portaudio is not installed")
    sd = None
import soundfile as sf

from PyQt6.QtCore import QObject, pyqtSignal, QThread

logger = logging.getLogger("voice_keying")


class Voice(QObject):
    """Voice class"""

    ptt_on = pyqtSignal()
    ptt_off = pyqtSignal()
    data_path = None
    current_op = None
    sounddevice = None
    voicings = []

    def __init__(self) -> None:
        super().__init__()
        """setup interface"""

    def run(self):
        while True:
            keyed = False
            while len(self.voicings):
                if not keyed:
                    self.ptt_on.emit()
                    keyed = True
                filename = self.voicings.pop(0)
                if Path(filename).is_file():
                    logger.debug("Voicing: %s", filename)
                    data, _fs = sf.read(filename, dtype="float32")
                    try:
                        sd.default.device = self.sounddevice
                        sd.default.samplerate = 44100.0
                        sd.play(data, blocking=True)
                        # https://snyk.io/advisor/python/sounddevice/functions/sounddevice.PortAudioError
                    except sd.PortAudioError as err:
                        logger.warning("%s", f"{err}")
            if keyed:
                self.ptt_off.emit()
            QThread.msleep(100)

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
        op_path = self.data_path / self.current_op
        if "[" in the_string:
            sub_string = the_string.strip("[]").lower()
            filename = f"{str(op_path)}/{sub_string}.wav"
            if Path(filename).is_file():
                self.voicings.append(filename)
            return
        for letter in the_string.lower():
            if letter in "abcdefghijklmnopqrstuvwxyz 1234567890":
                if letter == " ":
                    letter = "space"
                filename = f"{str(op_path)}/{letter}.wav"
                if Path(filename).is_file():
                    logger.debug("Voicing: %s", filename)
                    self.voicings.append(filename)
