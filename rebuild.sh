#!/bin/bash
pip uninstall -y not1mm
rm dist/*
python3 -m build
pip install -e .

