---
tags:
- model_hub_mixin
- pytorch_model_hub_mixin
license: openrail
language:
- en
metrics:
- accuracy
base_model:
- microsoft/wavlm-large
pipeline_tag: audio-classification
---
# WavLM-Large for Speech Flow (Fluency) Classification

# Model Description
This model includes the implementation of speech fluency classification described in Vox-Profile: A Speech Foundation Model Benchmark for Characterizing Diverse Speaker and Speech Traits (https://arxiv.org/pdf/2505.14648)

The model first predicts the speech with a 3-second window size and 1-second step size in 
```
["fluent", "disfluent"]
```
If the disfluent speech is detected, we predict the disfluent types in: 
```
[
  "Block", 
  "Prolongation", 
  "Sound Repetition", 
  "Word Repetition", 
  "Interjection"
]
```

# How to use this model

## Download repo
```bash
git clone git@github.com:tiantiaf0627/vox-profile-release.git
```
## Install the package
```bash
conda create -n vox_profile python=3.8
cd vox-profile-release
pip install -e .
```

## Load the model
```python
# Load libraries
import torch
import torch.nn.functional as F
from src.model.fluency.wavlm_fluency import WavLMWrapper

# Find device
device = torch.device("cuda") if torch.cuda.is_available() else "cpu"

# Load model from Huggingface
model = WavLMWrapper.from_pretrained("tiantiaf/wavlm-large-speech-flow").to(device)
model.eval()
```

## Load the model into 3s window chunks
```python
# The way we do inference for fluency is different as the training data is 3s, so we need to do some stacking
audio_data = torch.zeros([1, 16000*10]).float().to(device)
audio_segment = (audio_data.shape[1] - 3*16000) // 16000 + 1
if audio_segment < 1: audio_segment = 1
input_audio = list()
for idx in range(audio_segment): input_audio.append(audio_data[0, 16000*idx:16000*idx+3*16000])
input_audio = torch.stack(input_audio, dim=0)
```
## Prediction
```python
fluency_outputs, disfluency_type_outputs = model(input_audio)
fluency_prob   = F.softmax(fluency_outputs, dim=1).detach().cpu().numpy().astype(float).tolist()

disfluency_type_prob = nn.Sigmoid()(disfluency_type_outputs)
# we can set a higher threshold in practice
disfluency_type_predictions = (disfluency_type_prob > 0.7).int().detach().cpu().numpy().tolist()
disfluency_type_prob = disfluency_type_prob.cpu().numpy().astype(float).tolist()
```

## Now lets gather the predictions for the utterance
```python
utterance_fluency_list = list()
utterance_disfluency_list = list()
for audio_idx in range(audio_segment):
  disfluency_type = list()
  if fluency_prob[audio_idx][0] > 0.5: 
      utterance_fluency_list.append("fluent")
  else: 
      # If the prediction is disfluent, then which disfluency type
      utterance_fluency_list.append("disfluent")
      predictions = disfluency_type_predictions[audio_idx]
      for label_idx in range(len(predictions)):
          if predictions[label_idx] == 1:
            disfluency_type.append(disfluency_type_labels[label_idx])
  utterance_disfluency_list.append(disfluency_type)

# Now print how fluent is the utterance
print(utterance_fluency_list)
print(utterance_disfluency_list)
```

## If you have any questions, please contact: Tiantian Feng (tiantiaf@usc.edu)

## Kindly cite our paper if you are using our model or find it useful in your work
```
@article{feng2025vox,
  title={Vox-Profile: A Speech Foundation Model Benchmark for Characterizing Diverse Speaker and Speech Traits},
  author={Feng, Tiantian and Lee, Jihwan and Xu, Anfeng and Lee, Yoonjeong and Lertpetchpun, Thanathai and Shi, Xuan and Wang, Helin and Thebaud, Thomas and Moro-Velazquez, Laureano and Byrd, Dani and others},
  journal={arXiv preprint arXiv:2505.14648},
  year={2025}
}
```

## If you use this dataset, you should also cite the following dataset:
```
@article{ratner2018fluency,
  title={Fluency Bank: A new resource for fluency research and practice},
  author={Ratner, Nan Bernstein and MacWhinney, Brian},
  journal={Journal of fluency disorders},
  volume={56},
  pages={69--80},
  year={2018},
  publisher={Elsevier}
}

@inproceedings{lea2021sep,
  title={Sep-28k: A dataset for stuttering event detection from podcasts with people who stutter},
  author={Lea, Colin and Mitra, Vikramjit and Joshi, Aparna and Kajarekar, Sachin and Bigham, Jeffrey P},
  booktitle={ICASSP 2021-2021 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)},
  pages={6798--6802},
  year={2021},
  organization={IEEE}
}
```

Responsible use of the Model: the Model is released under Open RAIL license, and users should respect the privacy and consent of the data subjects, and adhere to the relevant laws and regulations in their jurisdictions in using our model.

❌ **Out-of-Scope Use**
- Clinical or diagnostic applications
- Surveillance
- Privacy-invasive applications
- No commercial use