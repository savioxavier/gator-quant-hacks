---
library_name: pytorch
license: mit
language:
- en
tags:
- chronologically consistent
- modded-nanogpt
- hellaswag
pipeline_tag: text-generation
inference: false
---
# ChronoGPT

## ChronoGPT Highlights

ChronoGPT is a series **high-performance chronologically consistent large language models (LLMs)** designed to eliminate lookahead bias and training leakage while maintaining good language understanding in time-sensitive applications. The model is pretrained on **diverse, high-quality, open-source, and timestamped text** to maintain chronological consistency.

All models in the series achieve **HellaSwag benchmark scores that surpass those of the GPT-2 124M model.** This approach preserves the integrity of historical analysis and enables more reliable economic and financial modeling.

- **Developed by:** Songrun He, Linying Lv, Asaf Manela, Jimmy Wu
- **Model type:** Transformer-based autoregressive decoder (Modified modded-NanoGPT architecture)
- **Language(s) (NLP):** English
- **License:** MIT License

## Model Overview

**ChronoGPT** has the following features:
- Type: Causal Language Models
- Training Stage: Pretraining
- Number of Parameters: ~1,552 Million
- Encoder & Decoder Partitioning: 26 encoder and 26 decoder layers
- Tokenizer: GPT2Tokenizer from HuggingFace
- Context Length: 1,792
- Embedding Dimension: 1,536

## 🚀 Quickstart

You can try ChronoGPT directly in your browser via Google Colab:

<p align="left">
  <a href="https://colab.research.google.com/github/LinyingLyu/ChronoGPT/blob/main/ChronoGPT_tutorial.ipynb" target="_blank">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>
  </a>
</p>

Or run it locally with:

```bash
pip install -r requirements.txt
```

### Text Generation

The following contains a code snippet illustrating how to use the model generate content based on given inputs. 

```python
import torch
import torch.nn.functional as F
import tiktoken
from huggingface_hub import HfApi, login
from ChronoGPT_inference import *

# ----------------------------- Setup -----------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
cache_dir = 'cache'  # Update this path as needed

tokenizer = tiktoken.get_encoding("gpt2")
max_length = 50
num_return_sequences = 5
seed = 123

# -------------------------- Load Model --------------------------
model = ChronoGPT.from_pretrained(
    "manelalab/chrono-gpt-v1-20241231",
    trust_remote_code=True,
    cache_dir=cache_dir
).to(device)

# ------------------------ Prepare Input -------------------------
prompt = "Hello, I am a language model,"
tokens = tokenizer.encode(prompt)
tokens = torch.tensor(tokens, dtype=torch.long).unsqueeze(0)
tokens = tokens.repeat(num_return_sequences, 1).to(device)

# -------------------- Sampling Initialization -------------------
xgen = tokens.clone()
sample_rng = torch.Generator(device=device)
sample_rng.manual_seed(seed)

# ------------------------- Text Generation -----------------------
while xgen.size(1) < max_length:
    with torch.no_grad():
        with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
            logits, _ = model(xgen)

        logits = logits[:, -1, :]  # Last token logits
        probs = F.softmax(logits, dim=-1)
        topk_probs, topk_indices = torch.topk(probs, 50, dim=-1)

        sampled_idx = torch.multinomial(topk_probs, 1, generator=sample_rng)
        next_token = torch.gather(topk_indices, -1, sampled_idx)

        xgen = torch.cat([xgen, next_token], dim=1)

# ------------------------- Decode Output -------------------------
for i in range(num_return_sequences):
    decoded_tokens = xgen[i, :max_length].tolist()
    decoded_text = tokenizer.decode(decoded_tokens)
    print(f"Rank sample {i}:\n{decoded_text}\n")
```

### Extract Embeddings 

The following contains a code snippet illustrating how to use the model generate embeddings of all layers based on given inputs. 

```python
import torch
import torch.nn.functional as F
import tiktoken
from huggingface_hub import HfApi, login
from ChronoGPT_inference import *

# ----------------------------- Setup -----------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
cache_dir = 'cache'  # Update this path as needed

tokenizer = tiktoken.get_encoding("gpt2")

# -------------------------- Load Model --------------------------
model = ChronoGPT.from_pretrained(
    "manelalab/chrono-gpt-v1-20241231",
    trust_remote_code=True,
    cache_dir=cache_dir
).to(device)

# ----------------------- Embedding Generation ---------------------
text = "Obviously, the time continuum has been disrupted, creating a new temporal event sequence resulting in this alternate reality."

inputs = torch.tensor(tokenizer.encode(text))[:max_length].reshape(1,-1).to(device)
logits, emb = model(inputs)
print('Dimension of embeddings:', emb[0].shape)
```

## Citation

```
@article{He2025ChronoBERT,
  title={Chronologically Consistent Large Language Models},
  author={He, Songrun and Lv, Linying and Manela, Asaf and Wu, Jimmy},
  journal={Working Paper},
  year={2025}
}
```

### Model Card Authors

- Songrun He (Washington University in St. Louis, h.songrun@wustl.edu)
- Linying Lv (Washington University in St. Louis, llyu@wustl.edu)
- Asaf Manela (Washington University in St. Louis, amanela@wustl.edu)
- Jimmy Wu (Washington University in St. Louis, jimmywu@wustl.edu)