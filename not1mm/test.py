#!/usr/bin/env python3
"""
K6GTE Contest logger
Email: michael.bridak@gmail.com
GPL V3
"""

# playing with sound

# pylint: disable=too-many-lines
# pylint: disable=invalid-name
# pylint: disable=no-member
# pylint: disable=no-name-in-module
# pylint: disable=c-extension-no-member
# pylint: disable=unused-import

# import threading

import sounddevice as sd
import soundfile as sf

print(f"{sd.query_devices(kind='output')}")

# FILENAME = "/home/mbridak/.local/share/not1mm/K6GTE/z.wav"
# current_frame = 0
# event = threading.Event()

callsign = "k6gte 599 org"


# def callback(outdata, frames, _time, status):
#     """docstring"""
#     global current_frame
#     if status:
#         print(status)
#     chunksize = min(len(data) - current_frame, frames)
#     outdata[:chunksize] = data[current_frame : current_frame + chunksize]
#     if chunksize < frames:
#         outdata[chunksize:] = 0
#         raise sd.CallbackStop()
#     current_frame += chunksize


# data, fs = sf.read(FILENAME)


for letter in callsign:
    if letter == " ":
        letter = "space"
    filename = f"/home/mbridak/.local/share/not1mm/K6GTE/{letter}.wav"
    print(filename)
    data, fs = sf.read(filename, dtype="float32")

    sd.play(data, fs)
    _status = sd.wait()
