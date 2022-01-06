#!/bin/bash


mkdir -p pyros
cd pyros

git clone https://github.com/Abstract-Horizon/pyros.git .

python -m venv venv
. venv/bin/activate

./package-pyros.py

sudo target/pyros install command

echo "You can start with typing"
echo ""
echo "pyros help"
