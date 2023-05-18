# Docker Installation

To use this with `docker`, you'll need to build the container using the supplied `Dockerfile`. The extra installed libraries are based on launching Not1MM and fixing any missing requirements.

It's entirely possible that there are more requirements that will become visible once you actually start using the software. Patches welcome.


# Launch and Configure

Not1MM has two internal variables to track where your data is stored. You can set these variables using Docker environment variables:

`docker run -e XDG_DATA_HOME="$(pwd)/data/" -e XDG_CONFIG_HOME="$(pwd)/config/" imagename:latest`

This should create two directories in your current directory that store the data used inside Not1MM.


# Warning

Note that there is a bug in `xdg-desktop-menu` (not part of Not1MM) which causes issues if your path has a space in it. There's a closed bug report associated with this, but the issue doesn't appear to have been actually fixed. I'm working on how to report this again and hopefully get that fixed. In the mean time, don't use a path with a space in it.
