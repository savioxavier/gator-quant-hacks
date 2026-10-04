---
license: apache-2.0
---
# Emotion2Vec-S

C<sup>2</sup>SER: [Paper](https://arxiv.org/abs/2502.18186) | [Code](https://github.com/zxzhao0/C2SER) | [HuggingFace](https://huggingface.co/collections/ASLP-lab/c2ser-67bc735d820403e7969fe8a0)

## Introduction

This repository contains the implementation of Emotion2Vec-S, a self-supervised learning (SSL) model for speech emotion recognition, as presented in our paper "Steering Language Model to Stable Speech Emotion Recognition via Contextual Perception and Chain of Thought". 

## Requirements and Installation

This project follows the fairseq installation process.

### Requirements

- PyTorch version >= 1.10.0
- Python version >= 3.8

### Installation

To install fairseq and develop locally:

```bash
git clone https://github.com/pytorch/fairseq
cd fairseq
pip install --editable ./
```

### Feature Extraction

You can download the pre-trained [Emotion2vec-S model](https://drive.google.com/drive/folders/1LWWi6bahzn7fJP4fCgPleOyQ30sD_BWO?usp=drive_link) and put it in the `./Emotion2Vec-S/ckpt` folder. 
Meanwhile，we have provided the pretrained checkpoints in the huggingface model hub. You can also download ckpt file from [here](https://huggingface.co/ASLP-lab/Emotion2Vec-S). We also provide [here](https://drive.google.com/drive/folders/12AOVJT7I9GSLJnjHa-Elc-UKgog-mZR2) the feature files for the Emo-Emilia dataset extracted using Emotion2vec-S. 

If you want to extract features using Emotion2Vec-S，you will also need to provide a `wav.scp` file and place it in the `./Emotion2Vec-S` directory. Here is an example of the `wav.scp` file:：
```pgsql
audio_name1 /path/to/audio_name1.wav
audio_name2 /path/to/audio_name2.wav
audio_name3 /path/to/audio_name3.wav
```

Next, you can directly run the following code to extract features：
```python
import torch
import os
import sys
import json
import numpy as np
import argparse
from tqdm import tqdm
import torchaudio
import torch.nn.functional as F
import fairseq
from dataclasses import dataclass

SAMPLING_RATE=16000

@dataclass
class UserDirModule:
    user_dir: str

def extract_fairseq_feature(wav_path, model, device):
    try:
        wav, sr = torchaudio.load(wav_path)
        # 合并多声道为单声道（取平均）
        if wav.size(0) > 1:
            wav = torch.mean(wav, dim=0, keepdim=True)
        if sr != SAMPLING_RATE:
            wav = torchaudio.functional.resample(wav, sr, SAMPLING_RATE)
        wav = wav[0, :].view(1, -1)
        wav = wav.to(device)
        out = model.extract_features(wav)
        return out
    except Exception as e:
        print(f"Error processing audio file {wav_path}: {e}")
        return None

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path', type=str, default="./Emotion2Vec-S/ckpt/checkpoint.pt")
    parser.add_argument('--model_dir', type=str, default="./Emotion2Vec-S/examples/data2vec/")
    parser.add_argument('--dump_dir', type=str, default="./Emotion2Vec-S/features_frm")
    parser.add_argument('--device', type=str, default='cuda')
    parser.add_argument('--data', type=str, default="./Emotion2Vec-S/wav.scp")
    parser.add_argument('--level', type=str, default="frame", help="frame or utterance")
    args = parser.parse_args()

    data = {}
    with open(args.data, 'r') as f:
        for line in f:
            seg_id, wav_path = line.strip().split(maxsplit=1)
            data[seg_id] = wav_path

    os.makedirs(args.dump_dir, exist_ok=True)

    seg_ids = data.keys()
    print(f'Loaded {len(seg_ids)} audio entries')
    # load models
    my_model_path = UserDirModule(args.model_dir)
    fairseq.utils.import_user_module(my_model_path)
    model, cfg, task = fairseq.checkpoint_utils.load_model_ensemble_and_task([args.model_path])
    model = model[0].to(args.device)
    
    for seg_id in tqdm(seg_ids):

        wav_path = data[seg_id]
        if not os.path.exists(wav_path):
            print(f"WARNING: {wav_path} does not exist")
            continue 
        try:
            torchaudio.load(wav_path)
        except:
            print(f'ERROR: Failed to load {wav_path}')
            continue         

        feat = extract_fairseq_feature(wav_path, model, args.device)

        if feat is not None:
            if args.level == 'frame':
                feat = feat['x'].cpu().detach().numpy()[0]
            elif args.level == 'utterance':
                feat = feat['utt_x'].cpu().detach().numpy()[0] 
            else:
                raise ValueError("Unknown level: {}".format(args.level))            

            save_path = os.path.join(args.dump_dir, f"{seg_id}.npy")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            np.save(save_path, feat)
            print(f"Processed: {seg_id} | Shape: {feat.shape} | Saved to: {save_path}")
        else:
            print(f"Skipped problematic file: {seg_id}")

```
Alternatively, you can adjust the code according to your needs. The code path is `./Emotion2Vec-S/speech_feature_extraction.py`. You can also use the `./Emotion2Vec-S/extract_feature.sh` script to batch process features for multiple datasets. The script supports parallel processing and offers the following parameters:

- `--model_path`: Path to the checkpoint file
- `--model_dir`: Path to the model
- `--dump_dir`: Directory to save extracted features
- `--device`: Device to run the model on (e.g., 'cuda:0')
- `--data`: Path to the dataset scp file
- `--level`: Level of feature (frame level or utterance level)

## 2. Training and testing on EmoBox using extracted features

If you want to test our model on other datasets using [EmoBox](https://github.com/emo-box/EmoBox/tree/main). There is also an example provided below, which you can modify to suit your needs:

Use k-fold cross-validation with learning rates (1e-3, 1e-4) and hidden sizes (128, 256):

```bash
cd examples/sb
data=/path/to/your/data_files
lrs=(1e-3 1e-4)               # Learning rate list
hidden_sizes=(128 256)        # Hidden size list
gpus=(0 1 2 3)                # GPU list
task_id=0
declare -A dataset_folds=(
    ["mesd"]=1
)
declare -A dataset_classes=(
    ["mesd"]=6
)
datasets=("mesd")

for dataset in "${datasets[@]}"; do
    folds=${dataset_folds[$dataset]}
    n_classes=${dataset_classes[$dataset]}

    for lr in "${lrs[@]}"; do
        for hidden_size in "${hidden_sizes[@]}"; do
            gpu=${gpus[$task_id % ${#gpus[@]}]}
            export CUDA_VISIBLE_DEVICES=$gpu
            task_number=$((task_id + 1))
            for fold in $(seq 1 $folds); do
                echo "Training fold $fold with lr=$lr, hidden_size=$hidden_size on GPU $gpu, task_number=$task_number, dataset=$dataset..."
                python3 train.py \
                    hparams/data2vec2-large_freeze.yaml \
                    --output_folder /path/to/your/${dataset}-S/fold${fold}_lr${lr}_hidden${hidden_size} \
                    --seed 1234 \
                    --batch_size 32 \
                    --lr $lr \
                    --train_annotation ${data}/${dataset}/fold_${fold}/${dataset}_train_fold_${fold}.json \
                    --test_annotation ${data}/${dataset}/fold_${fold}/${dataset}_test_fold_${fold}.json \
                    --number_of_epochs 100 \
                    --feat_dir /path/to/your/dump_${dataset}-S \
                    --label_map ${data}/${dataset}/label_map.json \
                    --device cuda \
                    --out_n_neurons ${n_classes} \
                    --hidden_size $hidden_size &
            done
            task_id=$((task_id + 1))
        done
    done
done

wait
echo "All training tasks completed."
```