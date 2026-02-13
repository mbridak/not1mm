# Installation

This section will hopefully get you started with installing Not1MM.

## Prerequisites

Not1MM requires:

- Python 3.10+
- PyQt6
- libportaudio2
- libxcb-cursor0 (maybe... Depends on the distro)

You should install these through your distribution's package manager before continuing.

## The Easy and Fast way to always run the latest version

- Step 1. Visit [Astral](https://docs.astral.sh/uv/) and install uv.

In short you run this in your terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- Step 2. Tell it to run not1mm:

```bash
uvx not1mm
```

or

```bash
uvx not1mm@latest
```

That's it... It will go out, fetch the latest version of not1mm, setup a python virtual environment, get all the needed python libraries, cache everything and run not1mm. The first time takes a minute, but each time after, it's lightning quick and it will automatically check for updates and run the latest version.

But wait... There's more. If your distro is old and you're stuck with an older version of python... Say 3.10. And you want to see what all the cool kids are using. But you don't want to corrupt your broke ol' system by downloading the newest Python version. No problem. You can tell uv to run not1mm with any version of Python you'd like. Let's say 3.14.

```bash
uvx --python 3.14 not1mm
```

It'll download Python 3.14 into you virtual environment and run not1mm.

Let's say I was an idiot and pushed a new version and did't fully test it. This happens a-lot... We test in production. Or lets say you just want to see the pain that was back in 2023. No problem.

```bash
uvx --python 3.10 not1mm==23.5.19
```

Pow! Enjoy the pain... If uv is not your cuppa, you can follow the more traditional route below.

## Common Installation Recipes for Ubuntu and Fedora with pip and pipx

I've taken the time to install some common Linux distributions into a VM and
noted the minimum steps needed to install Not1MM.

### Ubuntu 22.04 LTS, 23.04, 24.04 LTS and 25.04

#### Ubuntu 22.04 LTS

```bash
sudo apt install -y python3-pip python3-numpy libxcb-cursor0 libportaudio2
python3 -m pip install -U pip
# Logout and back in
pip3 install PyQt6
pip3 install not1mm
```

#### Ubuntu 23.04

```bash
sudo apt install -y libportaudio2 pipx libxcb-cursor0
pipx install not1mm
pipx ensurepath
```

#### Ubuntu 24.04 LTS and 25.04

```bash
sudo apt install -y pipx libportaudio2 libxcb-cursor0
pipx install not1mm
pipx ensurepath
```

You may need once to log out and in again to make the new PATH settings to work. Depending on the shell used you may type in

```bash
source ~/.bashrc
not1mm
```

### Fedora 38, 39 and 40

#### Fedora 38 & 39

```bash
sudo dnf upgrade --refresh
sudo dnf install python3-pip pipx portaudio
pipx install not1mm
pipx ensurepath
```

#### Fedora 40

```bash
sudo dnf upgrade --refresh
sudo dnf install python3-pip pipx python3-pyqt6 portaudio
pipx install not1mm
pipx ensurepath
```

### Others

#### Manjaro

```bash
pamac build not1mm-git 
```

#### Mint 22

```bash
sudo apt install python3-pip pipx libxcb-cursor0 
pipx install not1mm
pipx ensurepath
```

## Python, PyPI, pip and pipx if you want to know more

This software is a Python package hosted on PyPI, and installable with the pip
or pipx command. If this is your first exposure to Python packaging you can get
all the details from:

- [The PyPA](https://packaging.python.org/en/latest/tutorials/installing-packages/)
- [Install packages in a virtual environment using pip and venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
- [Installing stand alone command line tools](https://packaging.python.org/en/latest/guides/installing-stand-alone-command-line-tools/)

In short, You should install stuff into a Python virtual environment. Newer
Linux distros will make you do this unless you include a command line argument
akin to '--break-my-system' when using pip. I'm not telling you to use pipx.
But... **Use pipx**. Or better visit the [section above](#the-easy-and-fast-way-to-always-run-the-latest-version) on using uv.

### Bootstrapping pipx

Assuming you have only Python installed, your path to pipx is:

```bash
# First get pip installed. Either with apt or dnf, or the ensurepip command.
python3 -m ensurepip

# Update the pip that was just installed.
python3 -m pip install --upgrade pip

# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

### Installing with pipx

Then installing Not1MM is as simple as:

```bash
# Install not1mm
pipx install not1mm
```

If you need to later update Not1MM, you can do so with:

```bash
# Update not1mm
pipx upgrade not1mm
```

## Installing from GitHub Source

Since this is packaged for PyPI, if you want to work on your own source branch,
after cloning from github you would:

```bash
pip install --upgrade pip
pip install setuptools
pip install build
source rebuild.sh
```

from the root directory. This installs a build chain and a local editable copy
of Not1MM.

There's two ways to launch the program from the local editable copy.

You can either be in the root of the source directory and type:

```bash
python not1mm
```

or be in some other directory and just type:

```bash
not1mm
```

## After the Install

You can now open a new terminal and type `not1mm`. On it's first run, it may or
may not install a lovely non AI generated icon, which you can later click on to
launch the application.

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

You can use your package manager to load libxcb-cursor0.

If that's not an option, you can export an environment variable and launch the app like this:

`mbridak@vm:~$ export QT_QPA_PLATFORM=wayland; not1mm`

For a more permanent solution you can place the line
`export QT_QPA_PLATFORM=wayland` in your home directories .bashrc file. Then
after logging out and back in you should be able to launch it normally.
