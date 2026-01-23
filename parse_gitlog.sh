# call git log, requesting just the commit date and commit message and direct the output to a temporary file.

git log --since=$1 --pretty=format:"%ad %s" --date=short > scratch.txt
python process-scratch.py
