#!/bin/bash
pip uninstall -y not1mm
rm dist/*
uv build
uv pip install -e .

