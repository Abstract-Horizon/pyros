#!/bin/bash

mkdir pyros
cd pyros

git checkout https://github.com/Abstract-Horizon/pyros.git .

./package-pyros.py

sudo target/pyros install command

echo "You can start with typing"
echo ""
echo "pyros help"
