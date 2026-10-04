import os
import re
from datetime import datetime
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
import pandas as pd

TOKEN_HUB = os.environ.get("TOKEN_HUB", None)

# ---------------------------------------------------------------------------
# Version registry
# Each entry maps a human-readable label to the dataset repos/paths and an
# optional git *revision* (commit SHA, branch, or tag) for each source.
# Set revision=None to always pull the latest default branch.
# ---------------------------------------------------------------------------
VERSIONS = {
    "02-10-2026": {
        "label": "Add TheStageAI/thewhisper-large-v3-turbo, add FermionResearch/Phonon-2, update ibm-granite/granite-speech-5.0 with speed-up. Add Armenian 🇦🇲 to multilingual.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voice Arena Monsoon", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "c23ca4f10e5f1a77c9fd3b41e17cd06a04f0f56c"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "54d262667d97d24108560c3b6858713b7eb01ecc"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "54d262667d97d24108560c3b6858713b7eb01ecc"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "54d262667d97d24108560c3b6858713b7eb01ecc"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "54d262667d97d24108560c3b6858713b7eb01ecc"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "54d262667d97d24108560c3b6858713b7eb01ecc"},
        "hindi":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hi.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "dutch":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_nl.csv",     "revision": "54d262667d97d24108560c3b6858713b7eb01ecc"},
        "armenian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hy.csv",     "revision": "e99277674581549da40500936f934ae20a7aa1c7"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "4f164c2c904b630d9777323b5d2e7f1f549d0143"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "2ed6a388be388d51d291ab8eb1dfb884c74dcc5d"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "479f969d32a068ad76909eaeb493ddbb5b4bac4f"},
        "voicearena":     {"repo": "hf-audio/voicearena_shortform_results",  "file": "voicearena_short_latest.csv",  "revision": "b82bf4f67dcdaa13e8432ca41487e9114117c320"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "25-09-2026": {
        "label": "Add abr-ai models (9m, 84m), add Zipformer and Parakeet TDT with fast-asr-gpu decoding library, and add sprag API.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voice Arena Monsoon", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "d2c5b384deccdb82834f41aeaffcc618c00efa2f"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "hindi":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hi.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "dutch":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_nl.csv",     "revision": "d2341ed252c0bc3f692b4dd02839f41d96673c3b"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "bb562d8611c00e72ce65c56f3c5bc44e30b064a5"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "5ec509e63e69050542a4f2d4319405d49080bb0a"},
        "voicearena":     {"repo": "hf-audio/voicearena_shortform_results",  "file": "voicearena_short_latest.csv",  "revision": "60df1696b863e44dfa95f3f0fce3e45022c8197a"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "19-09-2026": {
        "label": "Add meta/muse-voice-transcribe.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voice Arena Monsoon", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "7e57dda97fe368a406fbfe5fee1de6f8266a5a04"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "96138dc7e4e8b5a13e6cb52ade8cc83c780c4c32"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "96dbd94b1f5a00c8bd42a21ab717bf14734249db"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "635716c21a21ed42c485ff4e37a97d34ed4a3db6"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "43947d9d9279f181f2a601088918606602d10d7f"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "b82833d19a950a236c15ea68ac0497f1b9e260ef"},
        "hindi":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hi.csv",     "revision": "b10a5e4c474b472dbc74bfc19a46f0cfd731e71b"},
        "dutch":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_nl.csv",     "revision": "eda0d48758ee7d00e8a292c2b3b24bd829df2321"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "ad9aebf06d97fd040f98b683992baf1ff7034657"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "610714e7bdfde63a1a788e83156d2e74058cdf21"},
        "voicearena":     {"repo": "hf-audio/voicearena_shortform_results",  "file": "voicearena_short_latest.csv",  "revision": "8c9d0a26bffd25b95f37c889fb1f221f81c68de7"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "11-09-2026": {
        "label": "Add microsoft/azure-speech-07-2026, google/gemma-4-E4B-it, FunAudioLLM/Fun-ASR-Nano-2512-hf, sophea/asr-k1 (preview).",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voice Arena Monsoon", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "34ee9976c0e916f568301caf4c2341321e2d418b"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "21feba58b409860f9cce7dd0b5007cf49df8f4ac"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "64b473fbc7ffb37503467759fad5fa8e58a26e59"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "393bcf4523425b4d210e2f8dd34860e94e69cdde"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "dbf6c78e5b15fffebb7c903dfcf46785343755f3"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "375a9671b552ec2c751f3ca8ab52eb2f82f284cf"},
        "hindi":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hi.csv",     "revision": "a9b490c9207708ea4e6a6dbbf9bdc18febb1922f"},
        "dutch":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_nl.csv",     "revision": "8efdc9701188e5ccb5b6220b57b2033ac274a2ee"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "d29e285b59aca721a0e9733f6d5f126b367d476a"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "45ec5bfacc222ecc4124ae277be26613da2467e4"},
        "voicearena":     {"repo": "hf-audio/voicearena_shortform_results",  "file": "voicearena_short_latest.csv",  "revision": "ca4e5b7d25a61f2a822022f32e0294fd22f8db9d"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "04-09-2026": {
        "label": "Add Dutch to multilingual. Add modulate/multilingual and zoom/scribe_v2_pro to shortform English.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voice Arena Monsoon", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "ba5712d5ace8f785fa0daae1aecea8561ecd87c9"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "41432b8973f02d61ac7b9647e03ed06a2a4d213b"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "f815da2788dce4bfa80c616faa4992405da0d70b"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "ac1671be60849911c7e7e1d072ae0b7a3a9bbaf0"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "2614e6b9f02d5bbc0928674e8ad9a6b6bbd45733"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "6449d2d773429ec53442eec31300455a9f705631"},
        "hindi":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hi.csv",     "revision": "9a13eac44dc92a2c8ecc22506c262b2d4466b976"},
        "dutch":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_nl.csv",     "revision": "b462ae77f7c9a0e07d86ff5072cdf6ec00a2540d"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "04889bc783f4fa1b3ee107389ead94ce97aa9778"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "5e8b1b9406b93da041ce70180c748d37eca2a0c9"},
        "voicearena":     {"repo": "hf-audio/voicearena_shortform_results",  "file": "voicearena_short_latest.csv",  "revision": "7e80e21d2e9d3086d313ad69f341b7f84fcb488d"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "28-08-2026": {
        "label": "Add Voice Arena data: English with Indian accent and Hindi. Add assemblyai/universal-3-5-pro, HojoAI/Hojo-ASR-Multi-V1, and OpenMOSS-Team/MOSS-Transcribe-Diarize to multilingual.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voice Arena Monsoon", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "ddd7fd73c4a33c5d6f616f5bd7ea230a657f15ad"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "41432b8973f02d61ac7b9647e03ed06a2a4d213b"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "f815da2788dce4bfa80c616faa4992405da0d70b"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "ac1671be60849911c7e7e1d072ae0b7a3a9bbaf0"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "2614e6b9f02d5bbc0928674e8ad9a6b6bbd45733"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "6449d2d773429ec53442eec31300455a9f705631"},
        "hindi":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_hi.csv",     "revision": "9a13eac44dc92a2c8ecc22506c262b2d4466b976"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "1f5512dd8081faa38359064f4fbd47a5e97bc976"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "4627bb807a292eed5c41471a787dbb4bb17832f3"},
        "voicearena":     {"repo": "hf-audio/voicearena_shortform_results",  "file": "voicearena_short_latest.csv",  "revision": "fc38f2f9becf99856acfd2484ed8c1a4fb4a0786"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "25-08-2026": {
        "label": "Add IBM Granite Speech 5.0 Turbo CTC models.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "dceb658a67e0b00dacf1514ae10ae8b2c8a20881"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "e1ce1e0c80f46cd9c1d13131d55cd91fc7aa0739"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "68116c85421723682adc17c9398bdcda9d43e0f0"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "38cc92c9febe7eb7064ed931dfec12fe75622927"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "dadea2a701cc8fc4e6db742d0d9b803bbcbb5303"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "11bff137e10ebcccf07b3b1cb77278d25aa2bafa"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "1f5512dd8081faa38359064f4fbd47a5e97bc976"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "4627bb807a292eed5c41471a787dbb4bb17832f3"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "21-08-2026": {
        "label": "Add benchmark fitting tab, and switch to Earnings22-Cleaned-AA-chunked.",
        "default_datasets": ["AMI-Cleaned", "Earnings22-Cleaned-AA-chunked", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "ef70a10e286c7e3bd502a7807f7783480f7edb44"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "e1ce1e0c80f46cd9c1d13131d55cd91fc7aa0739"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "68116c85421723682adc17c9398bdcda9d43e0f0"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "38cc92c9febe7eb7064ed931dfec12fe75622927"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "dadea2a701cc8fc4e6db742d0d9b803bbcbb5303"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "11bff137e10ebcccf07b3b1cb77278d25aa2bafa"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "8ef60d8d5e444afecf9b9da05ab8c7a49f30eecf"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "ed54e4c7588b016ddfb1f84b8f43941683b8904b"},
        "benchmark_fitting":     {"repo": "hf-audio/benchmark_fitting",  "revision": "5ccac7c307063723db20298e36bb244a57054b36"},
    },
    "05-08-2026": {
        "label": "Add multilingual results for Nemotron streaming, VibeVoice ASR, Qwen ASR HF. Force language for all multilingual models (like API and Nemo models).",
        "default_datasets": ["AMI-Cleaned", "Earnings22", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "1da45645cd660cf8c1624f91b4d2b854582a5c5e"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "e1ce1e0c80f46cd9c1d13131d55cd91fc7aa0739"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "68116c85421723682adc17c9398bdcda9d43e0f0"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "38cc92c9febe7eb7064ed931dfec12fe75622927"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "dadea2a701cc8fc4e6db742d0d9b803bbcbb5303"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "11bff137e10ebcccf07b3b1cb77278d25aa2bafa"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "f5bfa851fe6ea28662fb9cbdf3645c00b041e7bc"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "c15605c1ebd6b4bdaa2e4ecfcd485a008a6051d4"},
    },
    "31-07-2026": {
        "label": "Add MOSS-Transcribe-Diarize and QwenASR Transformers checkpoints. Remove older models",
        "default_datasets": ["AMI-Cleaned", "Earnings22", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "1da45645cd660cf8c1624f91b4d2b854582a5c5e"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "7e99f54bd3fc9eb195c051d84550ba4708d591e7"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "7e99f54bd3fc9eb195c051d84550ba4708d591e7"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "7e99f54bd3fc9eb195c051d84550ba4708d591e7"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "7e99f54bd3fc9eb195c051d84550ba4708d591e7"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "7e99f54bd3fc9eb195c051d84550ba4708d591e7"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "f5bfa851fe6ea28662fb9cbdf3645c00b041e7bc"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "c15605c1ebd6b4bdaa2e4ecfcd485a008a6051d4"},
    },
    "24-07-2026": {
        "label": "Add HojoAI/Hojo-ASR-V1. Add soniox/stt-async-v5 and ibm-granite/granite-speech-4.1-2b-nar to multilingual. Remove v1 Omnilingual from multilingual.",
        "default_datasets": ["AMI-Cleaned", "Earnings22", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned", "Private (scripted)", "Private (conversational)"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "1d3e13c97cd949c6e11f6bc872c20299145cd80a"},
        "french":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_fr.csv",     "revision": "44035251aa582eb738f3d26dcb822c9ec81d62de"},
        "german":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_de.csv",     "revision": "44035251aa582eb738f3d26dcb822c9ec81d62de"},
        "spanish":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_es.csv",     "revision": "44035251aa582eb738f3d26dcb822c9ec81d62de"},
        "italian":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_it.csv",     "revision": "44035251aa582eb738f3d26dcb822c9ec81d62de"},
        "portuguese":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_pt.csv",     "revision": "44035251aa582eb738f3d26dcb822c9ec81d62de"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "f2c2db410d890ad0f8f8311799a7c95e3bdc46a6"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "e760215c8d96af61a2d04dfd5c5a649f2c1089a2"},
    },
    "16-07-2026": {
        "label": "Add AutoArk-AI/Audio8-ASR-0.1B, soundsgoodai/Zipformer-cr-ctc-transducer-XL-290M, modulate/multilingual.",
        "default_datasets": ["AMI-Cleaned", "Earnings22", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "bd012e90273e08a719f9865a74676e73831743ca"},
        "multilingual":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_latest.csv",     "revision": "8e223df5c2eb64af2488db044d4ebe4bd889a3d8"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "bb17c35ab9f4225227ef3f129a9eccebcbf37b07"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "9e1da30e5bf2a124244979a944fd01347f8bb7ed"},
    },
    "10-07-2026": {
        "label": "Add modulate/vfast, gladia/solaria-3, assembly/universal-3-5-pro.",
        "default_datasets": ["AMI-Cleaned", "Earnings22", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "36717739242fa1251dd26340765a386aa4db576c"},
        "multilingual":  {"repo": "hf-audio/multilingual_evals",           "file": "multilingual_latest.csv",     "revision": "cbe04e5a2558fda6be01a6697e2771ba3bb8cdd3"},
        "longform":      {"repo": "hf-audio/leaderboard_longform",         "file": "longform_latest.csv",         "revision": "13d1000f7ba7cd3ca0d3f3864b69e672980254a6"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "f48148d1e8fc27912e00ae5b3144f8ee43909984"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "3bbbfd278b0b95fa262f672fc04f126e6a139cef"},
    },
    "07-07-2026": {
        "label": "Add cleaned splits for AMI, Gigaspeech, and Voxpopuli. Add ElevenLabs Scribe v2 and Nemotron streaming.",
        "default_datasets": ["AMI-Cleaned", "Earnings22", "Gigaspeech-Cleaned", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli-AA-Cleaned"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "db66be50b203d97d14b7447446da244f98670a35"},
        "multilingual":  {"repo": "Steveeeeeeen/multilingual_evals",       "file": "multilingual_latest.csv",     "revision": "5990ea8cff5d2692e7e26db8c6a5dc68c874174b"},
        "longform":      {"repo": "Steveeeeeeen/leaderboard_longform",     "file": "longform_latest.csv",         "revision": "be9066187270e3f298bc100d9fe0e65e455574a3"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "ed164286f72a81a4bb981e8d74771d49e7608407"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "c4ed42dcb6064087aae7c43b0d6710eea4c98d7f"},
    },
    "29-06-2026": {
        "label": "Add MOSS-Transcribe-preview-2B",
        "default_datasets": ["AMI", "Earnings22", "Gigaspeech", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "9518bb0d6fe210c28b33c1cece9a81e011ded6c2"},
        "multilingual":  {"repo": "Steveeeeeeen/multilingual_evals",       "file": "multilingual_latest.csv",     "revision": "5990ea8cff5d2692e7e26db8c6a5dc68c874174b"},
        "longform":      {"repo": "Steveeeeeeen/leaderboard_longform",     "file": "longform_latest.csv",         "revision": "be9066187270e3f298bc100d9fe0e65e455574a3"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "d813596850c051e411cfcc457ea194a1ef0e612b"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "f398e8838a372409b8930c88185b03572459fc5f"},
    },
    "24-06-2026": {
        "label": "Switch to H200 GPUs for eval and update English normalizer (better mappings and merge compounds with kaldialign). Add AutoArk (0.6B, 3B) and Higgs 2.7B.",
        "default_datasets": ["AMI", "Earnings22", "Gigaspeech", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "0dada3a8cb1e3c9ff51cfda5f4a2845ab71b23b0"},
        "multilingual":  {"repo": "Steveeeeeeen/multilingual_evals",       "file": "multilingual_latest.csv",     "revision": "5990ea8cff5d2692e7e26db8c6a5dc68c874174b"},
        "longform":      {"repo": "Steveeeeeeen/leaderboard_longform",     "file": "longform_latest.csv",         "revision": "be9066187270e3f298bc100d9fe0e65e455574a3"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "1fcffc9bf175290486cecdbe3544112964511749"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "49c677aadeffc571b86bc9a416272f866db26909"},
    },
    "13-06-2026": {
        "label": "Add Microsoft Azure Speech API, Reson8, Applied Brain Research Niagara, SoundsgoodAI Zipformer XL, and Smallest AI Pulse.",
        "default_datasets": ["AMI", "Earnings22", "Gigaspeech", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "b27154be631663d5af6d166883f519e7f63b7243"},
        "multilingual":  {"repo": "Steveeeeeeen/multilingual_evals",       "file": "multilingual_latest.csv",     "revision": "5990ea8cff5d2692e7e26db8c6a5dc68c874174b"},
        "longform":      {"repo": "Steveeeeeeen/leaderboard_longform",     "file": "longform_latest.csv",         "revision": "be9066187270e3f298bc100d9fe0e65e455574a3"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "216120916bc5d24e624a901b4ce2a28fa92ca317"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "d3303faed2197b3c8681606055ccf9fa6576e568"},
    },
    "20-05-2026": {
        "label": "Remove Tedlium dataset.",
        "default_datasets": ["AMI", "Earnings22", "Gigaspeech", "LS Clean", "LS Other", "SPGISpeech", "Voxpopuli"],
        "english_short": {"repo": "hf-audio/open-asr-leaderboard-results", "file": "english_short_latest.csv",   "revision": "f82da8589575706245e606f6c845bb3df6c93c71"},
        "multilingual":  {"repo": "Steveeeeeeen/multilingual_evals",       "file": "26_march_2026_latest.csv",     "revision": "40ee38190ed9413bffac46386aa7e1d63f109c1c"},
        "longform":      {"repo": "Steveeeeeeen/leaderboard_longform",     "file": "longform_latest.csv",         "revision": "be9066187270e3f298bc100d9fe0e65e455574a3"},
        "appen":         {"repo": "hf-audio/appen_shortform_results",      "file": "appen_short_latest.csv",      "revision": "216120916bc5d24e624a901b4ce2a28fa92ca317"},
        "dataocean":     {"repo": "hf-audio/dataocean_shortform_results",  "file": "dataocean_short_latest.csv",  "revision": "d3303faed2197b3c8681606055ccf9fa6576e568"},
    },
}

# "latest" is always an alias for the most recently added version above (the
# first entry — new versions are prepended, not appended) — synthesized here
# rather than hand-maintained as its own block, so it can never drift out of
# sync with it. Kept as its own top-of-dict entry so it still reads "Latest
# results" in the version dropdown instead of a raw date.
_latest_version = next(iter(VERSIONS.values()))
VERSIONS = {"latest": {**_latest_version, "label": "Latest results"}, **VERSIONS}

LATEST_VERSION = "latest"

# Per-language keys used in the version registry for the multilingual format
# that ships one CSV per language, mapped to their language codes. Versions
# using the legacy single combined CSV keep a "multilingual" key instead.
MULTILINGUAL_LANGUAGE_KEYS = {
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "hindi": "hi",
    "dutch": "nl",
    "armenian": "hy",
}

# Required columns for the fixed-schema private-data / longform CSVs, used to
# validate a download before trusting it (see _load_version_csv). Mirrors the
# per-dataset column lists in app.py (APPEN_SCRIPTED/APPEN_CONVERSATIONAL,
# DATAOCEAN_SCRIPTED/DATAOCEAN_CONVERSATIONAL, VOICEARENA_*) — keep in sync.
LONGFORM_REQUIRED_COLUMNS = {"model_id"}
APPEN_REQUIRED_COLUMNS = {
    "model", "Scripted-US", "Scripted-AU", "Scripted-CA", "Scripted-IN",
    "Conversational-US003", "Conversational-US004", "Conversational-IN",
}
DATAOCEAN_REQUIRED_COLUMNS = {
    "model", "Scripted-US", "Scripted-GB", "Conversational-US", "Conversational-GB",
}
VOICEARENA_REQUIRED_COLUMNS = {"model", "HF_English_Private_Set", "HF_Hindi_Private_Set"}

# Human-friendly changelog. Dates and their default text come from VERSIONS (see
# _build_changelog), so a new version only needs to be defined once — in
# VERSIONS. Add an entry here only to (a) give a version a richer description
# than its label, or (b) record an update that never had a version bump (e.g. a
# blog-only change). Newest first; each line: "- **<D Month YYYY>** — <text>".
# The date must match the version's date (DD-MM-YYYY) to override its label.
CHANGELOG_MANUAL = """
- **31 July 2026** — Add Pareto plots for multilingual and (WER vs model size). Add MOSS-Transcribe-Diarize and QwenASR Transformers checkpoints. Remove older models (efficient-speech/lite-whisper-large-v3, efficient-speech/lite-whisper-large-v3-turbo-acc, efficient-speech/lite-whisper-large-v3-fast, nvidia/stt_en_conformer_ctc_large, nvidia/stt_en_fastconformer_transducer_large, nvidia/stt_en_fastconformer_ctc_large, usefulsensors/moonshine-base, nvidia/stt_en_conformer_transducer_small, nvidia/stt_en_conformer_ctc_small, speechbrain/asr-wav2vec2-librispeech, facebook/hubert-xlarge-ls960-ft, facebook/data2vec-audio-large-960, facebook/wav2vec2-large-robust-ft-libri-960h, facebook/wav2vec2-conformer-rope-large-960h-ft, facebook/wav2vec2-conformer-rel-pos-large-960h-ft, facebook/wav2vec2-large-960h, facebook/data2vec-audio-base-960h, facebook/wav2vec2-base-960h).
- **24 July 2026** — New Multilingual interface: toggle desired languages and average WER is computed as macro-average across selected language (rather than micro-average across all datasets). Add medals to indicate top models in each category. Private data used in default average. Add HojoAI/Hojo-ASR-V1. Add soniox/stt-async-v5 and ibm-granite/granite-speech-4.1-2b-nar to multilingual. Remove v1 Omnilingual from multilingual.
- **10 July 2026** — Add search and proprietary model filter to all tabs. Add modulate/vfast, gladia/solaria-3, assembly/universal-3-5-pro.
- **7 July 2026** — Add Voxpopuli-Cleaned-AA (cleaned version of Voxpopuli by Artificial Analysis). Add cleaned splits for AMI and Gigaspeech that remove audio less than 1 second. Add ElevenLabs Scribe v2 and Nemotron streaming.
- **24 June 2026** — Add versioning for seeing past results. Switch to H200 GPUs for eval and updated English normalizer (better mappings and merge compounds with kaldialign). Add AutoArk AI models (0.6B, 3B) and Boson AI model (bosonai/higgs-audio-v3-stt).
- **13 June 2026** — Added new model submissions: Microsoft Azure Speech API (`microsoft/azure-speech-05-2026`, also evaluated on the Multilingual and Private Data tabs), Reson8 (`reson8/resonant-1`, `reson8/resonant-1-flash`), Applied Brain Research Niagara (`abr-ai/niagara-19m-batch.en`, `abr-ai/niagara-38m-batch.en`), SoundsgoodAI Zipformer XL (`soundsgoodai/Zipformer-transducer-XL-290M`), Boson AI Higgs Audio v3 (`bosonai/higgs-audio-v3-8b-stt-v2`), and Smallest AI Pulse (`smallestai/pulse`).
- **20 May 2026** — Removed Tedlium v3 from main and longform tabs due to license change in original data. Related commit for updated leaderboard results: https://huggingface.co/datasets/hf-audio/open-asr-leaderboard-results/commit/f3ff7c9d583f4beaf908f2b2c18f3055040e515b
- **5 May 2026** — Added 🔒 Private Data tab with benchmarks from Appen Inc. and DataoceanAI (11 datasets covering scripted and conversational speech across US, British, Australian, Canadian, and Indian accents). Private data average WER is now available as a toggleable column in the main leaderboard. Added rank column to show how ordering changes.
"""


def _version_date(vid):
    """Parse a 'DD-MM-YYYY' version id into a datetime, or None (e.g. 'latest')."""
    try:
        return datetime.strptime(vid, "%d-%m-%Y")
    except ValueError:
        return None


def _fmt_changelog_date(dt):
    """'D Month YYYY' with no leading zero on the day (e.g. '5 May 2026')."""
    return f"{dt.day} {dt.strftime('%B %Y')}"


def _build_changelog():
    """Merge the manually written entries with one auto-generated entry per dated
    VERSION (using its label) for any date not already covered manually, newest
    first. This lets a new version be documented from VERSIONS alone."""
    entry_re = re.compile(r"^- \*\*(.+?)\*\*\s*[—–-]\s*(.*)$")
    by_date = {}
    for line in CHANGELOG_MANUAL.strip().splitlines():
        m = entry_re.match(line.strip())
        if m:
            by_date[datetime.strptime(m.group(1).strip(), "%d %B %Y")] = m.group(2)

    for vid, v in VERSIONS.items():
        dt = _version_date(vid)
        if dt is not None and dt not in by_date:
            by_date[dt] = v["label"]

    lines = [f"- **{_fmt_changelog_date(dt)}** — {by_date[dt]}"
             for dt in sorted(by_date, reverse=True)]
    return "\n" + "\n".join(lines) + "\n"


CHANGELOG_TEXT = _build_changelog()


def get_version_choices():
    """Return (label, value) pairs for the version dropdown."""
    return [
        (v["label"] if vid == "latest" else f"({vid}) {v['label']}", vid)
        for vid, v in VERSIONS.items()
    ]


hf_api = HfApi(
    endpoint="https://huggingface.co", 
    token=TOKEN_HUB, 
)

def load_all_info_for_version(version_id):
    """Load all dataset CSVs for a specific version — the main leaderboard,
    multilingual, longform, private (appen/dataocean/voicearena) and
    benchmark-fitting (voxpopuli reference-error + per-split rendering-agreement) data.

    Returns:
        (csv_results, multilingual_csv, longform_csv, appen_csv, dataocean_csv,
         voicearena_csv, voxpopuli_fitting_csv, rendering_fitting_csvs, default_datasets)
    ``voicearena_csv`` is None for versions predating that private set.
    ``rendering_fitting_csvs`` is a {dataset label: csv_path} dict (possibly empty).
    """
    version = VERSIONS.get(version_id)
    if version is None:
        raise ValueError(f"Unknown version: {version_id}")

    eng = version["english_short"]
    lf = version["longform"]
    ap = version["appen"]
    do = version["dataocean"]
    va = version.get("voicearena")  # optional (added in later versions)

    # --- English short-form ---
    # Validate that every default dataset's WER column actually made it into
    # the download (guards against a partial/stale fetch at cold start). The
    # "Private (scripted/conversational)" columns are computed separately
    # from private data and never appear in this CSV, so they're excluded.
    required_wer_cols = {
        f"{d} WER" for d in (version.get("default_datasets") or [])
        if d not in ("Private (scripted)", "Private (conversational)")
    }
    csv_results = _load_version_csv(
        eng, validate=lambda p: _has_all_columns(p, required_wer_cols))

    # --- Multilingual ---
    # Two shapes are supported: a single combined CSV (legacy "multilingual"
    # key) or one CSV per language (french/german/... keys). The latter is
    # returned as a {language_code: csv_path} dict.
    if "multilingual" in version:
        multilingual_csv = _load_version_csv(version["multilingual"])
    else:
        multilingual_csv = {}
        for key, code in MULTILINGUAL_LANGUAGE_KEYS.items():
            if key in version:
                path = _load_version_csv(version[key])
                if path is not None:
                    multilingual_csv[code] = path

    # --- Longform ---
    longform_csv = _load_version_csv(
        lf, validate=lambda p: _has_all_columns(p, LONGFORM_REQUIRED_COLUMNS))

    # --- Private data ---
    appen_csv = _load_version_csv(
        ap, fallback=Path("assets") / "appen_latest.csv",
        validate=lambda p: _has_all_columns(p, APPEN_REQUIRED_COLUMNS))
    dataocean_csv = _load_version_csv(
        do, fallback=Path("assets") / "dataocean_latest.csv",
        validate=lambda p: _has_all_columns(p, DATAOCEAN_REQUIRED_COLUMNS))
    voicearena_csv = _load_version_csv(
        va, validate=lambda p: _has_all_columns(p, VOICEARENA_REQUIRED_COLUMNS)) if va else None

    # --- Benchmark fitting (optional; a single benchmark_fitting repo holds
    #     both the reference-error and per-split rendering-agreement files) ---
    bf = version.get("benchmark_fitting")
    if bf:
        repo, revision = bf.get("repo"), bf.get("revision")
        voxpopuli_fitting_csv = _load_version_csv(
            {"repo": repo, "file": VOXPOPULI_FITTING_FILE, "revision": revision})
        rendering_fitting_csvs = load_rendering_fitting_csvs(repo, revision)
    else:
        voxpopuli_fitting_csv = None
        rendering_fitting_csvs = {}

    version_default_datasets = version.get("default_datasets")
    return csv_results, multilingual_csv, longform_csv, appen_csv, dataocean_csv, voicearena_csv, voxpopuli_fitting_csv, rendering_fitting_csvs, version_default_datasets


# Files inside the benchmark_fitting dataset.
VOXPOPULI_FITTING_FILE = "ref_error_agreement_voxpopuli.csv"
# Per-split "rendering agreement" (spelling-copying) files, mapped to their
# leaderboard dataset labels.
RENDERING_FITTING_FILES = {
    "AMI-Cleaned": "ami_cleaned.csv",
    "Earnings22": "earnings22.csv",
    "Gigaspeech-Cleaned": "gigaspeech_cleaned.csv",
    "LS Clean": "librispeech_test.clean.csv",
    "LS Other": "librispeech_test.other.csv",
    "SPGISpeech": "spgispeech.csv",
    "Voxpopuli-AA-Cleaned": "voxpopuli_cleaned_aa.csv",
    "Voxpopuli": "voxpopuli.csv",
}


def load_rendering_fitting_csvs(repo, revision):
    """Download the per-split rendering-agreement CSVs and return a
    {dataset label: csv_path} dict (only splits that resolved)."""
    result = {}
    for label, filename in RENDERING_FITTING_FILES.items():
        path = _load_version_csv({"repo": repo, "file": filename, "revision": revision})
        if path is not None:
            result[label] = path
    return result


def _load_version_csv(source_cfg, fallback=None, validate=None, max_retries=2):
    """Download a dataset repo at a given revision and return the CSV path.

    ``validate``, if given, is called with the resolved CSV path and must
    return True for it to be accepted. This guards against a cold-start fetch
    landing a partial/stale file (e.g. a CDN race right after the source was
    updated) — on validation failure the download is retried with
    ``force_download`` (bypassing any locally/CDN-cached copy) up to
    ``max_retries`` times before falling back to whatever was resolved."""
    repo = source_cfg.get("repo")
    revision = source_cfg.get("revision")
    file = source_cfg.get("file")

    # Download into a *revision-specific* local dir.
    default_path = repo if revision is None else f"{repo}@{revision}"
    path = source_cfg.get("path", default_path)

    def _download(force_download):
        try:
            if TOKEN_HUB is not None and repo is not None:
                snapshot_download(
                    repo_id=repo,
                    local_dir=path,
                    token=TOKEN_HUB,
                    repo_type="dataset",
                    revision=revision,
                    # Only pull the single CSV we need
                    allow_patterns=[file] if file else None,
                    force_download=force_download,
                )
        except Exception as e:
            print(f"Failed to pull {repo}@{revision}: {e}")

    def _resolve():
        # Prefer the (possibly revision-specific) download dir, then fall back
        # to the plain repo dir — useful for local runs without a token,
        # where only the already-present files exist.
        for candidate_dir in (path, repo):
            csv_path = _resolve_csv(candidate_dir, file)
            if csv_path is not None:
                return csv_path
        return None

    _download(force_download=False)
    csv_path = _resolve()

    attempt = 0
    while (csv_path is None or (validate is not None and not validate(csv_path))) and attempt < max_retries:
        attempt += 1
        print(f"Retrying download for {repo}@{revision} (attempt {attempt}/{max_retries})")
        _download(force_download=True)
        csv_path = _resolve()

    if csv_path is not None:
        return csv_path

    if fallback is not None and Path(fallback).exists():
        return fallback
    return None


def _has_all_columns(csv_path, required_cols):
    """Cheap header-only check that ``csv_path`` has every column in
    ``required_cols``. Used to validate a freshly-downloaded CSV before
    trusting it."""
    if not required_cols:
        return True
    try:
        header_cols = set(pd.read_csv(csv_path, nrows=0).columns)
    except Exception:
        return False
    return required_cols.issubset(header_cols)


def _resolve_csv(directory, filename):
    """Return the CSV Path if it exists, or None."""
    if directory is None:
        return None
    if filename:
        p = Path(directory) / filename
        return p if p.exists() else None
    return None


def is_model_on_hub(model_name, revision="main") -> bool:
    try:
        model_name = model_name.replace(" ","")
        author = model_name.split("/")[0]
        model_id = model_name.split("/")[1]
        if len(author) == 0 or len(model_id) == 0:
            return False, "is not a valid model name. Please use the format `author/model_name`."
    except Exception as e:
        return False, "is not a valid model name. Please use the format `author/model_name`."

    try:
        models = list(hf_api.list_models(author=author, search=model_id))
        matched = [model_name for m in models if m.modelId == model_name]
        if len(matched) != 1:
            return False, "was not found on the hub!"
        else:
            return True, None
    except Exception as e:
        print(f"Could not get the model from the hub.: {e}")
        return False, "was not found on hub!"