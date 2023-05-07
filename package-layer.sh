#!/bin/bash

mkdir -p ./build/layers/$1/python

echo "Installing dependencies ..."
pip install -q -U -t ./build/layers/$1/python -r ./layers/$1/requirements.txt

echo "Including source code ..."
cp ./layers/$1/*.py ./build/layers/$1/python

echo "Zipping layer ..."
(cd ./build/layers/$1 && zip -qr ../$1.zip .)
rm -rf ./build/layers/$1