"""Read-only diagnosis: execute the frozen h234_s1_features.py source up to the per-meeting QA table (no market data)
and print the QA columns. Writes only into H234_OUT_DIR (a scratch folder)."""
import os, sys
CODE = os.environ["H234_CODE"]
sys.path.insert(0, CODE)
os.chdir(CODE)
src = open(os.path.join(CODE, "h234_s1_features.py"), encoding="utf-8").read()
cut = src.index("qa = pd.DataFrame(qa_rows)")
g = {"__name__": "diag", "__file__": os.path.join(CODE, "h234_s1_features.py")}
exec(compile(src[:cut], "h234_s1_features.py[diag]", "exec"), g)
import pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
qa = pd.DataFrame(g["qa_rows"])
cols = ["presser_id", "drop_timing", "turns_state", "clock_source", "vtt_median_offset_s", "vtt_ok", "wav_duration_s",
        "label_video_duration_s", "wav_gap_s", "wav_ok", "qa_ok", "diarize_state", "voice_state", "face_state",
        "n_caption_answers", "h2_ok", "h2_exclusion", "h3_ok", "h3_exclusion"]
print(qa[[c for c in cols if c in qa.columns]].to_string())
print("h2_ok", int(qa.h2_ok.sum()), "h3_ok", int(qa.h3_ok.sum()))
A = pd.concat(g["ans_tabs"], ignore_index=True)
print("answers rows", len(A), "columns", list(A.columns))
for c in ["nV", "A_raw", "nF", "BD_raw"]:
    if c in A.columns:
        print(c, "finite", int(pd.to_numeric(A[c], errors="coerce").notna().sum()))
