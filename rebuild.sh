#!/bin/bash
pipx uninstall not1mm
rm dist/*
python3 -m build
pipx install -e .

