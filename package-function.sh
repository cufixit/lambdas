#!/bin/bash

mkdir -p ./build/functions

echo "Installing dependencies ..."
pip install -q -U -t ./functions/$1/package -r ./functions/$1/requirements.txt
echo "Including dependencies ..."
(cd ./functions/$1/package && zip -qr ../../../build/functions/$1.zip .)
echo "Including source code ..."
zip -j ./build/functions/$1.zip ./functions/$1/*.py