# Not1MM

[![PyPI](https://img.shields.io/pypi/v/not1mm)](https://pypi.org/project/not1mm/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Made With:PyQt5](https://img.shields.io/badge/Made%20with-PyQt5-red)](https://pypi.org/project/PyQt5/)
[![Code Maturity:Snot Nosed](https://img.shields.io/badge/Code%20Maturity-Snot%20Nosed-red)](https://xkcd.com/1695/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/not1mm)](https://pypi.org/project/not1mm/)

![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

- [Not1MM](#not1mm)
  - [What and why is Not1MM](#what-and-why-is-not1mm)
  - [Current state](#current-state)
  - [Our Code Contributors ✨](#our-code-contributors-)
  - [List of should be working contests](#list-of-should-be-working-contests)
  - [Recent Changes](#recent-changes)
  - [Installing from PyPi](#installing-from-pypi)
    - [Python and pip](#python-and-pip)
    - [Installing with pip](#installing-with-pip)
      - [Ubuntu 22.04 LTS](#ubuntu-2204-lts)
      - [Ubuntu 23.04](#ubuntu-2304)
      - [Fedora 38](#fedora-38)
    - [You may or may not get a warning message like](#you-may-or-may-not-get-a-warning-message-like)
    - [Or this fan favorite](#or-this-fan-favorite)
    - [Updating with pip/pipx](#updating-with-pippipx)
  - [Other Libraries](#other-libraries)
    - [Dark mode on Ubuntu](#dark-mode-on-ubuntu)
  - [Wayland Compositor](#wayland-compositor)
  - [Running from source](#running-from-source)
  - [Various data file locations](#various-data-file-locations)
    - [Data](#data)
    - [Config](#config)
  - [The database](#the-database)
    - [Why](#why)
    - [The first one](#the-first-one)
    - [Why limit yourself](#why-limit-yourself)
    - [Revisiting an old friend](#revisiting-an-old-friend)
  - [Station Settings dialog (REQUIRED)](#station-settings-dialog-required)
    - [Changing station information](#changing-station-information)
  - [Adding a contest to the current dababase (REQUIRED)](#adding-a-contest-to-the-current-dababase-required)
  - [Selecting an existing contest as the current contest](#selecting-an-existing-contest-as-the-current-contest)
  - [Editing existing contest parameters](#editing-existing-contest-parameters)
  - [Configuration Settings](#configuration-settings)
    - [Lookup](#lookup)
    - [Soundcard](#soundcard)
    - [CAT](#cat)
    - [CW Keyer interface](#cw-keyer-interface)
    - [Cluster](#cluster)
    - [N1MM Packets](#n1mm-packets)
  - [Hiding screen elements](#hiding-screen-elements)
  - [Editing macro keys](#editing-macro-keys)
    - [Macro substitutions](#macro-substitutions)
    - [Macro use with voice](#macro-use-with-voice)
  - [cty.dat and QRZ lookups for distance and bearing](#ctydat-and-qrz-lookups-for-distance-and-bearing)
  - [Other uses for the call field](#other-uses-for-the-call-field)
  - [Windows](#windows)
    - [The Main Window](#the-main-window)
      - [Keyboard commands](#keyboard-commands)
    - [Log Display](#log-display)
      - [Editing a contact](#editing-a-contact)
  - [Recalulate Mults](#recalulate-mults)
  - [Bandmap](#bandmap)
  - [Cabrillo](#cabrillo)
  - [ADIF](#adif)
  - [Dupe checking](#dupe-checking)
  - [Contest specific notes](#contest-specific-notes)
    - [ARRL Sweekstakes](#arrl-sweekstakes)
      - [The exchange parser](#the-exchange-parser)
      - [The exchange](#the-exchange)

## What and why is Not1MM

Not1MM's interface is a blantent ripoff of N1MM.
It is NOT N1MM and any problem you have with this software should in no way reflect on their software.

If you use Windows(tm) you should run away from this and use someother program.

I personally don't. While it may be possible to get N1MM working under Wine, I haven't checked, I'd rather not have to jump thru the hoops.

**Currently this exists for my own personal amusement**.
Something to do in my free time.
While I'm not watching TV, Right vs Left political 'News' programs, mind numbing 'Reality' TV etc...

## Current state

The current state is "**BETA**". I've used it for A few contests, and was able to work contacts and submit a cabrillo at the end. I'm not a "Contester". So I'll add contests as/if I work them. I'm only one guy, so if you see a bug let me know. I don't do much of any Data or RTTY operating. This is why you don't see RTTY in the list of working contests. The Lord helps those who burn people at the... I mean who help themselves. Feel free to fill in that hole with a pull request.

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

## Our Code Contributors ✨

I wish to thank those who've contributed to the project.

<a href="https://github.com/mbridak/not1mm/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=mbridak/not1mm" />
</a>

## List of should be working contests

- General Logging (There are better general loggers like QLog, KLog, CQRLog)
- 10 10 Fall CW
- 10 10 Spring CW
- 10 10 Summer Phone
- 10 10 Winter Phone
- ARRL DX CW
- ARRL DX SSB
- ARRL Field Day
- ARRL Sweepstakes CW
- ARRL Sweepstakes SSB
- CQ WPX CW
- CQ WPX SSB
- CQ World Wide CW
- CQ World Wide SSB
- CWOps CWT
- IARU HF
- Japan International DX CW
- Japan International DX SSB
- RAC Canada Day

## Recent Changes

- [23-7-27] Check if bandwidth returned is not a number.
- [23-7-13] Add IARU HF contest.
- [23-7-11] Add mode to logwindow. Highlight already worked calls in bandmap. Add FM and AM to Field Day, since I guess it's still a thing.
- [23-7-5] Fix coredump in bandmap after CTRL-G.
- [23-7-2] bandmap now requests worked list at startup. Completed ARRL Field Day plugin.

See [CHANGELOG.md](CHANGELOG.md) for prior changes.

## Installing from PyPi

### Python and pip

This software is a Python package hosted on PyPi, and installable with the pip or pipx command. If this is your first exposure to pip you can get all the details from [The PyPA](https://packaging.python.org/en/latest/tutorials/installing-packages/). In short, most linux distros come with Python pre installed. If pip is not installed by default, you can usually load it through your package manager. For example `sudo apt install python3-pip` or `sudo dnf install python3-pip`.

### Installing with pip

I've included what installation steps I took to install on fresh images of Ubuntu and Fedora below. YMMV.

#### Ubuntu 22.04 LTS

```bash
sudo apt update
sudo apt upgrade
sudo apt install -y libportaudio2 python3-pip python3-pyqt5 python3-numpy adwaita-qt
pip install -U not1mm
```

#### Ubuntu 23.04

```bash
sudo apt update
sudo apt upgrade
sudo apt install -y libportaudio2 adwaita-qt pipx
pipx install not1mm
pipx ensurepath
```

Open a new terminal and type `not1mm`

#### Fedora 38

```bash
sudo dnf upgrade --refresh
sudo dnf install python3-pip portaudio
pip install not1mm
```

### You may or may not get a warning message like

```text
WARNING: The script not1mm is installed in '/home/mbridak/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

If you do, just logout and back in, or reboot.

### Or this fan favorite

```text
Warning: Ignoring XDG_SESSION_TYPE=wayland on Gnome. Use QT_QPA_PLATFORM=wayland to run on Wayland anyway.
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
```

To avoid this you can export an environment variable and launch the app like this:

`mbridak@vm:~$ export QT_QPA_PLATFORM=wayland; not1mm`

For a more permanent solution you can place the line `export QT_QPA_PLATFORM=wayland` in your home directories .bashrc file. Then after logging out and back in you should be able to launch it normally.

### Updating with pip/pipx

I've been posting updates just about everyday. Sometimes multiple times a day. It's early days, so there is much to do. You can check for and install updates with `pip install -U not1mm` or if installed with pipx `pipx upgrade not1mm`.

## Other Libraries

The audio library used, uses pipewire/portaudio. You may need to install portaudio. Ubuntu: `sudo apt install libportaudio2`

### Dark mode on Ubuntu

I believe I figured out dark mode in Ubuntu and have it working on my shack PC that runs Ubuntu 22.04. The secret sauce seems to be installing adwaita-qt with apt, and setting an environment variable `QT_STYLE_OVERRIDE` to `Adwaita-Dark`. I set the environment variable in the start of the program if running on a Gnome platform. So you don't need to do that part.

## Wayland Compositor

One side effect of Wayland is that we are not able to request for a window to regain or retain focus. So if you were to click on a spot in the bandmap window to tune to that spot, you would have to then click on the main window to continue entering contest data. I'm aware of this, but I can not change it.

## Running from source

Since this is packaged for PyPi, if you want to work on your own source branch, after cloning from github you would:

```bash
pip install --upgrade pip
pip install setuptools
pip install build
source rebuild.sh
```

from the root directory. This installs a build chain and a local editable copy of not1mm.

There's two ways to launch the program from the local editable copy.

You can either be in the root of the source directory and type:

```bash
python not1mm
```

or be in some other directory and just type:

```bash
not1mm
```

## Various data file locations

### Data

If your system has an `XDG_DATA_HOME` environment variable set, the database and CW macro files can be found there. Otherwise they will be found at `yourhome/.local/share/not1mm`

### Config

Configuration file(s) can be found at the location defined by `XDG_CONFIG_HOME`. Otherwise they will be found at `yourhome/.config/not1mm`

## The database

### Why

The database holds... wait for it... data... I know shocker right. A database can hold one or many contest logs. It also holds the station information, everything shown in the Station Settings dialog. You can have one database for the rest of your life. Filled with hundreds of contests you've logged. Or, you can create a new database to hold just one contest. You do You Boo.

### The first one

On the initial running, a database is created for you called `ham.db`. This, and all future databases, are located in the data directory mentioned above.

### Why limit yourself

You can create a new database by selecting `File` > `New Database` from the main window, and give it a snazzy name. Why limit yourself. Hell, create one every day for all I care. You can manage your own digital disaster.

### Revisiting an old friend

You can select a previously created databases for use by selecting `File` > `Open Database`.

## Station Settings dialog (REQUIRED)

After initial run of the program or creating a new database you will need to fill out the Station Settings dialog that will pop up.

![settings screen](https://github.com/mbridak/not1mm/raw/master/pic/settings.png)

You can fill it out if you want to. You can leave our friends behind. 'Cause your friends don't fill, and if they don't fill. Well, they're no friends of mine.

You can fill. You can fill. Everyone look at your keys.

[**I forgot my hat today**](https://www.youtube.com/watch?v=nM4okRvCg2g).

### Changing station information

Station information can be changed any time by going to `File` > `Station Settings` and editing the information.

## Adding a contest to the current dababase (REQUIRED)

Select `File` > `New Contest`

![New Contest Dialog](https://github.com/mbridak/not1mm/raw/master/pic/new_contest.png)

## Selecting an existing contest as the current contest

Select `File` > `Open Contest`

![Open an existing contest](https://github.com/mbridak/not1mm/raw/master/pic/select_contest.png)

## Editing existing contest parameters

You can edit the parameters of a previously defined contest by selecting it as the current contest. Then select `File` > `Edit Current Contest`. Click `OK` to save the new values and reload the contest. `Cancel` to keep the existing parameters.

## Configuration Settings

To setup your CAT control, CW keyer, Callsign lookups, select `File` > `Configuration Settings`

The tabs for groups and n1mm are disabled and are for future expansion.

![Configuration Settings screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_settings.png)

### Lookup

For callsign lookup, Two services are supported. QRZ and HamQTH. They require a username and password, Enter it here.

### Soundcard

Choose the sound output device for the voice keyer.

### CAT

Under the `CAT` TAB, you can choose either `rigctld` normally with an IP of `127.0.0.1` and a port of `4532`. Or `flrig`, IP normally of `127.0.0.1` and a port of `12345`. `None` is always an option, but is it really?

### CW Keyer interface

Under the `CW` TAB, There are three options. `cwdaemon`, which normally uses IP `127.0.0.1` and port `6789`. `pywinkeyer` which normally uses IP `127.0.0.1` and port `8000`. Or `None`, if you want to Morse it like it's 1899.

### Cluster

![Configuration Settings screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_cluster.png)

  Under the `Cluster` TAB you can change the default AR Cluster server, port and filter settings used for the bandmap window.

### N1MM Packets

Work has started on N1MM udp packets. So far just RadioInfo, contactinfo, contactreplace and contactdelete.

![N1MM Packet Configuration Screen](https://github.com/mbridak/not1mm/blob/master/pic/n1mm_packet_config.png?raw=true)

When entering IP and Ports, enter them with a colon ':' between them. You can enter multiple pairs on the same line if separated by a space ' '.

## Hiding screen elements

You can show or hide certain buttons/indicators by checking and unchecking their boxes under the view menu. You can then resize the screen to make it more compact.

![View Menu](https://github.com/mbridak/not1mm/raw/master/pic/view_menu.png)

The your choices will be remembered when you relaunch the program.

## Editing macro keys

To edit the macros, choose `File` > `Edit Macros`. This will open your systems registered text editor with current macros loaded. When your done just save the file and close the editor. The file loaded to edit, CW or SSB, will be determined by your current operating mode.

After editing and saving the macro file. You can force the logger to reload the macro file by toggeling between `Run` and `S&P` states.

### Macro substitutions

You can include a limited set of substitution instructions.

|Macro|Substitution|
|---|---|
| {MYCALL} | Sends the station call. |
| {HISCALL} | Send what's in the callsign field. |
| {SNT} | Sends 5nn (cw) or 599 (ssb) |
| {SENTNR} | Sends whats in the SentNR field. |
| {EXCH} | Sends what's in the Sent Exchange field when contest is defined. |
| '#' | Sends serial number. |

### Macro use with voice

The macros when used with voice, will also accept filenames of WAV files to play, excluding the file extension. The filename must be enclosed by brackets. For example `[CQ]` will play `cq.wav`, `[again]` will play `again.wav`. The wav files are stored in the operators personal data directory. The filenames must be in lowercase. See [Various data file locations](#various-data-file-locations) above for the location of your data files. For me, the macro `[cq]` will play `/home/mbridak/.local/share/not1mm/K6GTE/cq.wav`

**The current wav files in place are not the ones you will want to use. They sound like an idiot.** You can use something like Audacity to record new wav files in your own voice.

Aside from the `[filename]` wav files, there are also NATO phonetic wav files for each letter and number. So if your macro key holds `{HISCALL} {SNT} {SENTNR}` and you have entered K5TUX in callsign field during CQ WW SSB while in CQ Zone 3. You'll here Kilo 5 Tango Uniform X-ray, 5 9 9, 3. Hopefully not in an idiots voice.

## cty.dat and QRZ lookups for distance and bearing

When a callsign is entered, a look up is first done in a cty.dat file to determin the country of origin, geographic center, cq zone and ITU region. Great circle calculations are done to determin the heading and distance from your gridsquare to the grographic center. This information then displayed at the bottom left.

![snapshot of heading and distance](https://github.com/mbridak/not1mm/raw/master/pic/heading_distance.png)

After this, a request is made to QRZ for the gridsquare of the callsign. If there is a response the information is recalculated and displayed. You'll know is this has happened, since the gridsquare will replace the word "Regional".

![snapshot of heading and distance](https://github.com/mbridak/not1mm/raw/master/pic/heading_distance_qrz.png)

## Other uses for the call field

- [A Frequency] You can enter a frequency in kilohertz. This will change the band you're logging on. If you have CAT control, this will change the frequency of the radio as well.
- [CW, SSB, RTTY] You can set the mode logged. If you have CAT control this will also change the mode on the radio.
- [OPON] Change the operator currently logging.

**You must press the SPACE bar after entering any of the above.**

## Windows

### The Main Window

![Main screen with callouts](https://github.com/mbridak/not1mm/raw/master/pic/mainwithcallouts.png)

#### Keyboard commands

| Key | Result |
| -------------- | --- |
| [Esc] | Clears the input fields of any text. |
| [CTRL-Esc] | Stops cwdaemon from sending Morse. |
| [PgUp] | Increases the cw sending speed. |
| [PgDown] | Decreases the cw sending speed. |
| [Arrow-Up] | Jump to the next spot above the current VFO cursor in the bandmap window (CAT Required). |
| [Arrow-Down] | Jump to the next spot below the current VFO cursor in the bandmap window (CAT Required). |
| [TAB] | Move cursor to the right one field. |
| [Shift-Tab] | Move cursor left One field. |
| [SPACE] | When in the callsign field, will move the input to the first field needed for the exchange. |
| [Enter] | Submits the fields to the log. |
| [F1-F12] | Send (CW or Voice) macros. |
| [CTRL-S] | Spot Callsign to the cluster. |
| [CTRL-G] | Tune to a spot matching partial text in the callsign entry field (CAT Required). |

### Log Display

`Window`>`Log Window`

The Log display gets updated automatically when a contact is entered. The top half is a list of all contacts.

![Log Display Window](https://github.com/mbridak/not1mm/raw/master/pic/logdisplay.png)

The bottom half of the log displays contacts sorted by what's currently in the call entry field. The columns displayed in the log window are dependant on what contests is currently active.

#### Editing a contact

![Editing a cell](https://github.com/mbridak/not1mm/raw/master/pic/edit_cell.png)

You can double click a cell in the log window and edit its contents.

You can also Right-Click on a cell to bring up the edit dialog.

![right click edit dialog](https://github.com/mbridak/not1mm/raw/master/pic/edit_dialog.png)

You can not directly edit the multiplier status of a contact. Instead see the next section on recalculating mults. If you change the callsign make sure the `WPX` field is still valid.

## Recalulate Mults

After editing a contact and before generating a Cabrillo file. There is a Misc menu option that will recalculate the multipliers incase an edit had caused a change.

## Bandmap

`Window`>`Bandmap`

Put your callsign in the top and press the connect button.

The bandmap window is, as with everything, a work in progress. The bandmap now follows the VFO.

![Bandmap Window](https://github.com/mbridak/not1mm/raw/master/pic/bandmap.png)

VFO indicator now displays as small triangle in the frequency tickmarks. A small blue rectangle shows the receivers bandwidth.

![Bandmap Window](https://github.com/mbridak/not1mm/raw/master/pic/VFO_and_bandwidth_markers.png)

Clicked on spots now tune the radio and set the callsign field. Previously worked calls are displayed in red.

## Cabrillo

Click on `File` > `Generate Cabrillo`

The file will be placed in your home directory. The name will be in the format of:

`StationCall`_`ContestName`.log

So for me it would be:

K6GTE_CQ-WPX-SSB.log

## ADIF

`File` > `Generate ADIF`

Boom... ADIF

`StationCall`_`ContestName`.adi

## Dupe checking

Added dupe checking. Big Red 'Dupe' will appear if it's a dupe...

## Contest specific notes

I found it might be beneficial to have a section devoted to wierd quirky things about operating a specific contests.

### ARRL Sweekstakes

#### The exchange parser

This was a pain in the tukus. There are so many elements to the exchange, and one input field aside from the callsign field. So I had to write sort of a 'parser'. The parser moves over your input string following some basic rules and is re-evaluated with each keypress and the parsed result will be displayed in the label over the field. The exchange looks like `124 A K6GTE 17 ORG`, a Serial number, Precidence, Callsign, Year Licenced and Section. even though the callsign is given as part of the exchange, the callsign does not have to be entered and is pulled from the callsign field. If the exchange was entered as `124 A 17 ORG` you would see:

![SS Parser Result](https://github.com/mbridak/not1mm/raw/master/pic/ss_parser_1.png)

You can enter the serial number and precidence, or the year and section as pairs. For instance `124A 17ORG`. This would ensure the values get parsed correctly.

You do not have to go back to correct typing. You can just tack the correct items to the end of the field and the older values will get overwritten. So if you entered `124A 17ORG Q`, the precidence will change from A to Q. If you need to change the serial number you must append the precidence to it, `125A`.

If the callsign was entered wrong in the callsign field, you can put the correct callsign some where in the exchange. As long as it shows up in the parsed label above correctly your good.

The best thing you can do is play around with it to see how it behaves.

#### The exchange

In the `Sent Exchange` field of the New Contest dialog put in the Precidence, Call, Check and Section. Example: `A K6GTE 17 ORG`.

For the Run Exchange macro I'd put `{HISCALL} # A K6GTE 17 ORG`.
