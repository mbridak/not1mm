<center>

# Not1MM
<!-- markdownlint-disable MD001 MD033 -->


 ![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

</center>

 The worlds #1 unfinished contest logger <sup>*According to my daughter Corinna.<sup>

[![PyPI](https://img.shields.io/pypi/v/not1mm)](https://pypi.org/project/not1mm/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Made With:PyQt6](https://img.shields.io/badge/Made%20with-PyQt6-blue)](https://pypi.org/project/PyQt6/)
[![Code Maturity:Snot Nosed](https://img.shields.io/badge/Code%20Maturity-Snot%20Nosed-red)](https://xkcd.com/1695/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/not1mm)](https://pypi.org/project/not1mm/)

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

### The Elephant in the Room

Not1MM's interface is a blatant ripoff of N1MM. It is NOT N1MM and any problem
you have with this software should in no way reflect on their software.

### The What

Not1MM is, in my opinion, a usable amateur radio, or HAM, contest logger. It's
written in Python 3.10+, and uses Qt6 framework for the graphical interface
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

## Code Maturity & Current Multi Multi Development Focus

Not1MM is, at times, fairly stable. Recently, it would seem that I'm desperately trying to change that. The current focus of development is adding support for Multi Multi contest operations. It is something that I have no practical experience in. So you can expect the same quality of code fit and finish.

## Our Code Contributors ✨

I wish to thank those who've contributed to the project. Below is an automatically
generated, 'cause I'm lazy, list of those who've submitted PR's.

<a href="https://github.com/mbridak/not1mm/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=mbridak/not1mm" alt="Avatar icons for code contributors." />
</a>

## Recent Changes

- [25-10-6] Bugfix: Fix 70cm frequency ranges not showing in bandmap.
  - Bugfix: Fix broken dupe checking when not multi-multi.
  - Bugfix: Fix sending SN when not fetched.
- [25-10-5] Add Multi Multi dupe checking.
  - Add Multi Multi Serial Number support.

See [CHANGELOG.md](CHANGELOG.md) for prior changes.

## Installation

To install not1mm please see the [installation](INSTALL.md) section.

## Documentation

I've nuked 90% of the README.md and moved it to a LaTeX file. So now you can get the [user manual](https://github.com/mbridak/not1mm/raw/master/not1mm.pdf) as a PDF file. I know some WILL NOT LIKE THIS. Sorry, not sorry.

## Features

A quick feature list, See the user manual for more details.

- Lookup, QRZ and HamQTH
- CAT Control, rigctld and flrig
- CW Keyer Interface, winkeyer and cwdaemon
- Cluster and Bandmap
- Rotator control, rotctld
- Multi Multi (The super sketchy not ready for prime time)
- N1MM Packet output for nodered
- WSJT-X FT8/FT4/ETC and FLDIGI RTTY
- ADIF and Cabrillo output.
- And *Other Stuff*
