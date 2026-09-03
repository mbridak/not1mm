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

- [2026-09-03] @mbridak Add gen_edi function to plugin_common. removed the 3 different edi functions ...
  - @mbridak fix: timestamp in EDI export in ta_vhf_uhf_contest
  - Merge branch 'master' of https://github.com/mbridak/not1mm
  - @mbridak fix: reduce timeout for HamQTH API requests to 1s, willy tested willy approved.
- [2026-09-02] Merge pull request #677 from sblanchard/master
  - fix: MST ft8_handler no longer logs a lone received serial as the name
  - fix: CWO ft8_handler reads SRX_STRING and never leaks the previous exchange
  - Merge upstream mbridak/master (PR #4): callbook timeout 2s, v26.9.2
  - Merge pull request #3 from sblanchard/ft8-handler-cw-sprints
  - @mbridak Reduce callbook lookup timeout from 10 seconds to 2.
  - Add ft8_handler to CWT, SST, MST and CW Open plugins
- [2026-09-01] Add script to automate flatpak update process
- [2026-08-31] Fix handling of SentNr and NR in EDI output; enhance bandinMHz mapping tests
  - @mbridak Add NAC VHF contest

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
