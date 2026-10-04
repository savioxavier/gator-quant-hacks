---
library_name: transformers
license: mit
language:
- en
tags:
- chronologically consistent
- modernbert
- glue
pipeline_tag: fill-mask
inference: false
---
# ChronoBERT

## Model Description

ChronoBERT is a series of **high-performance chronologically consistent large language models (LLM)** designed to eliminate lookahead bias and training leakage while maintaining good language understanding in time-sensitive applications. The model is pretrained on **diverse, high-quality, open-source, and timestamped text** to maintain chronological consistency.

All models in the series achieve **GLUE benchmark scores that surpass standard BERT.** This approach preserves the integrity of historical analysis and enables more reliable economic and financial modeling.

- **Developed by:** Songrun He, Linying Lv, Asaf Manela, Jimmy Wu
- **Model type:** Transformer-based bidirectional encoder (ModernBERT architecture)
- **Language(s) (NLP):** English
- **License:** MIT License

## Model Sources

- **Paper:** "Chronologically Consistent Large Language Models" (He, Lv, Manela, Wu, 2025)

## 🚀 Quickstart

You can try ChronoBERT directly in your browser via Google Colab:

<p align="left">
  <a href="https://colab.research.google.com/gist/jimmywucm/64e70e3047bb126989660c92221abf3c/chronobert_tutorial.ipynb" target="_blank">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
  </a>
</p>

Or run it locally with:

```sh
pip install -U transformers>=4.48.0
pip install flash-attn
```

### Extract Embeddings 

The following contains a code snippet illustrating how to use the model to generate embeddings based on given inputs. 

```python
from transformers import AutoTokenizer, AutoModel
device = 'cuda:0'

model_name = "manelalab/chrono-bert-v1-19991231"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

text = "Obviously, the time continuum has been disrupted, creating a new temporal event sequence resulting in this alternate reality. -- Dr. Brown, Back to the Future Part II"

inputs = tokenizer(text, return_tensors="pt").to(device)
outputs = model(**inputs)
```

### Masked Language Modeling (MLM) Prediction 

The following contains a code snippet illustrating how to use the model to predict a missing token given an incomplete sentence.

```python
from transformers import AutoTokenizer, AutoModelForMaskedLM
device = 'cuda:0'

model_name = "manelalab/chrono-bert-v1-20201231"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForMaskedLM.from_pretrained(model_name).to(device)

year_election = 2016
year_begin = year_election+1
text = f"After the {year_election} U.S. presidential election, President [MASK] was inaugurated as U.S. President in the year {year_begin}."

inputs = tokenizer(text, return_tensors="pt").to(device)
outputs = model(**inputs)
masked_index = inputs["input_ids"][0].tolist().index(tokenizer.mask_token_id)
predicted_token_id = outputs.logits[0, masked_index].argmax(axis=-1)
predicted_token = tokenizer.decode(predicted_token_id)
```

## Training Details

### Training Data

- **Pretraining corpus:** Our initial model chrono-bert-v1-19991231 is pretrained on 460 billion tokens of pre-2000, diverse, high-quality, and open-source text data to ensure no leakage of data afterwards.
- **Incremental updates:** Yearly updates from 2000 to 2024 with an additional 65 billion tokens of timestamped text.

### Training Procedure

- **Architecture:** ModernBERT-based model with rotary embeddings and flash attention.
- **Objective:** Masked token prediction.

## Evaluation

### Testing Data, Factors & Metrics

- **Language understanding:** Evaluated on **GLUE benchmark** tasks.
- **Financial forecasting:** Evaluated using **return prediction task** based on Dow Jones Newswire data.
- **Comparison models:** ChronoBERT was benchmarked against **BERT, FinBERT, StoriesLM-v1-1963, and Llama 3.1**.

### Results

- **GLUE Score:** chrono-bert-v1-19991231 and chrono-bert-v1-20241231 achieved GLUE scores of 84.71 and 85.54, respectively, outperforming BERT (84.52).
- **Stock return predictions:** During the sample from 2008-01 to 2023-07, chrono-bert-v1-realtime achieves a long-short portfolio **Sharpe ratio of 4.80**, outperforming BERT, FinBERT, and StoriesLM-v1-1963, and comparable to **Llama 3.1 8B (4.90)**.


## Citation

```
@article{He2025ChronoBERT,
  title={Chronologically Consistent Large Language Models},
  author={He, Songrun and Lv, Linying and Manela, Asaf and Wu, Jimmy},
  journal={Working Paper},
  year={2025}
}
```

## Model Card Authors

- Songrun He (Washington University in St. Louis, h.songrun@wustl.edu)
- Linying Lv (Washington University in St. Louis, llyu@wustl.edu)
- Asaf Manela (Washington University in St. Louis, amanela@wustl.edu)
- Jimmy Wu (Washington University in St. Louis, jimmywu@wustl.edu)



