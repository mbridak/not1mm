# Not1MM

![logo](https://github.com/mbridak/not1mm/raw/master/not1mm/data/k6gte.not1mm.svg)

- [Not1MM](#not1mm)
  - [What and why is Not1MM](#what-and-why-is-not1mm)
  - [What it is not](#what-it-is-not)
  - [Changes of note](#changes-of-note)
  - [Running from source](#running-from-source)

## What and why is Not1MM

Not1MM's interface is a blantent ripoff of N1MM.
It is NOT N1MM and any problem you have with this software should in no way reflect on their software.

If you use Windows(tm) you should run their, or some other, program.

I personally don't. While it may be possible to get N1MM working under Wine, I haven't checked, I'd rather not have to jump thru the hoops.

Currently this exists for my own personal amusement.
Something to do in my free time.
While I'm not watching TV, Right vs Left political 'News' programs, mind numbing 'Reality' TV etc...

## What it is not

Working.

The current state is "Not Working". I literally just dragged some widgets out on a Qt Designer window, and wrote a couple stubs to display the interface. Next to nothing is working or useful.

![main screen](https://github.com/mbridak/not1mm/raw/master/pic/main.png)

## Changes of note

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
