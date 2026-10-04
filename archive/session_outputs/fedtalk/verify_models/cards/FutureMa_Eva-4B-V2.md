---
license: apache-2.0
language:
  - en
library_name: transformers
pipeline_tag: text-classification
tags:
  - finance
  - earnings-calls
  - evasion-detection
  - nlp
  - qwen3
base_model: Qwen/Qwen3-4B-Instruct-2507
datasets:
  - FutureMa/EvasionBench
---

# Eva-4B-V2

<p align="center">
  <a href="https://huggingface.co/FutureMa/Eva-4B-V2"><img src="https://img.shields.io/badge/🤗-Model-yellow?style=for-the-badge" alt="Model"></a>
  <a href="https://huggingface.co/datasets/FutureMa/EvasionBench"><img src="https://img.shields.io/badge/🤗-Dataset-orange?style=for-the-badge" alt="Dataset"></a>
  <a href="https://github.com/IIIIQIIII/EvasionBench"><img src="https://img.shields.io/badge/GitHub-Repo-blue?style=for-the-badge" alt="GitHub"></a>
  <a href="https://iiiiqiiii.github.io/EvasionBench"><img src="https://img.shields.io/badge/Project-Page-green?style=for-the-badge" alt="Project Page"></a>
  <a href="https://colab.research.google.com/github/IIIIQIIII/EvasionBench/blob/main/scripts/eva4b_inference.ipynb"><img src="https://img.shields.io/badge/Colab-Quick_Start-F9AB00?style=for-the-badge&logo=googlecolab" alt="Open In Colab"></a>
  <a href="https://arxiv.org/abs/2601.09142"><img src="https://img.shields.io/badge/arXiv-Paper-red?style=for-the-badge" alt="Paper"></a>
</p>

<p align="center">
  <b>A 4B parameter model fine-tuned for detecting evasive answers in earnings call Q&A sessions.</b>
</p>

## Model Description

- **Base Model:** [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- **Task:** Text Classification (Evasion Detection)
- **Language:** English
- **License:** Apache 2.0

## Performance

Eva-4B-V2 achieves **84.9% Macro-F1** on the EvasionBench evaluation set, outperforming frontier LLMs:

<p align="center">
  <img src="top5_performance.svg" alt="Top 5 Model Performance" width="100%">
</p>

| Rank | Model | Macro-F1 |
|------|-------|----------|
| 1 | **Eva-4B-V2** | **84.9%** |
| 2 | Gemini 3 Flash | 84.6% |
| 3 | <assistant> Opus 4.5 | 84.4% |
| 4 | GLM-4.7 | 82.9% |
| 5 | GPT-5.2 | 80.9% |

### Per-Class Performance

| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| Direct | 90.6% | 75.1% | 82.1% |
| Intermediate | 73.7% | 87.7% | 80.1% |
| Fully Evasive | 93.3% | 91.6% | 92.4% |

## Label Definitions

| Label | Definition |
|-------|------------|
| `direct` | The core question is directly and explicitly answered |
| `intermediate` | The response provides related context but sidesteps the specific core |
| `fully_evasive` | The question is ignored, explicitly refused, or entirely off-topic |

## Training

### Two-Stage Training Pipeline

```
Qwen3-4B-Instruct-2507
        │
        ▼ Stage 1: 60K consensus data
        │
Eva-4B-Consensus
        │
        ▼ Stage 2: 24K three-judge data
        │
Eva-4B-V2
```

### Training Configuration

| Parameter | Stage 1 | Stage 2 |
|-----------|---------|---------|
| Dataset | 60K consensus | 24K three-judge |
| Epochs | 2 | 2 |
| Learning Rate | 2e-5 | 2e-5 |
| Batch Size | 32 | 32 |
| Max Length | 2500 | 2048 |
| Precision | bfloat16 | bfloat16 |

### Hardware

- **Stage 1:** 2x NVIDIA B200 (180GB SXM6)
- **Stage 2:** 4x NVIDIA H100 (80GB SXM5)

## Usage

### With Transformers

````python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_name = "FutureMa/Eva-4B-V2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")

# Prompt template
prompt = """You are a financial analyst. Your task is to Detect Evasive Answers in Financial Q&A

Question: What is the expected margin for Q4?
Answer: We expect it to be 32%.

Response format:
```json
{"label": "direct|intermediate|fully_evasive"}
```

Answer in ```json content, no other text"""

messages = [{"role": "user", "content": prompt}]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
inputs = tokenizer(text, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=64, temperature=0.1, do_sample=False)

generated = outputs[0][inputs["input_ids"].shape[1]:]
print(tokenizer.decode(generated, skip_special_tokens=True))
# Output: ```json
# {"label": "direct"}
# ```
````

### With vLLM

```python
from vllm import LLM, SamplingParams

llm = LLM(model="FutureMa/Eva-4B-V2")
sampling_params = SamplingParams(temperature=0, max_tokens=64)

outputs = llm.generate([prompt], sampling_params)
print(outputs[0].outputs[0].text)
```

## Links

| Resource | URL |
|----------|-----|
| **Dataset** | [FutureMa/EvasionBench](https://huggingface.co/datasets/FutureMa/EvasionBench) |
| **GitHub** | [IIIIQIIII/EvasionBench](https://github.com/IIIIQIIII/EvasionBench) |
| **Project Page** | [https://iiiiqiiii.github.io/EvasionBench](https://iiiiqiiii.github.io/EvasionBench) |
| **Paper** | [arXiv:2601.09142](https://arxiv.org/abs/2601.09142) |
| **Colab** | [Quick Start Notebook](https://colab.research.google.com/github/IIIIQIIII/EvasionBench/blob/main/scripts/eva4b_inference.ipynb) |

## Citation

```bibtex
@misc{ma2026evasionbenchlargescalebenchmarkdetecting,
  title={EvasionBench: A Large-Scale Benchmark for Detecting Managerial Evasion in Earnings Call Q&A},
  author={Shijian Ma and Yan Lin and Yi Yang},
  year={2026},
  eprint={2601.09142},
  archivePrefix={arXiv},
  primaryClass={cs.LG},
  url={https://arxiv.org/abs/2601.09142}
}
```

## License

Apache 2.0
