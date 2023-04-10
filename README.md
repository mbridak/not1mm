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
  - [Various data file locations](#various-data-file-locations)
    - [Data](#data)
    - [Config](#config)
  - [Adding a database](#adding-a-database)
  - [Station Settings dialog](#station-settings-dialog)
  - [Adding a contest](#adding-a-contest)
  - [Selecting an added contest as the current contest](#selecting-an-added-contest-as-the-current-contest)
  - [Configuration Settings](#configuration-settings)
  - [Hiding screen elements](#hiding-screen-elements)
  - [Editing current sessions function key macros](#editing-current-sessions-function-key-macros)
  - [Editing macro keys (Persistent)](#editing-macro-keys-persistent)
  - [cty.dat and QRZ lookups for distance and bearing](#ctydat-and-qrz-lookups-for-distance-and-bearing)
  - [Other uses for the call field](#other-uses-for-the-call-field)
  - [Log Display](#log-display)
  - [Editing a contact](#editing-a-contact)
  - [Recalulate Mults](#recalulate-mults)
  - [Cabrillo](#cabrillo)
  - [ADIF](#adif)
  - [Dupe checking](#dupe-checking)
  - [CAT](#cat)
  - [CW Keyer interface](#cw-keyer-interface)

## What and why is Not1MM

Not1MM's interface is a blantent ripoff of N1MM.
It is NOT N1MM and any problem you have with this software should in no way reflect on their software.

If you use Windows(tm) you should run away from this and use someother program.

I personally don't. While it may be possible to get N1MM working under Wine, I haven't checked, I'd rather not have to jump thru the hoops.

**Currently this exists for my own personal amusement**.
Something to do in my free time.
While I'm not watching TV, Right vs Left political 'News' programs, mind numbing 'Reality' TV etc...

## What it is not

Fully working.

The current state is "**ALPHA**". I've used it for CQ WPX SSB and JIDX CW, and was able to work contacts and submit a cabrillo at the end. I'll add contests as/if I work them.

## What it probably never will be

Feature complete. I'm only one guy, and I'm not what you'd consider to be a contester. So new contests will be sparse.

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

## Changes of note

- [23-4-10] Added Configure Settings dialog. Added CW keyer and CAT control settings to Configure Settings dialog.
- [23-4-6] Added JIDX contest. Added {SNT} and {SENTNR} CW macros. Added a menu item to open then CW macros data file in your systems preferred text editor.
- [23-4-5] Fixed crash caused by lists not being lists. Filled out some existing code stubs in the Field Day plugin. Fixed log window not showing current contest Q's.  
- [23-4-4] Current OP defaults to Station call if OPON not used. Text formatting of Station settings. Removed STX and SRX strings from General Logging ADIF. DB now operates on current contest Nr. Hide/Show band-mode frames.
- [23-4-3] Added dialog to select from defined contests in the active database. Force Station settings then new contest dialog on new DB creation. Add Greneral Logging contest type. Added other Cabrillo tags.

<details>

<summary>March 2023</summary>

- [23-3-31] Now saving station settings in the contest database.
- [23-3-30] Added Open new and Open existing database
- [23-3-29] Added a new contest dialog.
- [23-3-27] Add menu item to recalculate mults.
- [23-3-27] Fix cursor behaviour when editing text in callsign field.
- [23-3-25] Fix minimum call length. Fix cabrillo tag. Add adif output.
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

</details>

<details>

<summary>February 2023</summary>

- [23-2-23] Dialogs now do darkmode, Add settings dialog. App remembers window size and location.
- [23-2-22] Added cty.dat file.
- [23-2-21] Added edit macro dialog.
- [23-2-20] Save view states. fixed debug messages. Started coding plugins/stubs.
- [23-2-15] Added qss stylesheet. Connected Run and S&P radio buttons. Reads in cwmacros.
- [23-2-12] Added View menu to show/hide macro buttons, command buttons, and the band/mode indicator on the left. Added OpOn dialog. Added a dark mode. QRZ lookup added but needs work.
- [23-2-9] Initial post and name squatting.

</details>

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

If your system has an `XDG_DATA_HOME` environment variable set, the databases can be found there. Otherwise they will be found at `yourhome/.local/share/not1mm`

### Config

Configuration file(s) can be found at the location defined by `XDG_CONFIG_HOME`. Otherwise they will be found at `yourhome/.config/not1mm`

## Adding a database

On the initial running, a database is created for you called `ham.db`. This and all future databases are located in the data directory mentioned above. You can create new databases by selecting `File` > `New Database` from the main window. You can select previously created databases by selecting `File` > `Open Database`.

## Station Settings dialog

After initial run of the program or creating a new contact database you will need to fo to `File` > `Station Settings` and fill out the information in the dialog.

![settings screen](https://github.com/mbridak/not1mm/raw/master/pic/settings.png)

You can fill it out if you want to. You can leave our friends behind. 'Cause your friends don't fill, and if they don't fill. Well, they're no friends of mine.

You can fill. You can fill. Everyone look at your keys.

**I forgot my hat today**.

## Adding a contest

Select `File` > `New Contest`

![New Contest Dialog](https://github.com/mbridak/not1mm/raw/master/pic/new_contest.png)

## Selecting an added contest as the current contest

Select `File` > `Open Contest`

![Open an existing contest](https://github.com/mbridak/not1mm/raw/master/pic/select_contest.png)

## Configuration Settings

Select `File` > `Configuration Settings`

![Configuration Settings screen](https://github.com/mbridak/not1mm/raw/master/pic/configuration_settings.png)

## Hiding screen elements

You can show or hide certain buttons/indicators by checking and unchecking their boxes under the view menu. You can then resize the screen to make it more compact.

![View Menu](https://github.com/mbridak/not1mm/raw/master/pic/view_menu.png)

The your choices will be remembered when you relaunch the program.

## Editing current sessions function key macros

You can edit the CW macros for the current session by right clicking on the buttons and filling out the dialog.

![Edit Macro](https://github.com/mbridak/not1mm/raw/master/pic/edit_macro.png)

You can include a limited set of substitution instructions.

- {MYCALL} Sends the station call.
- {HISCALL} Send what's in the callsign field.
- {SNT} Sends 5nn
- {SENTNR} Sends whats in the SentNR field.

## Editing macro keys (Persistent)

To edit the macros in a more persistent way. Choose `File` > `Edit CW Macros`. This will open your systems registered text editor with current macros loaded. When your done just save the file and close the editor. The logger will then reload the macros. This will persist across until you change them again.

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

## Log Display

The Log display gets updated automatically when a contact is entered. The top half is a list of all contacts.

![Log Display Window](https://github.com/mbridak/not1mm/raw/master/pic/logdisplay.png)

The bottom half of the log displays contacts sorted by what's currently in the call entry field.

## Editing a contact

![Editing a cell](https://github.com/mbridak/not1mm/raw/master/pic/edit_cell.png)

You can double click a cell in the log window and edit its contents.

You can also Right-Click on a cell to bring up the edit dialog.

![right click edit dialog](https://github.com/mbridak/not1mm/raw/master/pic/edit_dialog.png)

You can not directly edit the multiplier status of a contact. Instead see the next section on recalculating mults. If you change the callsign make sure the `WPX` field is still valid.

## Recalulate Mults

After editing a contact and before generating a Cabrillo file. There is a Misc menu option that will recalculate the multipliers incase an edit had caused a change.

## Cabrillo

Kinda working in a forced way. Need to generalize it for multiple contests. Click on `File` > `Generate Cabrillo`

There's a few more fields I have to code in. But it's enough for me to edit and submit.

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

## CAT

Go to `File` > `Configuration Settings`, You will find a `CAT` tab to accept your configutaion.

## CW Keyer interface

Go to `File` > `Configuration Settings`, You will find a `CW` tab to accept your configutaion.
