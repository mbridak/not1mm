#!/bin/bash

# call git log, and direct the output to a temporary file.
# remove dulicate lines.
# then write a new CHANGELOG.md file

thevar="2023-02-09"

git log --since=$thevar --pretty=format:"%ad %s" --date=short > temp.txt
awk '!seen[$0]++' temp.txt > scratch.txt
rm temp.txt

python process-scratch.py
