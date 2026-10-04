---
license: mit
language:
- en
metrics:
- perplexity
base_model:
- google-bert/bert-base-uncased
pipeline_tag: fill-mask
library_name: transformers
tags:
- bert
- masked-language-modeling
- mlm
- fill-mask
- transformers
- finance
- central-bank
- financial-nlp
- economic-policy
- monetary-policy
- BIS
- speeches
- BIS-Speeches
- pretraining
- domain-adaptation
- financial-domain-adaptation
---

# Central Bank-BERT: Domain-Adaptive Masked Language Model for Central Bank Communication
**Central Bank-BERT** is a **domain-adapted masked language model** based on `bert-base-uncased`, pretrained on more than **66 million tokens** across **over 2 million sentences** extracted from **central bank speeches published by the Bank for International Settlements (1996–2024)**. 
This model is specifically optimized for **masked token prediction** within the highly specialized domains of **monetary policy**, **financial regulation**, and **macroeconomic communication**, enabling deeper contextual understanding of central banking discourse and financial narratives.

## Dataset Summary
- **Source**: BIS Central Bank Speeches (1996–2024)
- **Total Speeches**: 19,609
- **MLM Sentences**: 2,087,615 (_~2.09M_)
- **Total Tokens**: 66,359,113 (_~66.36M_)
- **Avg. Tokens per Sentence**: 31.79

## Model & Training Details
| **Category**          | **Details**                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| **Tokenizer**          | `BertTokenizerFast` (base: `bert-base-uncased`) <br> Vocab Size: **30,522** <br> Max Seq Length: **128** |
| **Model**              | `BertForMaskedLM` (initialized from `bert-base-uncased`) <br> Total Params: **109,514,298 (~109.5M)** <br> Trainable Params: **109,514,298** |
| **Training Setup**     | Epochs: **1** <br> Batch Size (per device): **16** <br> Gradient Accumulation: **2** <br> Effective Batch Size: **32** <br> MLM Probability: **15%** |
| **Hardware**           | Device: **NVIDIA Tesla P100 (Kaggle)** <br> Mixed Precision: **fp16** |
| **Training Duration**  | **~8 hrs 18 mins** <br> Start: *2025-07-19 17:17* <br> End: *2025-07-20 01:35* |
| **Evaluation Results** | **Perplexity** <br> bert-base: *13.06* <br> [`CentralBank-BERT`](https://huggingface.co/bilalzafar/CentralBank-BERT): **4.66** |

> Lower perplexity demonstrates better fit on domain-specific central bank language.

**Notebook: Training, Evaluation & Results**
The full training pipeline, including data preprocessing, tokenizer setup, model training, evaluation, and result visualizations, is documented in the notebook [`cb-bert-mlm.ipynb`](./cb-bert-mlm.ipynb). This notebook includes actual outputs from the training run, perplexity comparisons, manual masked sentence evaluations, and Top-K accuracy analysis—ensuring full transparency and reproducibility of the model development process.

**Model Files**
  - `model.safetensors`: Trained model weights
  - `config.json`: Model architecture and hyperparameters
  - `tokenizer.json`: Serialized tokenizer
  - `vocab.txt`: Vocabulary file
  - `tokenizer_config.json`: Tokenizer configuration
  - `special_tokens_map.json`: Special tokens mapping
  - `training_args.bin`: Training arguments used during pretraining

  This model repository includes all essential files required to load, evaluate, or fine-tune the [`CentralBank-BERT`](https://huggingface.co/bilalzafar/CentralBank-BERT) model using Hugging Face's `transformers` library.
  These components are necessary to ensure full compatibility with the original training environment and to support seamless deployment or transfer learning.

---

## Downstream Models

In addition to the domain-adapted masked language model (**[`CentralBank-BERT`](https://huggingface.co/bilalzafar/CentralBank-BERT)**), a suite of fine-tuned downstream classifiers has been released to support CBDC-specific research and policy analysis. These models share the same encoder backbone and are designed for different classification and information extraction tasks on central bank communication.

| **Model**                       | **Purpose**                                                         | **Intended Use**                                                    | **Link**                                                               |
| ------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **bilalzafar/CBDC-BERT**        | Binary classifier: CBDC vs. Non-CBDC.                               | Flagging CBDC-related discourse in large corpora.                   | [CBDC-BERT](https://huggingface.co/bilalzafar/CBDC-BERT)               |
| **bilalzafar/CBDC-Stance**      | 3-class stance model (Pro, Wait-and-See, Anti).                     | Research on policy stances and discourse monitoring.                | [CBDC-Stance](https://huggingface.co/bilalzafar/CBDC-Stance)           |
| **bilalzafar/CBDC-Sentiment**   | 3-class sentiment model (Positive, Neutral, Negative).              | Tone analysis in central bank communications.                       | [CBDC-Sentiment](https://huggingface.co/bilalzafar/CBDC-Sentiment)     |
| **bilalzafar/CBDC-Type**        | Classifies Retail, Wholesale, General CBDC mentions.                | Distinguishing policy focus (retail vs wholesale).                  | [CBDC-Type](https://huggingface.co/bilalzafar/CBDC-Type)               |
| **bilalzafar/CBDC-Discourse**   | 3-class discourse classifier (Feature, Process, Risk-Benefit).      | Structured categorization of CBDC communications.                   | [CBDC-Discourse](https://huggingface.co/bilalzafar/CBDC-Discourse)     |
| **bilalzafar/CentralBank-NER**  | Named Entity Recognition (NER) model for central banking discourse. | Identifying institutions, persons, and policy entities in speeches. | [CentralBank-NER](https://huggingface.co/bilalzafar/CentralBank-NER)   |


---

## Repository and Replication Package

All **training pipelines, preprocessing scripts, evaluation notebooks, and result outputs** are available in the companion GitHub repository:

🔗 [https://github.com/bilalezafar/CentralBank-BERT](https://github.com/bilalezafar/CentralBank-BERT)

The repository includes:

* End-to-end notebooks for **CentralBank-BERT pretraining** and all **downstream classifiers** (CBDC-BERT, Stance, Sentiment, Type, Discourse, NER).
* Preprocessed **BIS speech dataset subsets** (CBDC-related sentences, annotated splits).
* **Reproducible code** to generate figures, tables, and evaluation metrics reported in the manuscript.
* Deployment-ready scripts for applying models to new corpora.

This ensures full **transparency, reproducibility, and extension** of the CentralBank-BERT family of models.

---

## Citation

If you use this model, please cite as:

**Zafar, M. B. (2025). CentralBank-BERT: Machine learning evidence on central bank digital currency discourse. *Journal of Economics and Business.* [https://doi.org/10.1016/j.jeconbus.2026.106300](https://doi.org/10.1016/j.jeconbus.2026.106300)**

```bibtex
@article{zafar2025centralbankbert,
  title={CentralBank-BERT: Machine learning evidence on central bank digital currency discourse},
  author={Zafar, Muhammad Bilal},
  year={2026},
  journal={Journal of Economics and Business},
  url={https://doi.org/10.1016/j.jeconbus.2026.106300}
}

