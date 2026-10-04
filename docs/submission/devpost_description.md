# Devpost description

Text for the Devpost project page, ready to paste. It is deliberately general, with no formulas and no metrics. The
numbers live in the report (`docs/report/REPORT.md`).

## Elevator pitch (200 characters at most)

We trade what the Fed says: a language model that never sees the future scores every Fed statement into a
Treasury/dollar signal, tested out of sample.

## About the project

```markdown
## Inspiration

Markets hang on every word the Fed says, but most "Fed sentiment" signals quietly cheat: their models were trained on
text written after the speeches they score, and their backtests get tuned until they look good. We wanted to know if
reading the Fed honestly, never peeking into the future and fixing every rule in advance, gives a real edge in
Treasuries and the dollar. We also wanted to test the press conferences: what the Chair says, how he sounds and how he
looks.

## What it does

It reads everything the Fed publishes, scores each sentence as hawkish or dovish, and turns that into a daily "Fed
mood" that trades Treasuries against the dollar. A second study tests whether the Chair's press-conference answers,
voice and facial expressions predict short-term Treasury moves.

## How we built it

- One language model per year, each trained only on text that existed before that year.
- We corrected the public training data, which had the wrong dates on almost every example.
- Every hypothesis and rule was written down and time-stamped before we ran anything.
- Press conferences were timed from live TV captions, and costs came from real market quotes.
- Voice and face models ran on UF's HiPerGator GPUs, and every result was rerun there to confirm it.

## What we found

The daily strategy looked promising on recent data and diversified our portfolio, but it missed the bar we set in
advance, so we report it as fragile, not proven. The press-conference, voice and face signals found nothing tradable.

## Challenges

A model we couldn't get access to, hidden look-ahead bugs (bad dates, a mislabelled video, a sizing step that peeked
at its own trade price), a GPU pipeline that broke at almost every stage, and licensed data we had to keep out of the
public repo.

## What we learned

An honest "it didn't work" beats a lucky backtest. Look-ahead hides in unexpected places, and a fancy model isn't
automatically better than a simple word list: you have to prove it.

## What's next

Time upcoming press conferences precisely, fix the signal's weak spots, and test the Fed's words against short-term
rates before deciding what to trade.
```

## Built with (25 tags)

```
python, pandas, numpy, scipy, statsmodels, pytorch, hugging-face-transformers, chrono-bert, whisper, faster-whisper, speechbrain, wav2vec2, mediapipe, emotiefflib, opencv, onnx-runtime, ffmpeg, nltk, parquet, matplotlib, slurm, hipergator, cuda, databento, fred
```

| Group | Tags |
|---|---|
| Core and statistics | python, pandas, numpy, scipy, statsmodels, parquet, matplotlib |
| Language models | pytorch, hugging-face-transformers, chrono-bert, nltk |
| Speech and voice | whisper, faster-whisper, speechbrain, wav2vec2, ffmpeg |
| Face | mediapipe, emotiefflib, opencv, onnx-runtime |
| Compute | slurm, hipergator, cuda |
| Data | databento, fred |

## Links for the project page

- Repository: https://github.com/savioxavier/gator-quant-hacks
- Full report: `docs/report/REPORT.md` in the repository
