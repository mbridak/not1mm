#!/bin/bash

today=$(date +'%y.%m.%d')
today_no_leading_zeros=$(echo "$today" | sed 's/\.0/./g')

# Cross-platform sed -i (works on both BSD and GNU)
sed_replace() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS/BSD sed
        sed -i '' "$1" "$2"
    else
        # Linux/GNU sed  
        sed -i "$1" "$2"
    fi
}

tnlz=$(echo version = \"$today_no_leading_zeros\")
str=$(cat pyproject.toml | grep version)
sed_replace "s/$str/$tnlz/" pyproject.toml

str=$(cat not1mm/lib/version.py | grep __version__)
tnlz=$(echo __version__ = \"$today_no_leading_zeros\")
sed_replace "s/$str/$tnlz/" not1mm/lib/version.py
