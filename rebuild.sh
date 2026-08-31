#!/bin/bash
pip3 uninstall -y not1mm
rm -rf ./build/*
rm -rf ./dist/*
python3 -m build
pip3 install -e .

