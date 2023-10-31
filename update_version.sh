#!/bin/bash

today=$(date +'%y.%m.%d')
today_no_leading_zeros=$(echo "$today" | sed 's/\.0/./g')

tnlz=$(echo version = \"$today_no_leading_zeros\")
str=$(cat pyproject.toml | grep version)
sed -i "s/$str/$tnlz/" pyproject.toml

str=$(cat not1mm/lib/version.py | grep __version__)
tnlz=$(echo __version__ = \"$today_no_leading_zeros\")
sed -i "s/$str/$tnlz/" not1mm/lib/version.py
