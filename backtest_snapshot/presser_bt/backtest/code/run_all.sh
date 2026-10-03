#!/bin/sh
# Reproduce the backtest label end to end (positions are re-frozen by s02; s03 refuses changed positions).
PY="${PY:-python}"
cd "$(dirname "$0")"
$PY -W ignore s01_qa.py && $PY -W ignore s02_positions.py && $PY -W ignore s03_pnl.py && $PY -W ignore s04_spreads.py && $PY -W ignore s05_tables.py
