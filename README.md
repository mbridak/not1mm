<!-- markdownlint-disable MD001 MD033 MD041 -->
<center>

# Not1MM

 ![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

</center>

 The worlds #1 unfinished contest logger <sup>*According to my daughter Corinna.<sup>

[![PyPI](https://img.shields.io/pypi/v/not1mm)](https://pypi.org/project/not1mm/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
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
written in Python 3.11+, and uses Qt6 framework for the graphical interface
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

- [2026-08-19] Merge pull request #665 from mbridak/fix-adif-import
  - @mbridak Handle both OperationalError and IntegrityError in exec_sql_commit method
  - Merge pull request #664 from mbridak/add-wpx-to-stats
  - @mbridak Add WPX statistics to the stats window
  - Merge pull request #663 from mbridak/improve-voice-keying
  - @mbridak Refactor voice keying logic to improve handling.
- [2026-08-18] @mbridak Update UI elements in bandmap and cluster windows to use icons instead of tex...
  - @mbridak Add Catppuccin Latte theme for light mode.
  - @mbridak Add Catppuccin Mocha theme to fix dark mode handling on Gnome.
- [2026-08-17] Merge pull request #661 from mbridak/660-font-cluster
  - @mbridak Add cluster window font resize buttons.
  - @mbridak Fix: main window title.
- [2026-08-16] @mbridak Fix:  The tray icon and other stuff sometimes persisted after quit.
- [2026-08-15] @mbridak Fix: clusterwindow always opened at program lanch.
- [2026-08-14] Merge pull request #658 from mbridak/language-translations
  - @mbridak Refactor plugin interfaces to use Qt translation for labels
  - @mbridak Add initial translations.
  - @mbridak Add internationalization support and language preferences
- [2026-08-13] Merge pull request #656 from mbridak/add-rdxc-contest
  - @mbridak Add RDXC contest.
- [2026-08-12] @mbridak Update installation instructions for Flatpak support
- [2026-08-11] Merge pull request #654 from mbridak/add-trans-tasman
  - @mbridak Add Trans Tasman contest support and update UI
  - @mbridak Update EXCHANGE_HINT to use "#" for John Moyle Field Day and Oceania DX plugins
- [2026-08-10] Merge pull request #653 from mbridak/john-moyle-field-day
  - @mbridak Add JOHN MOYLE FIELD DAY plugin
- [2026-08-09] Merge pull request #650 from IonixV/master
  - Merge pull request #652 from mbridak/add-oceania-dx
  - @mbridak Add Oceania DX CW and SSB plugins.
  - Merge branch 'master' into master
- [2026-08-08] Merge pull request #651 from mbridak/649-not1mm-2687-crashes-after-sending-qso-to-renfield
  - @mbridak Fix: Update datetime parsing to handle timezone information in server command expiration
- [2026-08-07] @mbridak Add imp_adif import to multiple plugins.
  - Merge pull request #647 from Koji-Kawano/all_asia
  - All Asia DX contest 1st commit
- [2026-08-06] Merge branch 'master' of https://github.com/mbridak/not1mm
  - Update version to 26.8.6 and refresh changelog with recent changes
  - Merge pull request #645 from df7cb/band
- [2026-08-05] Consolidate band/frequency conversion into a single source-of-truth table
- [2026-08-04] Remove some dead variables
- [2026-08-05] Merge pull request #644 from df7cb/spotdx
  - Move SPOTDX to clusterwindow.py
- [2026-08-04] @mbridak add 3hr band/mode dupe check to rd contest.
- [2026-08-03] @mbridak RD-Contest Update cabrillo function: enhance mode handling and format output ...
  - Merge pull request #641 from mbridak/rd-contest
  - @mbridak Update WIA Remembrance plugin: enhance scoring logic and clarify exchange instructions
  - Merge pull request #640 from df7cb/clusterwindow
- [2026-07-28] Create a Cluster window
- [2026-08-02] @mbridak Maybe Fix: update TCI sendcw method to use cw_macros command for CW transmission
  - @mbridak Fix: maybe Add: send cw_macros_stop command in stopcw method
  - @mbridak Fix: self assigned variable in rsgb-iota
  - Merge pull request #639 from df7cb/euhfc
  - Fix more Cabrillo names and enable online scores
  - Online scoring for EUHFC
- [2026-08-01] Merge pull request #638 from sblanchard/add-tci-support
  - docs: record cw_msg signature confirmed working on live AetherSDR
  - docs: note TCI rig control support in changelog
  - Wire TCI into vfo.py, fix online staleness, add missing send_cat_string stub
  - test: add fake TCI server for integration testing
  - Correct stale RTTY mode expectation in plan Task 4 test
  - feat: wire TCI backend into radio dispatch, settings, and UI
  - feat: add TciCAT backend implementing the CAT contract over TCI
  - fix: release socket/timer on their own thread after close(), fix backoff double-increm...
  - feat: add TCI websocket client with state cache
  - feat: add TCI protocol parsing and mode translation
  - docs: fix TCI handshake doc overclaim, wrong comment, and stat rounding
  - Add TCI probe and record live AetherSDR handshake
  - Ignore .superpowers scratch directory
  - Correct TCI port to 50001 to match the AetherSDR under test
  - Add implementation plan for TCI CAT backend (phase 1)
  - Add design spec for TCI support (AetherSDR compatibility)

See [CHANGELOG.md](CHANGELOG.md) for prior changes.

## Installation

### Via Flatpak

I'm pretty sure the flatpak works now. Let me know if it doesn't.

Grab the [flatpak file](https://github.com/mbridak/not1mm/raw/refs/heads/master/not1mm.flatpak).

#### Install

```bash
flatpak install --user not1mm.flatpak
```
#### Run it

```bash
flatpak run io.github.mbridak.not1mm 
```

Or find it in your launcher.

### Via uv installer

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

- 60+ [supported contests](Working_Contests.md)
- Lookup, QRZ and HamQTH
- CAT Control, rigctld, flrig, TCI
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
