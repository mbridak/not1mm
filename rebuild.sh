#!/bin/bash
pip uninstall not1mm
rm dist/*
python3 -m build
pip install -e .

