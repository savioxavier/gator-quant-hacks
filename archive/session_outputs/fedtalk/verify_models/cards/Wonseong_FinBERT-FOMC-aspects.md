---
language:
- en
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
tags:
- finance
- fomc
- bert
- sentiment-analysis
- text-classification
base_model: ZiweiChen/FinBERT-FOMC
widget:
- text: "growth"
  text_pair: "Spending on cars and light trucks increased somewhat in July."
- text: "inflation"
  text_pair: "Prices increased modestly over the period."
model-index:
- name: Wonseong/FinBERT-FOMC-aspects
  results:
  - task:
      type: text-classification
      name: Text Classification
    dataset:
      name: FOMC_sentences_expanded_zeroshot_labeled.xlsx / expanded_10500
      type: private
    metrics:
    - type: accuracy
      value: 0.8789625360230547
      name: Holdout Accuracy
    - type: f1
      value: 0.7980614874405157
      name: Holdout Macro F1
    - type: precision
      value: 0.7708534213383098
      name: Holdout Macro Precision
    - type: recall
      value: 0.8321941498302832
      name: Holdout Macro Recall
    - type: mae
      value: 0.1399295549151457
      name: Holdout MAE
    - type: mse
      value: 0.1777137367915466
      name: Holdout MSE
---

# FinBERT-FOMC Aspect Sentiment v5

This is a single aspect-aware sentiment model fine-tuned from `ZiweiChen/FinBERT-FOMC` on `FOMC_sentences_expanded_zeroshot_labeled.xlsx`.

## Model Details
- Base model: `ZiweiChen/FinBERT-FOMC`
- Training mode: `all`
- Train rows: `28377`
- Eval rows: `3123`

## Labels
- `Negative` (0)
- `Neutral` (1)
- `Positive` (2)

## Inference Contract
Use one model for all targets:
- `text` = `mode`
- `text_pair` = FOMC sentence

Valid `mode` values:
- `growth`
- `employment`
- `inflation`

## Python Usage
```python
from transformers import BertForSequenceClassification, BertTokenizer, pipeline

model_id = "Wonseong/FinBERT-FOMC-aspects"
tokenizer = BertTokenizer.from_pretrained(model_id)
model = BertForSequenceClassification.from_pretrained(model_id)
clf = pipeline("text-classification", model=model, tokenizer=tokenizer)

sentence = "Spending on cars and light trucks increased somewhat in July."
mode = "growth"  # growth | employment | inflation

result = clf({"text": mode, "text_pair": sentence})
print(result)
```

## Local Helper Usage
```python
from predict_aspect import FinBERTFOMCModeClassifier

clf = FinBERTFOMCModeClassifier("Wonseong/FinBERT-FOMC-aspects")
print(clf.predict("Spending on cars and light trucks increased somewhat in July.", mode="growth"))
```

## Metrics

Holdout evaluation:
- Accuracy: `0.8789625360230547`
- Loss: `0.5731372237205505`
- Macro F1: `0.7980614874405157`
- Macro Precision: `0.7708534213383098`
- Macro Recall: `0.8321941498302832`
- MAE: `0.1399295549151457`
- MSE: `0.1777137367915466`
- MAPE: `8.09051126054008`

Full training data fit:
- Accuracy: `0.9348888888888889`
- Macro F1: `0.8977282349978499`
- Macro Precision: `0.8621019267617939`
- Macro Recall: `0.9424642336852936`
- MAE: `0.06847619047619048`
- MSE: `0.07520634920634921`
- MAPE: `3.6275132275132274`

## Training Data Contract
Expected spreadsheet columns in sheet `expanded_10500`:
- `sentence`
- `growth_sentiment_final`
- `employment_sentiment_final`
- `inflation_sentiment_final`

Label values are normalized from `negative`, `neutral`, and `positive`.

## Dataset Provenance
The training file `FOMC_sentences_expanded_zeroshot_labeled.xlsx` contains sentence-level labels for the `expanded_10500` sheet. These aspect labels were generated through zero-shot annotation with `oss-20b` using the prompt template stored in `zeroshot_fomc_sentiment_prompt.txt`.

The labeled dataset can be provided upon reasonable request.

The zero-shot prompt asks for one label per aspect:
- `growth_sentiment_final`
- `employment_sentiment_final`
- `inflation_sentiment_final`

Each aspect is restricted to:
- `positive`
- `neutral`
- `negative`

The prompt design is derived from the human-labeling framework described in:

Kim, W., Sporer, J., Lee, C. L., & Handschuh, S. (2024, November). *Is small really beautiful for central Bank communication? Evaluating language models for finance: Llama-3-70B, GPT-4, FinBERT-FOMC, FinBERT, and VADER.* In *Proceedings of the 5th ACM International Conference on AI in Finance* (pp. 626-633).

## Intended Use
This model is intended for aspect-conditioned sentiment classification on FOMC-related sentences. The caller supplies the target aspect through `mode` and the sentence through `text_pair`.

## Limitations
- This is not a general finance sentiment model for arbitrary entities or tasks.
- Reported metrics are from a holdout split of the labeled spreadsheet, not from external benchmark evaluation.
- The model predicts one of three ordinal sentiment classes only: `Negative`, `Neutral`, `Positive`.

## Training Summary
- Runtime device: `Tesla T4`
- CUDA available: `true`
- BF16: `true`
- FP16: `false`

Additional artifacts in this repo:
- `training_metadata.json`
- `metric_history.csv`
- `mae_mse_curve.png`

## Citation
```bibtex
@article{kim2023analyzing,
  title={Analyzing FOMC minutes: Accuracy and constraints of language models},
  author={Kim, Wonseong and Sp{\~A}{\c{k}}rer, Jan Frederic and Handschuh, Siegfried},
  journal={arXiv preprint arXiv:2304.10164},
  year={2023}
}

@inproceedings{kim2024small,
  author = {Kim, W. and Sporer, J. and Lee, C. L. and Handschuh, S.},
  title = {Is small really beautiful for central Bank communication? Evaluating language models for finance: Llama-3-70B, GPT-4, FinBERT-FOMC, FinBERT, and VADER},
  booktitle = {Proceedings of the 5th ACM International Conference on AI in Finance},
  pages = {626--633},
  year = {2024}
}
```
