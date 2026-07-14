#!/bin/bash
pip uninstall -y not1mm
rm dist/*
python3 -m build
python3 -m twine upload dist/*
