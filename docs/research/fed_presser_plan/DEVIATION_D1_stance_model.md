# Deviation D1 (Sat 2026-10-03, about 21:20 UTC): stance model for the press-conference text tests

Applies to H1-primary, H1-answer and H1-Q in the team plan (team_FINAL_PLAN.md). It is logged before any H1 return was computed; the scores are still empty because the registered model is unavailable.

- **Registered model:** frozen gtfintechlab/FOMC-RoBERTa. It is gated (manual approval by the authors) and no approved access exists. Unofficial re-uploads are not used.
- **Replacement, chosen by the team:** a walk-forward chronological stance model, identical to Amendment 2 of research/fedspeak_v2/HYPOTHESIS_v2.md.
  - For press conferences in year Y, the model is manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231 (MIT), fine-tuned on gtfintechlab/fomc_communication labels with year <= Y-1.
  - Three seeds, averaged probabilities, fixed training settings.
  - Answer and statement score = (share hawkish - share dovish).
- **Consequence for the plan's samples:** the 2016-2022 meetings are scored by models that never saw later text or labels. So, as an amendment to the plan's sample rule, 2016-2022 becomes an additional clean sample for H1, reported alongside the registered 2023-2026 Powell confirmation sample. The primary GO/NO-GO is still the registered 2023-2026 Powell sample.
- **Unchanged:** everything else in the locked family (targets, residualisation, costs, gates).

## Update D1a (2026-10-03, about 21:50 UTC, before any H1 return or any full stance-model training): corrected label dates
The same correction as Amendment 3 of research/fedspeak_v2/HYPOTHESIS_v2.md applies: labels are re-dated from the authors' per-document source files, and rows that cannot be dated are excluded from the 2015-2022 models. 2016-2022 is called clean only if, after the correction, no training row for model Y comes from a document dated Y or later. The coverage and leakage counts are reported. The registered 2023-2026 Powell sample is unaffected.
