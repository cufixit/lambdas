#!/bin/bash

echo "Installing dependencies ..."
pip install -q -U -t ./$1/package -r ./$1/requirements.txt
echo "Including dependencies ..."
(cd ./$1/package && zip -qr ../../$1.zip .)
echo "Including source code ..."
zip -j ./$1.zip ./$1/*.py