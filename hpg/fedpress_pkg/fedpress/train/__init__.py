"""Training steps that run outside the per-meeting stages (each writes models the stages later read).

* ``stance_walkforward``: one hawkish/dovish/neutral classifier per test year Y, fine-tuned from the
  chronologically pretrained ChronoBERT checkpoint of year Y-1 on labelled sentences dated Y-1 or earlier
  (deviation D1 of the team plan, identical to Amendment 2 of fedspeak_v2).
* ``labels``: builds the labelled sentence table (Hugging Face copy + document types from the authors'
  GitHub repository + an optional team-labelled CSV).
"""
