"""Fake `databento` package for offline tests of data/download_databento.py.

Serves the real cached raw bars (read-only) plus a synthetic extension, honouring start (inclusive)
and end (exclusive) like the real Historical.timeseries.get_range. Logs every request to
FAKE_DB_LOG so the test can check what range the builder asked for. Never touches the network.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

_REAL = Path("<home>/.cache/gqh/databento_raw")
_EXT = Path(os.environ["FAKE_DB_EXT"])
_LOG = Path(os.environ["FAKE_DB_LOG"])


class _Store:
    def __init__(self, df):
        self._df = df

    def to_df(self):
        return self._df.set_index("ts_event")


class _TS:
    def get_range(self, dataset, schema, stype_in, symbols, start, end, **kw):
        roots = sorted({s.split(".")[0] for s in symbols})
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"schema": schema, "symbols": symbols, "start": start, "end": end}) + "\n")
        frames = []
        for r in roots:
            if schema == "ohlcv-1d":
                frames.append(pd.read_parquet(_REAL / f"glbx_ohlcv1d_v01__{r}__2010.parquet"))
            else:
                frames.append(pd.read_parquet(_REAL / f"glbx_ohlcv1h_v01_es_zn__{r}__batch.parquet"))
        ext = pd.read_parquet(_EXT / ("daily_ext.parquet" if schema == "ohlcv-1d" else "hourly_ext.parquet"))
        frames.append(ext[ext["symbol"].isin(symbols)])
        df = pd.concat(frames, ignore_index=True)
        df = df[df["symbol"].isin(symbols)]
        a = pd.Timestamp(start, tz="UTC")
        b = pd.Timestamp(end, tz="UTC")
        df = df[(df["ts_event"] >= a) & (df["ts_event"] < b)].sort_values(["ts_event", "symbol"])
        return _Store(df.reset_index(drop=True))


class Historical:
    def __init__(self, key):
        self.timeseries = _TS()
