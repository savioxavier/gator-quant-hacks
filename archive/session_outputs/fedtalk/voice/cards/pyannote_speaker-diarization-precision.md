---
tags:
  - pyannote
  - pyannote-audio
  - pyannote-audio-pipeline
  - audio
  - voice
  - speech
  - speaker
  - speaker-diarization
  - speaker-change-detection
  - voice-activity-detection
  - overlapped-speech-detection
---

# `Precision` speaker diarization

This pipeline runs `Precision` speaker diarization on [pyannoteAI](https://www.pyannote.ai) cloud.  
Read the announcement [blog post](https://www.pyannote.ai/blog/precision-3).

This pipeline is a stripped down version of pyannoteAI SDK that provides [much more features](https://docs.pyannote.ai):
* speaker diarization optimized for speech-to-text
* speaker voiceprinting and identification
* confidence scores
* and more...

A self-hosted version of `Precision` is also available for enterprise customers.

## Setup

1. `pip install pyannote.audio`
2. Create an API key on [`pyannoteAI` dashboard](https://dashboard.pyannote.ai) (free credits included)

## Usage

```python
# initialize speaker diarization pipeline
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
    'pyannote/speaker-diarization-precision', 
    token="{pyannoteAI-api-key}")

# run speaker diarization on pyannoteAI cloud
output = pipeline("/path/to/audio.wav")

# enjoy state-of-the-art speaker diarization
for turn, speaker in output.speaker_diarization:
    print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
```




