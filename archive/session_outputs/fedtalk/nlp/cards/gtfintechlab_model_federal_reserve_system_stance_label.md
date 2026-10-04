---
license: cc-by-nc-sa-4.0

datasets:
- gtfintechlab/federal_reserve_system

language:
- en

metrics:
- accuracy
- f1
- precision
- recall

base_model:
- roberta-base

pipeline_tag: text-classification

library_name: transformers
---

# World of Central Banks Model

**Model Name:** Federal Reserve Stance Detection Model

**Model Type:** Text Classification

**Language:** English

**License:** [CC-BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en)

**Base Model:** [roberta-base](https://huggingface.co/FacebookAI/roberta-base)

**Dataset Used for Training:** [gtfintechlab/federal_reserve_system](https://huggingface.co/datasets/gtfintechlab/federal_reserve_system)

## Model Overview

Federal Reserve Stance Detection Model is a fine-tuned roberta-base model designed to classify text data on **Stance Detection**. This label is annotated in the federal_reserve_system dataset, which focuses on meeting minutes for the Federal Reserve.

## Intended Use

This model is intended for researchers and practitioners working on subjective text classification for the Federal Reserve, particularly within financial and economic contexts. It is specifically designed to assess the **Stance Detection** label, aiding in the analysis of subjective content in financial and economic communications.

## How to Use

To utilize this model, load it using the Hugging Face `transformers` library:

```python
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification, AutoConfig

# Load tokenizer, model, and configuration
tokenizer = AutoTokenizer.from_pretrained("gtfintechlab/federal_reserve_system", do_lower_case=True, do_basic_tokenize=True)
model = AutoModelForSequenceClassification.from_pretrained("gtfintechlab/federal_reserve_system", num_labels=4)
config = AutoConfig.from_pretrained("gtfintechlab/federal_reserve_system")

# Initialize text classification pipeline
classifier = pipeline('text-classification', model=model, tokenizer=tokenizer, config=config, framework="pt")

# Classify Stance Detection
sentences = [
    "[Sentence 1]",
    "[Sentence 2]"
]
results = classifier(sentences, batch_size=128, truncation="only_first")

print(results)
```

In this script:

- **Tokenizer and Model Loading:**  
  Loads the pre-trained tokenizer and model from `gtfintechlab/federal_reserve_system`.

- **Configuration:**  
  Loads model configuration parameters, including the number of labels.

- **Pipeline Initialization:**  
  Initializes a text classification pipeline with the model, tokenizer, and configuration.

- **Classification:**  
  Labels sentences based on **Stance Detection**.

Ensure your environment has the necessary dependencies installed.

## Label Interpretation

- **LABEL_0:** Neutral; the sentence contains neither hawkish or dovish sentiment, or both hawkish and dovish sentiment.
- **LABEL_1:**  Hawkish; the sentnece supports contractionary monetary policy.
- **LABEL_2:** Dovish; the sentence supports expansionary monetary policy.
- **LABEL_3:** Irrelevant; the sentence is not related to monetary policy.

## Training Data

The model was trained on the federal_reserve_system dataset, comprising annotated sentences from the Federal Reserve meeting minutes, labeled by **Stance Detection**. The dataset includes training, validation, and test splits.

## Citation

If you use this model in your research, please cite the federal_reserve_system:

```bibtex
@article{WCBShahSukhaniPardawala,
  title={Words That Unite The World: A Unified Framework for Deciphering Global Central Bank Communications},
  author={Agam Shah, Siddhant Sukhani, Huzaifa Pardawala et al.},
  year={2025}
}
```

For more details, refer to the [federal_reserve_system dataset documentation](https://huggingface.co/datasets/gtfintechlab/federal_reserve_system).

## Contact

For any Federal Reserve System related issues and questions, please contact:

- Huzaifa Pardawala: huzaifahp7[at]gatech[dot]edu

- Siddhant Sukhani: ssukhani3[at]gatech[dot]edu

- Agam Shah: ashah482[at]gatech[dot]edu 