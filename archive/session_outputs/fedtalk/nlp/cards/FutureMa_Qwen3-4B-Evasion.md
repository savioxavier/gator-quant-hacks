---
language:
- en
license: apache-2.0
tags:
- finance
- earnings-call
- evasion-detection
- qwen3
- text-classification
base_model: Qwen/Qwen3-4B-Instruct-2507
datasets:
- earnings-call-qa
metrics:
- accuracy
- f1
model-index:
- name: Qwen3-4B-Evasion
  results:
  - task:
      type: text-classification
      name: Evasion Classification
    metrics:
    - type: accuracy
      value: 0.7508
      name: Accuracy
    - type: f1
      value: 0.7475
      name: Weighted F1
library_name: transformers
pipeline_tag: text-classification
---

# Qwen3-4B-Evasion

A fine-tuned model for detecting evasion levels in earnings call Q&A responses.

## Model Description

**Qwen3-4B-Evasion** is a specialized model fine-tuned from [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) for analyzing executive responses during earnings call Q&A sessions. The model classifies responses into three evasion categories based on the Rasiah taxonomy.

## Intended Use

### Primary Use Case
- Analyze transparency and directness of executive responses in earnings calls
- Financial discourse analysis
- Corporate communication research

### Classification Categories

- **direct**: Clear, on-topic resolution to the question
- **intermediate**: Partially responsive, incomplete, or softened answer
- **fully_evasive**: Does not provide requested information

## Training Details

### Training Data
- **Dataset**: 27,097 earnings call Q&A pairs
- **Source**: Annotated by DeepSeek-V3.2 and Qwen3-Max models
- **Label Distribution**:
  - intermediate: 45.4%
  - direct: 29.8%
  - fully_evasive: 24.9%

### Training Configuration
- **Base Model**: Qwen/Qwen3-4B-Instruct-2507
- **Training Type**: Full parameter fine-tuning
- **Hardware**: 2x NVIDIA B200 GPUs
- **Epochs**: 2
- **Batch Size**: 32 (effective)
- **Learning Rate**: 2e-5
- **Framework**: MS-SWIFT

## Performance

Evaluated on 297 human-annotated benchmark samples:

| Metric | Score |
|--------|-------|
| **Overall Accuracy** | 75.08% |
| **Weighted F1** | 74.75% |
| **Weighted Precision** | 77.56% |
| **Weighted Recall** | 75.08% |

### Per-Class Performance

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| direct | 86.67% | 54.74% | 67.10% | 95 |
| intermediate | 63.12% | 80.91% | 70.92% | 110 |
| fully_evasive | 85.42% | 89.13% | 87.23% | 92 |

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "FutureMa/Qwen3-4B-Evasion"
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Prepare input
question = "What are your revenue projections for next quarter?"
answer = "We don't provide specific guidance on that."

prompt = f"""You are a financial discourse analyst. Classify the evasion level of this executive response.

Question: {question}
Answer: {answer}

Return JSON: {{"rasiah":"direct|intermediate|fully_evasive","confidence":0.00}}"""

messages = [{"role": "user", "content": prompt}]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer([text], return_tensors="pt").to(model.device)

outputs = model.generate(**inputs, max_new_tokens=128, temperature=1)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response)
```

## Limitations

- **Direct Class Recall**: Lower recall (54.74%) for direct responses - model tends to be conservative
- **Domain Specific**: Optimized for earnings call context, may not generalize to other domains
- **English Only**: Trained exclusively on English text
- **Confidence Calibration**: Model confidence scores may require further calibration

## Bias and Ethical Considerations

- Training data derived from corporate earnings calls may reflect existing biases in financial communication
- Model should not be used as sole determinant for investment decisions
- Human oversight recommended for critical applications

## Citation

```bibtex
@misc{qwen3-4b-evasion,
  author = {Shijian Ma},
  title = {Qwen3-4B-Evasion: Earnings Call Evasion Detection Model},
  year = {2025},
  publisher = {HuggingFace},
  howpublished = {\url{https://huggingface.co/FutureMa/Qwen3-4B-Evasion}}
}
```

## License

Apache 2.0

## Acknowledgments

- Base model: [Qwen Team](https://huggingface.co/Qwen)
- Training framework: [MS-SWIFT](https://github.com/modelscope/ms-swift)
- Evasion taxonomy: Rasiah et al.

## Contact

For questions or issues, please open an issue on the model repository.