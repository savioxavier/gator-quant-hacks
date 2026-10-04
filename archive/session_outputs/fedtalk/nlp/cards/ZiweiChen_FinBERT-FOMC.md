# FinBERT-FOMC
FinBERT-FOMC model, a language model based on enhanced sentiment analysis of FOMC meeting minutes. This model is a fine-tuned version of [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert).

FinBERT-FOMC is a FinBERT model fine-tuned on the data used FOMC minutes 2006.1 to 2023.2 with relabeled complex sentences using Sentiment Focus(SF) method. It is more accurate than the original FinBERT for more complex financial sentences.

**Input:**   
A financial text.

**Output:**  
Positive, Negative, Neutral

# How to use
You can use this model with Transformers pipeline for FinBERT-FOMC.

```bash
from transformers import BertTokenizer, BertForSequenceClassification, pipeline

finbert = BertForSequenceClassification.from_pretrained('ZiweiChen/FinBERT-FOMC',num_labels=3)
tokenizer = BertTokenizer.from_pretrained('ZiweiChen/FinBERT-FOMC')
finbert_fomc = pipeline("text-classification", model=finbert, tokenizer=tokenizer)

sentences = ["Spending on cars and light trucks increased somewhat in July after a lackluster pace in the second quarter but apparently weakened in August"]
results = finbert_fomc(sentences)
print(results)
# [{'label': 'Negative', 'score': 0.994509756565094}]

```
Visit https://github.com/Incredible88/FinBERT-FOMC for more details  
Paper location:  https://doi.org/10.1145/3604237.3626843
