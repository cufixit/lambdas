#!/bin/bash

mkdir -p ./build

echo "Installing dependencies ..."
pip install -q -U -t ./$1/package -r ./$1/requirements.txt
echo "Including dependencies ..."
(cd ./$1/package && zip -qr ../../build/$1.zip .)
echo "Including source code ..."
zip -j ./build/$1.zip ./$1/*.py