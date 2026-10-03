"""Step 3b: frozen gtfintechlab/FOMC-RoBERTa on every sentence unit (answers, questions, opening, statements).

Model: gtfintechlab/FOMC-RoBERTa (Shah, Paturi, Chava, ACL 2023), RoBERTa-large, 3-way sentence classifier.
License CC BY-NC 4.0 (research use; disclose). The Hugging Face repo is gated (manual approval by the authors).
Pinned: revision aa3bc4281fb1fe73c8872e09ad5c64b898f90d83, pytorch_model.bin sha256
c7f49f8b3049d0a446e0e4ac5c5e161f2dc2d8834806c7b9b75a4399226c280a (from the Hub LFS metadata, read 2026-10-03).
Label mapping per the authors' README: LABEL_0 = dovish, LABEL_1 = hawkish, LABEL_2 = neutral. The run does not
trust it blindly: unambiguous test sentences must come out as expected, or the run aborts without writing scores.

Run (after access is granted and `hf auth login` has been done by the account holder):
    <venv>/python.exe score_roberta.py        # writes sentence_labels.parquet + rob_meta.json
    <venv>/python.exe build.py                # rebuilds answers.parquet / meetings.parquet with the scores
No fine-tuning, no thresholds: label = argmax of the softmax; fp32; truncation at 512 tokens.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1]
MODEL_ID = "gtfintechlab/FOMC-RoBERTa"
MODEL_REV = "aa3bc4281fb1fe73c8872e09ad5c64b898f90d83"
MODEL_BIN_SHA256 = "c7f49f8b3049d0a446e0e4ac5c5e161f2dc2d8834806c7b9b75a4399226c280a"
LABELS = {0: "dove", 1: "hawk", 2: "neut"}
MAX_LEN = 512

# unambiguous sentences used only to verify the label mapping (never scored as data)
SANITY = [
    ("The Committee decided to raise the target range for the federal funds rate to 5-1/4 to 5-1/2 percent.", "hawk"),
    ("Inflation is far too high, and we will keep raising interest rates until it comes down.", "hawk"),
    ("Such a directive would imply that any tightening should be implemented promptly if developments were "
     "perceived as pointing to rising inflation.", "hawk"),
    ("The Committee decided to lower the target range for the federal funds rate to 0 to 1/4 percent.", "dove"),
    ("We will cut interest rates and expand asset purchases to support employment.", "dove"),
    ("The Committee decided to increase its holdings of Treasury securities by at least $500 billion.", "dove"),
    ("The meeting adjourned at 11:00 a.m.", "neut"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(sentences, tok, model, device, batch_size=128) -> np.ndarray:
    import torch
    order = np.argsort([len(s) for s in sentences])[::-1]
    probs = np.zeros((len(sentences), 3), dtype=np.float32)
    with torch.inference_mode():
        for k in range(0, len(order), batch_size):
            idx = order[k:k + batch_size]
            enc = tok([sentences[i] for i in idx], padding=True, truncation="only_first", max_length=MAX_LEN,
                      return_tensors="pt").to(device)
            probs[idx] = torch.softmax(model(**enc).logits.float(), dim=-1).cpu().numpy()
    return probs


def main() -> None:
    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    t0 = time.time()
    try:
        p = Path(hf_hub_download(MODEL_ID, "pytorch_model.bin", revision=MODEL_REV))
    except Exception as e:  # gated repo without approved login
        status = {"status": "blocked", "error_type": type(e).__name__, "error": str(e).splitlines()[0][:300],
                  "when": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        (OUT / "rob_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        sys.exit(2)
    got = sha256(p)
    if got != MODEL_BIN_SHA256:
        raise SystemExit(f"weights sha256 mismatch: {got}")
    dev = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REV, do_lower_case=True, do_basic_tokenize=True)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=MODEL_REV, num_labels=3,
                                                               use_safetensors=False).to(dev).eval()
    pr = classify([s for s, _ in SANITY], tok, model, dev)
    sanity = [{"sentence": s, "expected": e, "got": LABELS[int(np.argmax(q))],
               "probs_dove_hawk_neut": [round(float(x), 4) for x in q]} for (s, e), q in zip(SANITY, pr)]
    ok_hd = all(r["got"] == r["expected"] for r in sanity if r["expected"] in ("hawk", "dove"))
    if not ok_hd:
        (OUT / "rob_sanity_failed.json").write_text(json.dumps(sanity, indent=2), encoding="utf-8")
        raise SystemExit("label-mapping check failed; nothing scored (see rob_sanity_failed.json)")

    S = pd.read_parquet(OUT / "sentences.parquet")
    t1 = time.time()
    probs = classify(S.sentence.tolist(), tok, model, dev)
    t2 = time.time()
    S["label"] = [LABELS[int(k)] for k in probs.argmax(1)]
    S["p_dove"], S["p_hawk"], S["p_neut"] = probs[:, 0], probs[:, 1], probs[:, 2]
    S[["unit_id", "label", "p_dove", "p_hawk", "p_neut"]].to_parquet(OUT / "sentence_labels.parquet", index=False)
    meta = {"status": "scored", "model": MODEL_ID, "revision": MODEL_REV, "weights_sha256": got,
            "config_id2label": getattr(model.config, "id2label", {}), "label_mapping_used": LABELS,
            "device": torch.cuda.get_device_name(0) if dev.type == "cuda" else "cpu", "torch": torch.__version__,
            "precision": "fp32", "max_len": MAX_LEN, "n_units": int(len(S)), "classify_sec": round(t2 - t1, 1),
            "total_sec": round(time.time() - t0, 1), "sanity": sanity}
    (OUT / "rob_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    (OUT / "rob_status.json").write_text(json.dumps({"status": "scored"}, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "sanity"}, indent=2, default=str))


if __name__ == "__main__":
    main()
