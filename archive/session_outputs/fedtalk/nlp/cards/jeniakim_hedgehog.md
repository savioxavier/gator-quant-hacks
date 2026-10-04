---
language: en
license: mit
inference: false
---

🦔 HEDGEhog 🦔: BERT-based multi-class uncertainty cues recognition
====================================================================

# Description
A fine-tuned multi-class classification model that detects four different types of uncertainty cues (a.k.a hedges) on a token level.

# Uncertainty types
label | type | description | example
---| ---| ---| ---
E | Epistemic | The proposition is possible, but its truth-value cannot be decided at the moment. | She **may** be already asleep.
I | Investigation | The proposition is in the process of having its truth-value determined. | She **examined** the role of NF-kappaB in protein activation.
D | Doxatic | The proposition expresses beliefs and hypotheses, which may be known as true or false by others. | She **believes** that the Earth is flat.
N | Condition | The proposition is true or false based on the truth-value of another proposition. | **If** she gets the job, she will move to Utrecht.
C | *certain* | *n/a* | *n/a*

# Intended uses and limitations
- The model was fine-tuned with the [Simple Transformers](https://simpletransformers.ai/) library. This library is based on Transformers but the model cannot be used directly with Transformers `pipeline` and classes; doing so would generate incorrect outputs. For this reason, the API on this page is disabled.

# How to use
To generate predictions with the model, use the [Simple Transformers](https://simpletransformers.ai/) library:
```
from simpletransformers.ner import NERModel

model = NERModel(
    'bert',
    'jeniakim/hedgehog',
    use_cuda=False,
    labels=["C", "D", "E", "I", "N"],
)

example = "As much as I definitely enjoy solitude, I wouldn't mind perhaps spending little time with you (Björk)"
predictions, raw_outputs = model.predict([example])
```
The predictions look like this:
```
[[{'As': 'C'},
  {'much': 'C'},
  {'as': 'C'},
  {'I': 'C'},
  {'definitely': 'C'},
  {'enjoy': 'C'},
  {'solitude,': 'C'},
  {'I': 'C'},
  {"wouldn't": 'C'},
  {'mind': 'C'},
  {'perhaps': 'E'},
  {'spending': 'C'},
  {'little': 'C'},
  {'time': 'C'},
  {'with': 'C'},
  {'you': 'C'},
  {'(Björk)': 'C'}]]
```
In other words, the token 'perhaps' is recognized as an **epistemic uncertainty cue** and all the other tokens are not uncertainty cues.

# Training Data
HEDGEhog is trained and evaluated on the [Szeged Uncertainty Corpus](https://rgai.inf.u-szeged.hu/node/160) (Szarvas et al. 2012<sup>1</sup>). The original sentence-level XML version of this dataset is available [here](https://rgai.inf.u-szeged.hu/node/160).

The token-level version that was used for the training can be downloaded from [here](https://1drv.ms/u/s!AvPkt_QxBozXk7BiazucDqZkVxLo6g?e=IisuM6) in a form of pickled pandas DataFrame's. You can download either the split sets (```train.pkl``` 137MB, ```test.pkl``` 17MB, ```dev.pkl``` 17MB) or the full dataset (```szeged_fixed.pkl``` 172MB). Each row in the df contains a token, its features (these are not relevant for HEDGEhog; they were used to train the baseline CRF model, see [here](https://github.com/vanboefer/uncertainty_crf)), its sentence ID, and its label.

# Training Procedure
The following training parameters were used:
- Optimizer: AdamW
- Learning rate: 4e-5
- Num train epochs: 1
- Train batch size: 16

# Evaluation Results
class | precision | recall | F1-score | support
---|---|---|---|---
Epistemic | 0.90 | 0.85 | 0.88 | 624
Doxatic | 0.88 | 0.92 | 0.90 | 142
Investigation | 0.83 | 0.86 | 0.84 | 111
Condition | 0.85 | 0.87 | 0.86 | 86
Certain | 1.00 | 1.00 | 1.00 | 104,751
**macro average** | **0.89** | **0.90** | **0.89** | 105,714

# References
<sup>1</sup> Szarvas, G., Vincze, V., Farkas, R., Móra, G., & Gurevych, I. (2012). Cross-genre and cross-domain detection of semantic uncertainty. *Computational Linguistics, 38*(2), 335-367.
