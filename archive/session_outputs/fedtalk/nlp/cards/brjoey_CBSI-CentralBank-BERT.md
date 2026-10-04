---
language:
- en
base_model:
- bilalzafar/CentralBank-BERT
- google-bert/bert-base-uncased
pipeline_tag: text-classification
tags:
- central_bank_communication
- central_bank
- economics
- hawkish
- dovish
library_name: transformers
---

# CBSI-BERT Models

This model is trained on the replication data of [Nițoi et al. (2023)](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/40JFEK).  
Check out their [paper](https://www.sciencedirect.com/science/article/abs/pii/S2214635023000230) and [website](https://sites.google.com/view/bert-cbsi/) for more information.

The model is trained with the hyperparameters used by [Nițoi et al. (2023)](https://www.sciencedirect.com/science/article/abs/pii/S2214635023000230).  
In addition, different hyperparameters, seeds, and reinitialization of the first L layers were tested. The performance seems relatively stable across hyperparameter settings.  

Alongside these models, FinBERT, different versions of RoBERTa, and EconBERT were tested. The performance of the BERT-based models reported here is significantly better. In addition, fine-tuned [ModernBERT](https://huggingface.co/docs/transformers/main/en/model_doc/modernbert) and [CentralBank-BERT](https://huggingface.co/bilalzafar/CentralBank-BERT) versions are also available.

## Results

| Model                                                                 | F1 Score | Accuracy | Loss |
|------------------------------------------------------------------------|----------|----------|------|
| [CBSI-bert-base-uncased](https://huggingface.co/brjoey/CBSI-bert-base-uncased)   | 0.88     | 0.88     | 0.49 |
| [CBSI-bert-large-uncased](https://huggingface.co/brjoey/CBSI-bert-large-uncased) | 0.92     | 0.92     | 0.45 |
| [CBSI-ModernBERT-base](https://huggingface.co/brjoey/CBSI-ModernBERT-base)   | 0.93    | 0.93    | 0.40 |
| [CBSI-ModernBERT-large](https://huggingface.co/brjoey/CBSI-ModernBERT-large) | 0.91    | 0.91    | 0.53 |
| [CBSI-CentralBank-BERT](https://huggingface.co/brjoey/CBSI-CentralBank-BERT) | 0.92 | 0.92  |0.36 |

## How to use

```python
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# Load model and tokenizer
model_name = "brjoey/CBSI-CentralBank-BERT"
classifier = pipeline(
    "text-classification",
    model=model_name,
    tokenizer=model_name
)

# Define label mapping
cbsi_label_map = {
    0: "neutral",
    1: "dovish",
    2: "hawkish"
}

# Classify a column in a Pandas DataFrame - replace with your DataFrame
texts = [
    "The Governing Council decided to lower interest rates.",
    "The central bank will maintain its current policy stance."
]

df = pd.DataFrame({
    "text": texts
})

# Run classification 
predictions = classifier(
    df["text"].tolist()
)

# Store the results
df["label"], df["score"] = zip(*[
    (cbsi_label_map[int(pred["label"].split("_")[-1])], pred["score"])
    for pred in predictions
])

print("\n                              === Results ===\n")
print(df[["text", "label", "score"]])
```
---
# Citation
If you use this model, please cite: \
Data:\
Nițoi Mihai; Pochea Maria-Miruna; Radu Ștefan-Constantin, 2023, \
"Replication Data for: Unveiling the sentiment behind central bank narratives: A novel deep learning index", \
https://doi.org/10.7910/DVN/40JFEK, Harvard Dataverse, V1

Paper: \
Mihai Niţoi, Maria-Miruna Pochea, Ştefan-Constantin Radu, \
Unveiling the sentiment behind central bank narratives: A novel deep learning index, \
Journal of Behavioral and Experimental Finance, Volume 38, 2023, 100809, ISSN 2214-6350. \
https://doi.org/10.1016/j.jbef.2023.100809

CentralBank-BERT: \
Zafar, M. B., 2025,\
CentralBank-BERT: Machine Learning Evidence on Central Bank Digital Currency Discourse. \
SSRN. https://papers.ssrn.com/abstract=5404456