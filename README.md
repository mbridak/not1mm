# Not1MM
<!-- markdownlint-disable MD001 MD033 -->

 ![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

 The worlds #1 unfinished contest logger <sup>*According to my daughter Corinna.<sup>

[![PyPI](https://img.shields.io/pypi/v/not1mm)](https://pypi.org/project/not1mm/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Made With:PyQt6](https://img.shields.io/badge/Made%20with-PyQt6-blue)](https://pypi.org/project/PyQt6/)
[![Code Maturity:Snot Nosed](https://img.shields.io/badge/Code%20Maturity-Snot%20Nosed-red)](https://xkcd.com/1695/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/not1mm)](https://pypi.org/project/not1mm/)

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

- [Not1MM](#not1mm)
  - [What and Why is Not1MM](#what-and-why-is-not1mm)
    - [The Elephant in the Room](#the-elephant-in-the-room)
    - [The What](#the-what)
    - [Target Environment](#target-environment)
    - [The Why](#the-why)
  - [Current State](#current-state)
    - [Code Maturity](#code-maturity)
    - [Data and RTTY](#data-and-rtty)
    - [Other not so Supported Contests](#other-not-so-supported-contests)
  - [Our Code Contributors ✨](#our-code-contributors-)
  - [List of Should be Working Contests](#list-of-should-be-working-contests)
  - [Recent Changes](#recent-changes)
  - [Flatpak](#flatpak)
  - [Installation](#installation)
  - [Update your CTY and SCP files](#update-your-cty-and-scp-files)
  - [Various data file locations](#various-data-file-locations)
    - [Data](#data)
    - [Config](#config)
  - [The Database](#the-database)
    - [Why](#why)
    - [The first one is free](#the-first-one-is-free)
    - [Why limit yourself](#why-limit-yourself)
    - [Revisiting an old friend](#revisiting-an-old-friend)
  - [Station Settings dialog (It's REQUIRED Russ)](#station-settings-dialog-its-required-russ)
    - [Changing station information](#changing-station-information)
  - [Selecting a contest (It's REQUIRED Russ)](#selecting-a-contest-its-required-russ)
    - [Selecting a new contest](#selecting-a-new-contest)
    - [Selecting an existing contest as the current contest](#selecting-an-existing-contest-as-the-current-contest)
    - [Editing existing contest parameters](#editing-existing-contest-parameters)
  - [Configuration Settings](#configuration-settings)
    - [Lookup](#lookup)
    - [Soundcard](#soundcard)
    - [CAT Control](#cat-control)
    - [CW Keyer Interface](#cw-keyer-interface)
    - [Cluster](#cluster)
    - [N1MM Packets](#n1mm-packets)
    - [Bands](#bands)
    - [Options](#options)
  - [Logging WSJT-X FT8/FT4/ETC and FLDIGI RTTY contacts](#logging-wsjt-x-ft8ft4etc-and-fldigi-rtty-contacts)
  - [Sending CW](#sending-cw)
    - [Sending CW Macros](#sending-cw-macros)
    - [Auto CQ](#auto-cq)
      - [Setting the delay](#setting-the-delay)
      - [Cancelling the Auto CQ](#cancelling-the-auto-cq)
    - [Sending CW Free Form](#sending-cw-free-form)
    - [Editing macro keys](#editing-macro-keys)
    - [Macro substitutions](#macro-substitutions)
    - [Macro use with voice](#macro-use-with-voice)
      - [{VOICE1} - {VOICE10}](#voice1---voice10)
      - [Voice macro wave files](#voice-macro-wave-files)
  - [cty.dat and QRZ lookups for distance and bearing](#ctydat-and-qrz-lookups-for-distance-and-bearing)
  - [Other uses for the call field](#other-uses-for-the-call-field)
  - [The Windows](#the-windows)
    - [The Main Window](#the-main-window)
      - [Keyboard commands](#keyboard-commands)
    - [The Log Window](#the-log-window)
      - [Editing a contact](#editing-a-contact)
    - [The Bandmap Window](#the-bandmap-window)
    - [The Check Partial Window](#the-check-partial-window)
    - [The Rate Window](#the-rate-window)
    - [The DXCC window](#the-dxcc-window)
    - [The Rotator Window (Work In Progress)](#the-rotator-window-work-in-progress)
    - [The Remote VFO Window](#the-remote-vfo-window)
  - [Cabrillo](#cabrillo)
  - [ADIF](#adif)
  - [Recalulate Mults](#recalulate-mults)
  - [ESM](#esm)
    - [Run States](#run-states)
      - [CQ](#cq)
      - [Call Entered send His Call and the Exchange](#call-entered-send-his-call-and-the-exchange)
      - [Empty exchange field send AGN till you get it](#empty-exchange-field-send-agn-till-you-get-it)
      - [Exchange field filled, send TU QRZ and logs it](#exchange-field-filled-send-tu-qrz-and-logs-it)
    - [S\&P States](#sp-states)
      - [With his call entered, Send your call](#with-his-call-entered-send-your-call)
      - [If no exchange entered send AGN](#if-no-exchange-entered-send-agn)
      - [With exchange entered, send your exchange and log it](#with-exchange-entered-send-your-exchange-and-log-it)
  - [Call History Files](#call-history-files)
    - [Creating your own Call History files](#creating-your-own-call-history-files)
  - [Contest specific notes](#contest-specific-notes)
    - [ARRL Sweekstakes](#arrl-sweekstakes)
      - [The exchange parser](#the-exchange-parser)
      - [The exchange](#the-exchange)
    - [RAEM](#raem)
    - [RandomGram](#randomgram)
    - [UKEI DX](#ukei-dx)

## What and Why is Not1MM

### The Elephant in the Room

Not1MM's interface is a blatant ripoff of N1MM. It is NOT N1MM and any problem
you have with this software should in no way reflect on their software.

### The What

Not1MM attempts to be a useable amateur radio, or HAM, contest logger. It's
written in Python, 3.9+, and uses Qt6 framework for the graphical interface
and SQLite for the database.

### Target Environment

The primary target for this application is Linux. It may be able to run on other
platforms, BSD and Windows. But I don't have a way, or desire, to directly support them.

I've recently purchased an M4 Mac Mini, So I'll probably put more effort into that platform as well.

### The Why

**Currently this exists for my own personal amusement**. I've recently retired
after 35+ years working for 'The Phone Company', GTE -> Verizon -> Frontier.
And being a Gentleman of Leisure, needed something to do in my free time.
I'm a casual contester and could not find any contesting software for Linux that
I wanted to use. There is [Tucnak](http://tucnak.nagano.cz/) which is very robust
and mature. It just wasn't for me.

## Current State

### Code Maturity

The current state is "**BETA**".

I've used it for quite a few contests, and was able to work contacts and submit
cabrillos at the end. There are still quite a few features I'd like to implement.
And "BETA" is a sort of get out of jail free badge for coders. A safety net for
when the program craps the bed. I'm only one guy, so if you see a bug let me know.

### Data and RTTY

I've recently added portions of code to watch for WSTJ-X and fldigi QSOs. I've added
the Weekly RTTY Test, So RTTY could be tested. Also added FT8/4 and RTTY to ARRL Field
Day and ARRL VHF. Found it works better if you don't use FlDigi for making the QSO at all.
Rather just using it as a RTTY modem and sending the text for it to send from Not1MM
using the function keys or ESM.

### Other not so Supported Contests

Of note, state QSO parties. I haven't worked any yet. And no one has submitted a PR
adding one... So there you go. In the near future I'll probably add California, guess
where I live, and the 4 states QSO party.

## Our Code Contributors ✨

I wish to thank those who've contributed to the project. Below is an automatically
generated, 'cause I'm lazy, list of those who've submitted PR's.

<a href="https://github.com/mbridak/not1mm/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=mbridak/not1mm" alt="Avatar icons for code contributors." />
</a>

## List of Should be Working Contests

- General Logging
- 10 10 Fall CW
- 10 10 Spring CW
- 10 10 Summer Phone
- 10 10 Winter Phone
- ARI 40 80
- ARI DX
- ARRL 10M
- ARRL 160M
- ARRL DX CW, SSB
- ARRL Field Day
- ARRL RTTY Roundup
- ARRL Sweepstakes CW, SSB
- ARRL VHF January, June, September
- CQ 160 CW, SSB
- CQ WPX CW, RTTY, SSB
- CQ World Wide CW, RTTY, SSB
- CWOps CWT
- DARC Xmas
- DARC VHF
- EA Majistad CW
- EA Majistad SSB
- EA RTTY
- ES OPEN HF
- ES FIELD DAY HF
- Helvetia
- IARU Fieldday R1 CW, SSB
- IARU HF
- ICWC MST
- Japan International DX CW, SSB
- K1USN Slow Speed Test
- Labre RS Digi
- LZ DX
- NAQP CW, RTTY, SSB
- Phone Weekly Test
- RAEM
- RandomGram
- RAC Canada Day
- REF CW, SSB
- SAC CW, SSB
- SPDX
- Stew Perry Topband
- UK/EI DX
- Weekly RTTY
- Winter Field Day

## Recent Changes

- [25-7-12] Add Mode column to log window for IARU Field Day.
- [25-7-10] Improved checkpartial contrast if not using dark mode.
- [25-7-3] Fixed CAT online indicator.

See [CHANGELOG.md](CHANGELOG.md) for prior changes.

## Flatpak

I've tried for a couple days to get Not1MM to build as a flatpak. I've failed.
It keeps failing at building numpy. If you happen to be a flatpak savant, please
feel free to look at com.github.mbridak.not1mm.yaml and python3-modules.yaml and
clue me into the black magic needed to get it to work.

## Installation

The README is getting a bit long. So I'll start breaking out the following subsections into
their own markdown files. The first will be the [installation](INSTALL.md) section.

## Update your CTY and SCP files

After all the configuration stuff below and before operating in a contest, you
might want to update the CTY and SCP files. You can do this by choosing FILE->Update CTY and FILE->Update MASTER.SCP

## Various data file locations

### Data

If your system has an `XDG_DATA_HOME` environment variable set, the database and
CW macro files can be found there. Otherwise they will be found at
`yourhome/.local/share/not1mm`

### Config

Configuration file(s) can be found at the location defined by `XDG_CONFIG_HOME`.
Otherwise they will be found at `yourhome/.config/not1mm`

## The Database

### Why

The database holds... wait for it... data... I know shocker right. A database
can hold one or many contest logs. It also holds the station information,
everything shown in the Station Settings dialog. You can have one database for
the rest of your life. Filled with hundreds of contests you've logged. Or, you
can create a new database to hold just one contest. You do You Boo.

### The first one is free

On the initial running, a database is created for you called `ham.db`. This, and
all future databases, are located in the data directory mentioned above.

### Why limit yourself

You can create a new database by selecting `File` > `New Database` from the main
window, and give it a snazzy name. Why limit yourself. Hell, create one every
day for all I care. You can manage your own digital disaster.

### Revisiting an old friend

You can select a previously created databases for use by selecting
`File` > `Open Database`.

## Station Settings dialog (It's REQUIRED Russ)

After initial run of the program or creating a new database you will need to
fill out the Station Settings dialog that will pop up.

![settings screen](https://github.com/mbridak/not1mm/raw/master/pic/settings.png)

You can fill it out if you want to. You can leave our friends behind.
'Cause your friends don't fill, and if they don't fill. Well, they're no friends
of mine.

You can fill. You can fill. Everyone look at your keys.

[**I forgot my hat today**](https://www.youtube.com/watch?v=nM4okRvCg2g).

### Changing station information

Station information can be changed any time by going to
`File` > `Station Settings` and editing the information.

## Selecting a contest (It's REQUIRED Russ)

### Selecting a new contest

Select `File` > `New Contest`

![New Contest Dialog](https://github.com/mbridak/not1mm/raw/master/pic/new_contest.png)

### Selecting an existing contest as the current contest

Select `File` > `Open Contest`

![Open an existing contest](https://github.com/mbridak/not1mm/raw/master/pic/select_contest.png)

### Editing existing contest parameters

You can edit the parameters of a previously defined contest by selecting it as
the current contest. Then select `File` > `Edit Current Contest`. Click `OK` to
save the new values and reload the contest. `Cancel` to keep the existing
parameters.

## Configuration Settings

To setup your CAT control, CW keyer, and callsign lookups, select
`File` > `Configuration Settings`

The tabs for groups and n1mm are disabled and are for future expansion.

![Configuration Settings screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_settings.png)

### Lookup

For callsign lookup, two services are supported: QRZ and HamQTH. They require a
username and password. Enter that information here.

### Soundcard

Choose the appropriate sound output device for the voice keyer.

### CAT Control

Under the `CAT` tab, you can choose either: `rigctld` normally with an IP of
`127.0.0.1` and a port of `4532` or `flrig` with an IP normally of `127.0.0.1` and a
port of `12345`. `None` is always an option, but is it really? There's an
onscreen icon for CAT status. Green good, Red bad, Grey neither.

### CW Keyer Interface

Under the `CW` tab, there are three options: i) `cwdaemon` that normally uses IP address
`127.0.0.1`port `6789`, ii) `pywinkeyer` that normally uses IP address `127.0.0.1` port `8000`, and
iii) `CAT` that sends Morse characters via rigctld if your radio supports it.

For contests that require a serial number as part of the exchange, there is an option to pad it with leading zeroes,
typically represented by the cut number "T". For example, serial number "001" can be sent as "TT1". The user can
configure the `CW Sent Nr Padding` character (default: T) and `CW Sent Nr Padding
Length` (default: 3) or specify no padding by entering length "0".

### Cluster

![Configuration Settings screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_cluster.png)

Under the `Cluster` tab you can change the default AR Cluster server, port, and
filter settings used for the bandmap window.

### N1MM Packets

Work has started on N1MM udp packets. So far just RadioInfo, contactinfo,
contactreplace and contactdelete.

![N1MM Packet Configuration Screen](https://github.com/mbridak/not1mm/blob/master/pic/n1mm_packet_config.png?raw=true)

When entering IP and Ports, enter them with a colon ':' between them. You can
enter multiple pairs on the same line if separated by a space ' '.

### Bands

You can define which bands appear in the main window. Those with checkmarks will
appear. Those without will not.

![Bands Configuration Screen](https://github.com/mbridak/not1mm/raw/master/pic/configure_bands.png)

### Options

On the Options TAB you can:

- Select to use Enter Sends Message ([ESM](#esm)), and configure it's function keys.
- Select whether or not to use [Call History](#call-history-files) info.
- Select whether or not to send XML score info to online scoreboards.
- Select whether or not to clear input fields when you QSY while in S&P mode.

![Options Screen](https://github.com/mbridak/not1mm/blob/master/pic/configuration_options.png?raw=true)

Three realtime score boards are supported:

- Real Time Contest Server at hamscore.com
- Contest Online ScoreBoard at contestonlinescore.com
- LiveScore at contest.run

## Logging WSJT-X FT8/FT4/ETC and FLDIGI RTTY contacts

Not1MM listens for WSJT-X UDP traffic on the Multicast address 224.0.0.1:2237.
No setup is needed to be done on Not1MM's side. That's good because I'm lazy.

Not1MM watches for fldigi qso's by watching for UDP traffic from fldigi on 127.0.0.1:9876.

![fldigi configuration dialog](https://github.com/mbridak/not1mm/blob/master/pic/fldigi_adif_udp.png?raw=true)

The F1-F12 function keys be sent to fldigi via XMLRPC. Fldigi will be placed into TX
mode, the message will be sent and a ^r will be tacked onto the end to place it back into
RX mode.

Unlike WSJT, fldigi needs to be setup for this to work. The XMLRPC interface needs to be
active. And in fldigi's config dialog go to CONTESTS -> General -> CONTEST and select
Generic Contest. Make sure the Text Capture Order field says CALL EXCHANGE.

## Sending CW

### Sending CW Macros

Other than sending CW by hand, you can also send predefined CW text messages by
pressing F1 - F12. See next section on Editing macro keys.

### Auto CQ

If you press `SHIFT-F1` The Auto CQ mode will be activated, you will be placed in a Run state
and the F1 macro will be resent after each Auto CQ Delay interval has passed.
An indicator will appear to the upper left of the F1 macro key as a visual reminder that your
Auto CQ is active. With it to the right, you will see a small progress bar giving you a visual
indication as to when F1 will fire next.

![Auto CQ Visual Indicator](https://github.com/mbridak/not1mm/raw/master/pic/auto_cq_indicator.png)

#### Setting the delay

The delay can be changed by going to the `Options` TAB in the Configuration dialog. If you are in
S&P mode when you enable Auto CQ, you will be automatically switched into RUN mode. To properly set
the delay you should time how long your F1 macro takes to key, then add how many seconds of pause
you would like. This is your delay value.

#### Cancelling the Auto CQ

The auto CQ can be cancelled by either typing in the call sign field, or by pressing ESC.

### Sending CW Free Form

If you need to send something freeform, you can press `CTRL-SHIFT-K`, this will
expose an entry field at the bottom of the window which you can type directly into.
When you're done you can either press CTRL-SHIFT-K again, or press the Enter Key to
close the field.

### Editing macro keys

To edit the macros, choose `File` > `Edit Macros`. This will open your systems
registered text editor with current macros loaded. When your done just save the
file and close the editor. The file loaded to edit, CW, SSB or RTTY, will be
determined by your current operating mode and contest. Each contest gets it's own
copy of the macros.

After editing and saving the macro file. You can force the logger to reload the
macro file by toggeling between `Run` and `S&P` states.

### Macro substitutions

You can include a limited set of substitution instructions.

|Macro|Substitution|
|---|---|
| {MYCALL} | Sends the station call. |
| {HISCALL} | Send what's in the callsign field. |
| {SNT} | Sends 5nn (cw) or 599 (ssb) |
| {SENTNR} | Sends whats in the SentNR field. |
| {EXCH} | Sends what's in the Sent Exchange field when contest is defined. |
| {PREVNR} | Sends the previous serial number. |
| {OTHER1} | Sends whats in the SentNR/Name field without altering it. |
| {OTHER2} | Sends whats in the Comment field without altering it. |
| {LOGIT} | Log the contact after macro pressed. |
| {MARK} | Mark the current call in the bandmap. |
| {SPOT} | Spot the current call to the cluster. |
| {RUN} | Change to Run mode. |
| {SANDP} | Change to S&P mode. |
| {WIPE} | Wipe input fields. |
| '#' | Sends serial number. |
| {VOICE1} - {VOICE10} | Uses rigctld to send voice macros stored in the radio. |

### Macro use with voice

#### {VOICE1} - {VOICE10}

If you use rigctld and your radio supports it you can use the macros {VOICE1},
{VOICE2} etc to send the voice messages stored in your radio.

#### Voice macro wave files

The macros when used with voice, will also accept filenames of WAV files to
play, excluding the file extension. The filename must be enclosed by brackets.
For example `[CQ]` will play `cq.wav`, `[again]` will play `again.wav`. The wav
files are stored in the operators personal data directory. The filenames must be
in lowercase. See [Various data file locations](#various-data-file-locations)
above for the location of your data files. For me, the macro `[cq]` will play
`/home/mbridak/.local/share/not1mm/K6GTE/cq.wav`

**The current wav files in place are not the ones you will want to use. They
sound like an idiot.** You can use something like Audacity to record new wav
files in your own voice.

Aside from the `[filename]` wav files, there are also NATO phonetic wav files
for each letter and number. So if your macro key holds
`{HISCALL} {SNT} {SENTNR}` and you have entered K5TUX in callsign field during
CQ WW SSB while in CQ Zone 3. You'll here Kilo 5 Tango Uniform X-ray, 5 9, 3.
Hopefully not in an idiots voice.

## cty.dat and QRZ lookups for distance and bearing

When a callsign is entered, a look up is first done in a cty.dat file to
determin the country of origin, geographic center, cq zone and ITU region.
Great circle calculations are done to determin the heading and distance from
your gridsquare to the geographic center. This information then displayed at the
bottom left.

![snapshot of heading and distance](https://github.com/mbridak/not1mm/raw/master/pic/heading_distance.png)

After this, a request is made to QRZ for the gridsquare of the callsign. If
there is a response the information is recalculated and displayed. You'll know
is this has happened, since the gridsquare will replace the word "Regional".

![snapshot of heading and distance](https://github.com/mbridak/not1mm/raw/master/pic/heading_distance_qrz.png)

## Other uses for the call field

**You must press the SPACE bar after entering any of the below.**

- [A Frequency] You can enter a frequency in kilohertz. This will change the band you're logging on. If you have CAT control, this will change the frequency of the radio as well.
- [CW, SSB, FM, AM, RTTY] You can set the mode logged. If you have CAT control this will also change the mode on the radio.
- [OPON] Change the operator currently logging.

**You must press the SPACE bar after entering any of the above.**

## The Windows

### The Main Window

![Main screen with callouts](https://github.com/mbridak/not1mm/raw/master/pic/mainwithcallouts.png)

#### Keyboard commands

| Key | Result |
| -------------- | --- |
| [Esc] | Stops sending CW. |
| [PgUp] | Increases the CW sending speed. |
| [PgDown] | Decreases the CW sending speed. |
| [Arrow-Up] | Jump to the next spot above the current VFO cursor in the bandmap window (CAT Required). |
| [Arrow-Down] | Jump to the next spot below the current VFO cursor in the bandmap window (CAT Required). |
| [TAB] | Move cursor to the right one field. |
| [Shift-Tab] | Move cursor left One field. |
| [SPACE] | When in the callsign field, will move the input to the first field needed for the exchange. |
| [Enter] | Submits the fields to the log. Unless ESM is enabled. |
| [F1-F12] | Send (CW/RTTY/Voice) macros. |
| [CTRL-R] | Toggle between Run and S&P modes. |
| [CTRL-S] | Spot Callsign to the cluster. |
| [CTRL-M] | Mark Callsign to the bandmap window to work later. |
| [CTRL-G] | Tune to a spot matching partial text in the callsign entry field (CAT Required). |
| [CTRL-SHIFT-K] | Open CW text input field. |
| [CTRL-=] | Log the contact without sending the ESM macros.|
| [CTRL-W] | Clears the input fields of any text. |
| [ALT-B] | Toggles the BandMap window. |
| [ALT-C] | Toggles the Check Partial window. |
| [ALT-L] | Toggles the QSO Log window. |
| [ALT-R] | Toggles the Rate window. |
| [ALT-S] | Toggles the Statistics window. |
| [ALT-V] | Toggles the VFO window. |

### The Log Window

`Window`>`Log Window`

The Log display gets updated automatically when a contact is entered. The top
half is a list of all contacts.

![Log Display Window](https://github.com/mbridak/not1mm/raw/master/pic/logdisplay.png)

The bottom half of the log displays contacts sorted by what's currently in the
call entry field. The columns displayed in the log window are dependant on what
contests is currently active.

#### Editing a contact

![Editing a cell](https://github.com/mbridak/not1mm/raw/master/pic/edit_cell.png)

You can double click a cell in the log window and edit its contents.

You can also Right-Click on a cell to bring up the edit dialog.

![right click edit dialog](https://github.com/mbridak/not1mm/raw/master/pic/edit_dialog.png)

You can not directly edit the multiplier status of a contact. Instead see the
next section on recalculating mults. If you change the callsign make sure the
`WPX` field is still valid.

### The Bandmap Window

`Window`>`Bandmap`

Put your callsign in the top and press the connect button.

The bandmap window is, as with everything, a work in progress. The bandmap now
follows the VFO.

![Bandmap Window](https://github.com/mbridak/not1mm/raw/master/pic/bandmap.png)

VFO indicator now displays as small triangle in the frequency tickmarks. A small
blue rectangle shows the receivers bandwidth if one is reported.

![Bandmap Window](https://github.com/mbridak/not1mm/raw/master/pic/VFO_and_bandwidth_markers.png)

Clicking on a spots tunes the radio to the spot frequency and sets the callsign field.

Previously worked calls are displayed in Red.

Callsigns that were marked with CTRL-M to work later are displayed in a Yellow-ish color.

In between the spots call and time is now a little icon to visually tell you what kind of spot it is.

![Bandmap Icons](https://github.com/mbridak/not1mm/raw/master/pic/bandmap_icons.png)

- ○ CW
- ⦿ FT*
- ⌾ RTTY
- 🗼 Beacons
- @ Everything else

Secondary Icons:

- [P] POTA
- [S] SOTA

### The Check Partial Window

`Window`>`Check Partial Window`

As you enter a callsign, the Check Window will show probable matches to calls
either in the MASTER.SCP file, your local log or the recent telnet spots. The
MASTER.SCP column will show results for strings of 3 or more matching characters
from the start of the call string. The local log and telnet columns will show
matches of any length appearing anywhere in the string.

Clicking on any of these items will change the callsign field.

![Check Window](https://github.com/mbridak/not1mm/raw/master/pic/checkwindow.png)

### The Rate Window

`Window`>`Rate Window`

This window contains QSO rates and counts.

![Rate Window](https://github.com/mbridak/not1mm/raw/master/pic/rate_window.png)

### The DXCC window

`Window`>`DXCC`

This window shows you a grid of DXCC entities you've aquired and on what bands.

![DXCC Window](https://github.com/mbridak/not1mm/raw/master/pic/dxcc_window.png)

### The Rotator Window (Work In Progress)

`Window`>`Rotator`

The Rotator window is a work in progress. The Rotator window relies on the functionality
of the rotctld daemon. It connects to rotctld on address 127.0.0.1 and port 4533. You can
change this if needed in the configuration dialog under the rotator tab. If started
and there is no connection, you will see this:

![Rotator Window](https://github.com/mbridak/not1mm/raw/master/pic/rot1.png)

Once there is a connection to rotctld, the current azimuth of the antenna is obtained and
you will see a direction needle apear:

![Rotator Window](https://github.com/mbridak/not1mm/raw/master/pic/rot2.png)

Once a call is entered and the bearing to contact is calculated you will see another needle
appear:

![Rotator Window](https://github.com/mbridak/not1mm/raw/master/pic/rot3.png)

At this time you can click on the 'Move' button to point your antenna at the contact. A list
of other buttons follows below.

Move: Rotates the antenna at the target.

Stop: Stops the current movement.

Park: Parks the antenna.

N,S,W,E: Points the antenna to one of the 4 cardinal directions.

You can also move the rotator by clicking in the globe where you want the
antenna to point.

### The Remote VFO Window

You can control the VFO on a remote rig by following the directions listed in
the link below. It's a small hardware project with a BOM of under $20, and
consisting of two parts. The VFO knob is now detectable on MacOS. I've made the
operation of the knob smoother by having the knob ignore frequency updates from
the radio while it's in rotation.

1. Making the [VFO](https://github.com/mbridak/not1mm/blob/master/usb_vfo_knob/vfo.md)...
2. Then... `Window`>`VFO`

![VFO](https://github.com/mbridak/not1mm/raw/master/pic/vfo.png)

## Cabrillo

Click on `File` > `Generate Cabrillo`

The file will be placed in your home directory. The name will be in the format of:

`StationCall`\_`ContestName`\_`CurrentDate`\_`CurrentTime`.log

So for me it would look like:

K6GTE_CANADA-DAY_2023-09-04_07-47-05.log

Look, a log [eh](https://www.youtube.com/watch?v=El41sHXck-E)?

[This](https://www.youtube.com/watch?v=oMI23JJUpGE) outlines some differences
between ARRL Field Day and Canada Day.

## ADIF

`File` > `Generate ADIF`

Boom... ADIF

`StationCall`\_`ContestName`\_`Date`\_`Time`.adi

## Recalulate Mults

After editing a contact and before generating a Cabrillo file. There is a Misc
menu option that will recalculate the multipliers incase an edit had caused a
change.

## ESM

ESM or Enter Sends Message. ESM is a feature in which the logging program will automatically
send the right function key macros based on the information present in the input fields and
which input field is active when you press the Enter key. You can see a common flow in the
examples below.

To test it out you can go to `FILE -> Configuration Settings`

![Config Screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_options.png)

Check the mark to Enable ESM and tell it which function keys do what. The keys will need
to have the same function in both Run and S&P modes. The function keys will highlight
green depending on the state of the input fields. The green keys will be sent if you
press the Enter key. You should use the Space bar to move to another field.

The contact will be automatically logged once all the needed info is collected and the
QRZ (for Run) or Exchange (for S&P) is sent.

### Run States

#### CQ

![CQ](https://github.com/mbridak/not1mm/raw/master/pic/esm_cq.png)

#### Call Entered send His Call and the Exchange

![Call Entered send His Call and the Exchange.](https://github.com/mbridak/not1mm/raw/master/pic/esm_withcall.png)

#### Empty exchange field send AGN till you get it

![Empty exchange field send AGN till you get it](https://github.com/mbridak/not1mm/raw/master/pic/esm_empty_exchange.png)

#### Exchange field filled, send TU QRZ and logs it

![Exchange field filled, send TU QRZ and logs it](https://github.com/mbridak/not1mm/raw/master/pic/esm_qrz.png)

### S&P States

#### With his call entered, Send your call

![With his call entered, Send your call](https://github.com/mbridak/not1mm/raw/master/pic/esm_sp_call.png)

#### If no exchange entered send AGN

![If no exchange entered send AGN](https://github.com/mbridak/not1mm/raw/master/pic/esm_sp_agn.png)

#### With exchange entered, send your exchange and log it

![With exchange entered, send your exchange and log it](https://github.com/mbridak/not1mm/raw/master/pic/esm_sp_logit.png)

## Call History Files

To use Call History files, go to `FILE -> Configuration Settings`

![Config Screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_options.png)

Place a check in the `Use Call History` box. Call history files are very specific to the contest you are working. Example files can be obtained from [n1mm's](https://n1mmwp.hamdocs.com/mmfiles/categories/callhistory/?) website. They have a searchbox so you can find the contest you are looking for. If you are feeling masocistic, you can craft your own. The general makeup of the file is a header defining the fields to be used, followed by by lines of comma separated data.

### Creating your own Call History files

You can use [adif2callhistory](https://github.com/mbridak/adif2callhistory) to generate your own call history file from your ADIF files. You can use a list of call history keys used for each contest [here](https://github.com/mbridak/not1mm/blob/master/call_history_keys.md).

An example file excerpt looks like:

```text
!!Order!!,Call,Name,State,UserText,
#
# 0-This is helping file, LOG what is sent.
# 1-Last Edit,2024-08-18
# 2-Send any corrections direct to ve2fk@arrl.net
# 3-Updated from the log of Marsh/KA5M
# 4-Thanks Bjorn SM7IUN for his help. 
# 5-Thanks
# NAQPCW 
# NAQPRTTY 
# NAQPSSB 
# SPRINTCW 
# SPRINTLADD 
# SPRINTNS 
# SPRINTRTTY 
# SPRINTSSB
AA0AC,DAVE,MN,Example UserText
AA0AI,STEVE,IA,
AA0AO,TOM,MN,
AA0AW,DOUG,MN,
AA0BA,,TN,
AA0BR,,CO,
AA0BW,,MO,
```

The first line is the field definition header. The lines starting with a `#` are comments. Some of the comments are other contests that this file also works with.
This is followed by the actual data. If the matched call has `UserText` information, that user text is populated to the bottom left of the logging window.

So if one were to go to `FILE -> LOAD CALL HISTORY FILE` and choose a downloaded call history file for NAQP and typed in the call AA0AC while operating in the NAQP, after pressing space, one would see:

![Call History Example](https://github.com/mbridak/not1mm/raw/master/pic/call_history_example.png)

Where the Name and State would auto-populate and the UserText info apprears in the bottom left.

## Contest specific notes

I found it might be beneficial to have a section devoted to wierd quirky things
about operating a specific contests.

### ARRL Sweekstakes

#### The exchange parser

This was a pain in the tukus. There are so many elements to the exchange, and
one input field aside from the callsign field. So I had to write sort of a
'parser'. The parser moves over your input string following some basic rules and
is re-evaluated with each keypress and the parsed result will be displayed in
the label over the field. The exchange looks like `124 A K6GTE 17 ORG`, a Serial
number, Precidence, Callsign, Year Licenced and Section. even though the
callsign is given as part of the exchange, the callsign does not have to be
entered and is pulled from the callsign field. If the exchange was entered as
`124 A 17 ORG` you would see:

![SS Parser Result](https://github.com/mbridak/not1mm/raw/master/pic/ss_parser_1.png)

You can enter the serial number and precidence, or the year and section as
pairs. For instance `124A 17ORG`. This would ensure the values get parsed
correctly.

You do not have to go back to correct typing. You can just tack the correct
items to the end of the field and the older values will get overwritten. So if
you entered `124A 17ORG Q`, the precidence will change from A to Q. If you need
to change the serial number you must append the precidence to it, `125A`.

If the callsign was entered wrong in the callsign field, you can put the correct
callsign some where in the exchange. As long as it shows up in the parsed label
above correctly your good.

The best thing you can do is play around with it to see how it behaves.

#### The exchange

In the `Sent Exchange` field of the New Contest dialog put in the Precidence,
Call, Check and Section. Example: `A K6GTE 17 ORG`.

For the Run Exchange macro I'd put `{HISCALL} {SENTNR} {EXCH}`.

### RAEM

In the New/Edit Contest dialog, in the exchange field put just your Lat and Lon.
for me 33N117W. And in the exchange macro put `# {EXCH}`.

### RandomGram

This plugin was submitted by @alduhoo. It reads a rg.txt file if it exists in the user's home directory to populate the next group in the sent exchange field.

### UKEI DX

For the Run exchange macro I'd put '{SNT} # {EXCH}'
