#!/usr/bin/env bash 
set -euo pipefail

make clean
make
sudo make install

