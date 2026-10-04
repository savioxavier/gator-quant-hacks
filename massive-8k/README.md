# Massive 8-K challenge

This folder is the **Massive** sponsor challenge under Systematic Trading.
It is not part of the Fed-communications study in the rest of this repository.

## Files

- `WRITEUP.md` — two-page write-up
- `gator-quant-hacks-8k-options-challenge.ipynb` — runnable notebook
- `requirements.txt`
- `.env.example`

## Run

1. Copy `.env.example` to `.env` in this folder.
2. Set `MASSIVE_API_KEY`. Do not commit `.env`.
3. Install `requirements.txt` (Python 3.10 or later).
4. Open the notebook. Run all cells from the top.

The function `run_study` is at the end of the notebook.
For the sealed window, call `run_study("share_repurchase_program", start, end)`.

The notebook reads `.env` and writes `.massive_cache/` next to the notebook.
Do not commit those.
