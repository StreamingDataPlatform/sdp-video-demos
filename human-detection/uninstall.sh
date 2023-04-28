#!/bin/bash

set -e
cd "$(dirname "$(readlink -f "$0")")"

python3 scripts/install.py --config config.ini --uninstall
