#!/bin/bash

set -e
cd "$(dirname "$(readlink -f "$0")")"

read_ini() {
    section="$1"
    key="$2"
    found_section=false
    while IFS="= " read -r k v; do
        if [[ $k == "["*"]" ]]; then
            if [[ $k == "[$section]" ]]; then
                found_section=true
            else
                found_section=false
            fi
        elif [[ $found_section == true && $k == $key ]]; then
            echo "$v"
            break
        fi
    done < config.ini
}

NAMESPACE=$(read_ini Project namespace)

echo "[Install human-detection demo in project '$NAMESPACE']"

echo $'\n[Deploy simulator camera]'
helm upgrade --install human-detection ./chart -n $NAMESPACE

echo $'\n[Setup Grafana]'
python3 scripts/setup_grafana.py --config config.ini
