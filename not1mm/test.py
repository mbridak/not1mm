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

import threading

import sounddevice as sd
import soundfile as sf

print(f"{sd.query_devices()}")

FILENAME = "/home/mbridak/Nextcloud/dev/the-last-blade/Assets/sounds/zombie_kick.wav"
current_frame = 0
event = threading.Event()


def callback(outdata, frames, _time, status):
    """docstring"""
    global current_frame
    if status:
        print(status)
    chunksize = min(len(data) - current_frame, frames)
    outdata[:chunksize] = data[current_frame : current_frame + chunksize]
    if chunksize < frames:
        outdata[chunksize:] = 0
        raise sd.CallbackStop()
    current_frame += chunksize


data, fs = sf.read(FILENAME, always_2d=True)


stream = sd.OutputStream(
    samplerate=fs,
    device="pipewire",
    channels=data.shape[1],
    callback=callback,
    finished_callback=event.set,
)
with stream:
    event.wait()  # Wait until playback is finished
