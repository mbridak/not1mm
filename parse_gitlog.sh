#!/bin/bash

# call git log, requesting just the commit date and commit message and direct the output to a temporary file.

#If no date passed in, use today.
thevar=""
if [$1 -eq ""]; then
    thevar=`date +"%F"`
else
    thevar=$1
fi

git log --since=$thevar --pretty=format:"%ad %s" --date=short > scratch.txt
python process-scratch.py
