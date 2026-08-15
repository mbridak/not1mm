#!/bin/bash
pip3 uninstall -y not1mm
rm dist/*
python3 -m build
pip3 install -e .

