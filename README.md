<!-- markdownlint-disable MD001 MD033 MD041 -->
<center>

# Not1MM

 ![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

</center>

 The worlds #1 unfinished contest logger <sup>*According to my daughter Corinna.<sup>

[![PyPI](https://img.shields.io/pypi/v/not1mm)](https://pypi.org/project/not1mm/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Made With:PyQt6](https://img.shields.io/badge/Made%20with-PyQt6-blue)](https://pypi.org/project/PyQt6/)
[![Code Maturity:Snot Nosed](https://img.shields.io/badge/Code%20Maturity-Snot%20Nosed-red)](https://xkcd.com/1695/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/not1mm?period=monthly&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=GREEN&left_text=Monthly%20Downloads)](https://pepy.tech/projects/not1mm)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/not1mm?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=GREEN&left_text=Total%20Downloads)](https://pepy.tech/projects/not1mm)

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

### The Elephant in the Room

Not1MM's interface is a blatant ripoff of N1MM. It is NOT N1MM and any problem
you have with this software should in no way reflect on their software.

### Not1MM is NOT ment for interoperability with N1MM+

I wake up, take my first sip of coffee and am greeted by a lovely heartfelt [message](TomsAMassiveTwat.md) from Tom Wagner.
So I feel something may need to be clarified. Not1MM is... NOT N1MM neither is it N1MM+ or even N1MMPlus.
They're not ment to work with each other. It does send N1MM packets, but that's for nodered scoreboards, not Tom's beloved program.

You shouldn't bother Tom or his Team. They be cranky...

### The What

Not1MM is, in my opinion, a usable amateur radio, or HAM, contest logger. It's
written in Python 3.10+, and uses Qt6 framework for the graphical interface
and SQLite for the database.

### Target Environment

The primary target for this application is Linux. It may be able to run on other
platforms, BSD and Windows. But I don't have a way, or desire, to directly support them.

I've recently purchased an M4 Mac Mini, So I can confirm it works well on the MacOS platform.

### The Why

**Currently this exists for my own personal amusement**. I've recently retired
after 35+ years working for 'The Phone Company', GTE -> Verizon -> Frontier.
And being a Gentleman of Leisure, needed something to do in my free time.
I'm a casual contester and could not find any contesting software for Linux that
I wanted to use. There is [Tucnak](http://tucnak.nagano.cz/) which is very robust
and mature. It just wasn't for me.

## Code Maturity & Current Multi Multi Development Focus

Not1MM is, at times, fairly stable. Recently, it would seem that I'm desperately trying to change that. The current focus of development is adding support for [Multi Multi](Multi-Multi.md) contest operations. It is something that I have no practical experience in. So you can expect the same quality of code fit and finish.

## Our Code Contributors ✨

I wish to thank those who've contributed to the project. Below is an automatically
generated, 'cause I'm lazy, list of those who've submitted PR's.

<a href="https://github.com/mbridak/not1mm/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=mbridak/not1mm" alt="Avatar icons for code contributors." />
</a>

## Recent Changes

- [2026-06-21] @mbridak Fix: Ignore errors when reading utf8 history files and exclude commented line...
- [2026-06-20] Refactor: Clean up code and improve readability in darc_vhf.py
- [2026-06-17] @mbridak Add app icon for macos.
  - Add JetBrains Mono font to various UI elements in main.ui
  - Update version to 26.6.17 and fix changelog entries for recent changes
  - Fix XML syntax by closing <family> tags in configuration.ui
- [2026-06-16] Add script to automate version updates in pyproject.toml and version.py
  - Remove outdated version update script
  - Update version to 26.6.16.1 in version.py and pyproject.toml; add script to automate version updates
  - @mbridak Add {PREVCALL} macro.
  - @mbridak fix is_it_dark function to return a bool value instead of None.
  - @mbridak Add font weight property to UI files for consistency
  - @mbridak Get rid of the font warning.
  - Update version to 26.6.16, fix SQL queries in StatsWindow, and add changelog entry
  - @mbridak Fix SQL queries in StatsWindow to include more CW modes.
- [2026-06-14] Update version to 26.6.14.1, add changelog entry for PR #591, and reflect changes in README
  - Merge pull request #591 from df7cb/trayicon
  - Set tray icon earlier
  - @mbridak Changes the app name on MacOS from Python to Not1MM.
  - @mbridak Add a MacOS specific dependancy.
  - Update version to 26.6.14 and fix dependency name in changelog and README
  - Fix dependency name for adif-io in pyproject.toml
- [2026-06-13] @mbridak Update EXCHANGE_HINT for clarity in EUDX plugin
- [2026-06-11] Add EUDX contest entry to Not1MM user manual
  - Update version to 26.6.11 and add EUDX contest entry to changelog and README
  - Remove greeting from SOAPBOX_HINT in EUDX plugin
  - @mbridak Add EUDX
  - Add additional assertions for module imports in CQ WW CW plugin
- [2026-06-09] Update version to 26.6.9.1 and add changelog entry for sound device check
  - Handle multiple exceptions in voice keying stream
  - Update version to 26.6.9 and document recent changes in changelog and README
  - @mbridak prevent {} macros from cycling PTT in CW mode.
  - update scp and cty
  - Remove D-Bus notification helper implementation from notification.py
- [2026-06-08] Lets try that again
  - Bump version to 26.6.8.1 in version.py and pyproject.toml
  - Merge branch 'master' of https://github.com/mbridak/not1mm
  - @mbridak Remove dbus-python libglib2.0-dev and libdbus-1-dev from installation require...
  - Merge pull request #589 from d3m3vilurr/bypass-dbus-on-windows
  - Update installation requirements in INSTALL.md and README.md to include libglib2.0-dev...
- [2026-06-09] Bypass installing dbus-python on non linux platform
- [2026-06-08] Bump version to 26.6.8 in version.py and pyproject.toml
  - Remove version constraint for dbus-python dependency
- [2026-06-07] @mbridak Bump version to 26.6.7.1 and update changelog and README for recent changes
  - Merge pull request #585 from df7cb/cluster-rate
  - Merge pull request #586 from df7cb/rig-timeout
  - Allow more time for rig connection
  - @mbridak Bump version to 26.6.7 and update changelog and README for ADIF generation fix
  - Process all pending spots every cycle
  - Merge pull request #584 from mbridak/583-stroke-character-in-call-prevents-saving-adif
  - @mbridak Fix ADIF filename generation to replace '/' with '-' in callsign and remove u...
- [2026-06-05] Merge pull request #582 from microphonon/manual_edits
  - Attempt to fic not1mm.pdf merge conflict
  - Bump version to 26.6.5.1 in version.py and pyproject.toml
  - Merge pull request #581 from mbridak/580-adif-import-bug
  - Update changelog and README to document fixes for ADIF import bugs
  - Fix ADIF import frequency handling and improve logging for missing frequencies
  - Add temp.txt to .gitignore to exclude temporary testing files
  - @mbridak Fix typo in method name for showing message box during ADIF import
  - Update version to 26.6.5 and document recent changes in changelog and README
  - Merge pull request #579 from mbridak/new_notifications
  - Enhance error handling with message boxes and improve voice keying functionality
- [2026-06-03] edits to the user manual
- [2026-06-02] Add D-Bus notification support for Linux and clean up code
- [2026-06-01] Update changelog and README to document recent changes
  - Bump version to 26.6.1 in version.py and pyproject.toml
  - Remove debug print statement from process_esm function

See [CHANGELOG.md](CHANGELOG.md) for prior changes.

## Installation

### TL;DR

#### Prerequisites

Not1MM requires:

- PyQt6
- libportaudio2
- libxcb-cursor0 (maybe... Depends on the distro)

#### One liner install
  
```bash
curl -LsSf uvx.sh/not1mm/install.sh | sh
```

For more in depth info, please see the [installation](INSTALL.md) section.

## Documentation

I've nuked 90% of the README.md and moved it to a LaTeX file. So now you can get the [user manual](https://github.com/mbridak/not1mm/raw/master/not1mm.pdf) as a PDF file. I know some WILL NOT LIKE THIS. Sorry, not sorry.

## Features

A quick feature list, See the user manual for more details.

- 45+ [supported contests](Working_Contests.md)
- Lookup, QRZ and HamQTH
- CAT Control, rigctld and flrig
- CW Keyer Interface, winkeyer and cwdaemon
- Cluster and Bandmap
- Rotator control, rotctld
- [Multi Multi](Multi-Multi.md) (The super sketchy not ready for prime time)
- N1MM Packet output for nodered
- WSJT-X FT8/FT4/ETC and FLDIGI RTTY
- ADIF and Cabrillo output.
- And *Other Stuff*

## Known Issues

- Hamlib before 4.6.3 had a problem with sending CW and changing/reading the keying speed.
- wfview before version 2.2 has issues with frequency reporting and CW sending.
