---
license: mit
widget:
- text: >-
    We used our liquidity tools to make funding available to banks that might
    need it.
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

CentralBankRoBERTA is a large language model. It combines an economic agent classifier that distinguishes five basic macroeconomic agents with a binary [sentiment classifier](https://huggingface.co/Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier) that identifies the emotional content of sentences in central bank communications.

#### Overview

The AgentClassifier model is designed to classify the target agent of a given text. It can determine whether the text is adressing **households**, **firms**, **the financial sector**, **the government** or **the central bank** itself. This model is based on the RoBERTa architecture and has been fine-tuned on a diverse and extensive dataset to provide accurate predictions.

#### Intended Use

The AgentClassifier model is intended to be used for the analysis of central bank communications where content categorization based on target agents is essential. 

#### Performance

- Accuracy: 93%
- F1 Score: 0.93
- Precision: 0.93
- Recall: 0.93

### Usage

You can use these models in your own applications by leveraging the Hugging Face Transformers library. Below is a Python code snippet demonstrating how to load and use the AgentClassifier model:

```python
from transformers import pipeline

# Load the AgentClassifier model
agent_classifier = pipeline("text-classification", model="Moritz-Pfeifer/CentralBankRoBERTa-agent-classifier")

# Perform agent classification
agent_result = agent_classifier("We used our liquidity tools to make funding available to banks that might need it.")
print("Agent Classification:", agent_result[0]['label'])
```

<table>
  <tr>
    <td colspan="2" style="border-top: 1px solid #ccc; padding: 5px; text-align: left;">
      Please cite this model as Pfeifer, M. and Marohl, V.P. (2023) "CentralBankRoBERTa: A Fine-Tuned Large Language Model for Central Bank Communications", <em>Journal of Finance and Data Science </em> <a href="https://doi.org/10.1016/j.jfds.2023.100114">https://doi.org/10.1016/j.jfds.2023.100114</a> </td>
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
