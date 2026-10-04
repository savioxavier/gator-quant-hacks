---
license: mit
widget:
- text: >-
    The early effects of our policy tightening are also becoming visible,
    especially in sectors like manufacturing and construction that are more
    sensitive to interest rate changes.
datasets:
- Moritz-Pfeifer/CentralBankCommunication
language:
- en
pipeline_tag: text-classification
tags:
- finance
---

<div style="display: flex; align-items: center; gap: 10px;">
  <a href="https://doi.org/10.1016/j.jfds.2023.100114">
    <img src="https://img.shields.io/badge/Paper_Page-j.jfds.2023.100114-green" alt="Paper Page">
  </a>
  <a href="https://github.com/Moritz-Pfeifer/CentralBankRoBERTa">
    <img src="https://img.shields.io/badge/GitHub-Space-blue" alt="GitHub Space">
  </a>
</div>

<div style="display: flex; align-items: center;">
  <img src="https://i.postimg.cc/HLqPqkyk/Central-Bank-Ro-BERTa-logos-black.png" width="200" height="200" style="margin-right: 20px;">
  <div>
    <h1 style="font-size: 36px; font-weight: bold; margin: 0;">CentralBankRoBERTa</h1>
    <p style="font-size: 18px; margin: 0;">A Fine-Tuned Large Language Model for Central Bank Communications</p>
  </div>
</div>


## CentralBankRoBERTa

CentralBankRoBERTA is a large language model. It combines an economic [agent classifier](https://huggingface.co/Moritz-Pfeifer/CentralBankRoBERTa-agent-classifier) that distinguishes five basic macroeconomic agents with a binary sentiment classifier that identifies the emotional content of sentences in central bank communications.

#### Overview

The SentimentClassifier model is designed to detect whether a given sentence is positive or negative for either **households**, **firms**, **the financial sector** or **the government**. This model is based on the RoBERTa architecture and has been fine-tuned on a diverse and extensive dataset to provide accurate predictions.

#### Intended Use

The SentimentClassifier model is intended to be used for the analysis of central bank communications where sentiment analysis is essential. 

#### Performance

- Accuracy: 88%
- F1 Score: 0.88
- Precision: 0.88
- Recall: 0.88

### Usage

You can use these models in your own applications by leveraging the Hugging Face Transformers library. Below is a Python code snippet demonstrating how to load and use the AgentClassifier model:

```python
from transformers import pipeline

# Load the SentimentClassifier model
sentiment_classifier = pipeline("text-classification", model="Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier")

# Perform sentiment analysis
sentinement_result = sentiment_classifier("The early effects of our policy tightening are also becoming visible, especially in sectors like manufacturing and construction that are more sensitive to interest rate changes.")
print("Sentiment:", sentinement_result[0]['label'])
```

<table class="clearfix">
  <tr>
    <td colspan="2" style="border-top: 1px solid #ccc; padding: 5px; text-align: left;">
      Please cite this model as Pfeifer, M. and Marohl, V.P. (2023) "CentralBankRoBERTa: A Fine-Tuned Large Language Model for Central Bank Communications". <em>Journal of Finance and Data Science </em> <a href="https://doi.org/10.1016/j.jfds.2023.100114">https://doi.org/10.1016/j.jfds.2023.100114</a> </td>
  </tr>
  <tr>
    <td style="padding: 5px;">
      Moritz Pfeifer<br>
      Institute for Economic Policy, University of Leipzig<br>
      04109 Leipzig, Germany<br>
      <a href="mailto:pfeifer@wifa.uni-leipzig.de">pfeifer@wifa.uni-leipzig.de</a>
    </td>
    <td style="padding: 5px;">
      Vincent P. Marohl<br>
      Department of Mathematics, Columbia University<br>
      New York NY 10027, USA<br>
      <a href="mailto:vincent.marohl@columbia.edu">vincent.marohl@columbia.edu</a>
    </td>
  </tr>
</table>

### BibTeX entry and citation info

```bibtex
@article{Pfeifer2023,
  title = {CentralBankRoBERTa: A fine-tuned large language model for central bank communications},
  journal = {The Journal of Finance and Data Science},
  volume = {9},
  pages = {100114},
  year = {2023},
  issn = {2405-9188},
  doi = {https://doi.org/10.1016/j.jfds.2023.100114},
  url = {https://www.sciencedirect.com/science/article/pii/S2405918823000302},
  author = {Moritz Pfeifer and Vincent P. Marohl},
}
```
