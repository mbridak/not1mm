# Not1MM

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Made With:PyQt5](https://img.shields.io/badge/Made%20with-PyQt5-red)](https://pypi.org/project/PyQt5/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/not1mm)](https://pypi.org/project/not1mm/)

![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

- [Not1MM](#not1mm)
  - [What and why is Not1MM](#what-and-why-is-not1mm)
  - [What it is not](#what-it-is-not)
  - [What it probably never will be](#what-it-probably-never-will-be)
  - [Changes of note](#changes-of-note)
  - [Running from source](#running-from-source)
  - [Hiding screen elements](#hiding-screen-elements)
  - [Editing function key macros](#editing-function-key-macros)
  - [cty.dat and QRZ lookups for distance and bearing](#ctydat-and-qrz-lookups-for-distance-and-bearing)
  - [Settings dialog](#settings-dialog)
  - [Other uses for the call field](#other-uses-for-the-call-field)
  - [Log Display](#log-display)
  - [Editing a contact](#editing-a-contact)
  - [Cabrillo](#cabrillo)
  - [Dupe checking](#dupe-checking)
  - [CAT](#cat)

## What and why is Not1MM

Not1MM's interface is a blantent ripoff of N1MM.
It is NOT N1MM and any problem you have with this software should in no way reflect on their software.

If you use Windows(tm) you should run their, or some other, program.

I personally don't. While it may be possible to get N1MM working under Wine, I haven't checked, I'd rather not have to jump thru the hoops.

**Currently this exists for my own personal amusement**.
Something to do in my free time.
While I'm not watching TV, Right vs Left political 'News' programs, mind numbing 'Reality' TV etc...

## What it is not

Working.

The current state is "**Not Working**". I literally just dragged some widgets out on a Qt Designer window, and wrote a couple stubs to display the interface. Next to nothing is working or useful.

## What it probably never will be

Feature complete.

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

## Changes of note

- [23-3-24] Added dupe checking. Added CAT check for flrig or rigctld. Added online flag for flrig.
- [23-3-23] Added most of Cabrillo generation. Plan to test it this weekends CQ WPX SSB.
- [23-3-22] Add prefill of serial nr. set OP call on startup. Set IsMultiplier1 new unique wpx. Add OP and contest name to window title. and stuff.
- [23-3-21] Worked on CQ WPX SSB plugin.
- [23-3-20] Added a contact edit dialog. RightClick to edit contact. Changed placeholder text color in settings dialog. Hooked up CW speedchange widget. PgUp/PgDn to change speed.
- [23-3-17] Added multicast UDP messages to update the log window when new contact made. You can now edit existing contacts in the log window. You can't delete them yet. Got rid of watchdog. Isolated common multicast code to it's own class.
- [23-3-15] Added a rudimentary log view window.
- [23-3-10] Started work on saving contacts to the DB. Added a claculate_wpx_prefix routine.
- [23-3-9] Placed network call lookup in a thread. Display freq/mode for non CAT radios. Hooked up the CW macros to cwdaemon.
- [23-3-8] Band/Frequency/Mode indicators. Direct frequency/mode entry in call field.
- [23-3-7] Changed dxlog table column names.
- [23-3-1] Add shift tab for field movement.
- [23-2-23] Dialogs now do darkmode, Add settings dialog. App remembers window size and location.
- [23-2-22] Added cty.dat file.
- [23-2-21] Added edit macro dialog.
- [23-2-20] Save view states. fixed debug messages. Started coding plugins/stubs.
- [23-2-15] Added qss stylesheet. Connected Run and S&P radio buttons. Reads in cwmacros.
- [23-2-12] Added View menu to show/hide macro buttons, command buttons, and the band/mode indicator on the left. Added OpOn dialog. Added a dark mode. QRZ lookup added but needs work.
- [23-2-9] Initial post and name squatting.

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

## Hiding screen elements

You can show or hide certain buttons/indicators by checking and unchecking their boxes under the view menu. You can then resize the screen to make it more compact.

![View Menu](https://github.com/mbridak/not1mm/raw/master/pic/view_menu.png)

The your choices will be remembered when you relaunch the program.

## Editing function key macros

You can edit the CW macros by right clicking on the buttons and filling out the dialog.
![Edit Macro](https://github.com/mbridak/not1mm/raw/master/pic/edit_macro.png)

## cty.dat and QRZ lookups for distance and bearing

When a callsign is entered, a look up is first done in a cty.dat file to determin the country of origin, geographic center, cq zone and ITU region. Great circle calculations are done to determin the heading and distance from your gridsquare to the grographic center. This information then displayed at the bottom left.

![snapshot of heading and distance](https://github.com/mbridak/not1mm/raw/master/pic/heading_distance.png)

After this, a request is made to QRZ for the gridsquare of the callsign. If there is a response the information is recalculated and displayed. You'll know is this has happened, since the gridsquare will replace the word "Regional".

![snapshot of heading and distance](https://github.com/mbridak/not1mm/raw/master/pic/heading_distance_qrz.png)

## Settings dialog

Added a settings screen.

![settings screen](https://github.com/mbridak/not1mm/raw/master/pic/settings.png)

You can fill it out if you want to. You can leave our friends behind. 'Cause your friends don't fill, and if they don't fill. Well, they're no friends of yours.

You can fill. You can fill. Everyone look at your keys.

**I forgot my hat today**.

## Other uses for the call field

- [Freqnency] You can enter a frequency in kilohertz. This will change the band you're logging on. If you have CAT control, this will change the frequency of the radio as well.
- [CW, SSB, RTTY] You can set the mode logged. If you have CAT control this will also change the mode on the radio.
- [OPON] Change the operator currently logging.

**You must press the SPACE bar after entering any of the above.**

## Log Display

The Log display gets updated automatically when a contact is entered. The top half is a list of all contacts.

![Log Display Window](https://github.com/mbridak/not1mm/raw/master/pic/logdisplay.png)

The bottom half of the log displays contacts sorted by what's currently in the call entry field.

## Editing a contact

![Log Display Window](https://github.com/mbridak/not1mm/raw/master/pic/edit_cell.png)

You can double click a cell in the log window and edit its contents.

You can also Right-Click on a cell to bring up the edit dialog.

![Log Display Window](https://github.com/mbridak/not1mm/raw/master/pic/edit_dialog.png)

## Cabrillo

Kinda working in a forced way. Need to generalize it for multiple contests. Click on `File` then `Generate Cabrillo`

There's a few more fields I have to code in. But it's enough for me to edit and submit.

The file will be placed in your home directory. The name will be in the format of:

`StationCall`_`ContestName`.log

So for me it would be:

K6GTE_CQ-WPX-SSB.log

## Dupe checking

Added dupe checking. Big Red 'Dupe' will appear if it's a dupe...

## CAT

Added rudimentary check for running instance of flrig or rigctld. It will connect to whichever it finds first.
