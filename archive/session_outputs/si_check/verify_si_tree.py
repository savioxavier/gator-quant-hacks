"""Check the source-invariance tree against what the frozen h234 code reads (h234_lib.stage_state / table_meta /
read_done, h234_s1_features.voice_answers and the model check), without computing any feature statistic or ICC and
without printing feature values. Market data are never touched (GQH_MARKET_DIR is removed before import)."""
import json
import os
import sys
from pathlib import Path

os.environ.pop("GQH_MARKET_DIR", None)
CODE = Path(__file__).resolve().parent.parent / "team_push" / "backtests" / "presser" / "backtest" / "code"
sys.path.insert(0, str(CODE))
import pandas as pd  # noqa: E402

import h234_lib as H  # noqa: E402

ROOT, SI = Path(r"<fedpress-root>"), Path(r"<fedpress-root>_si")
H._MODE["placebo"] = False                      # real mode: placebo stamps in markers/tables raise SystemExit
NEED = ["chair", "chunk_idx", "turn_idx", "qa_idx", "t_start_s", "t_end_s", "dur_s", "identity_frac", "identity_ok",
        "identity_source", "voiced_frac", "arousal", "dominance", "valence", "known_at"]
STRUCT = ["chunk_idx", "turn_idx", "qa_idx", "t_start_s", "t_end_s", "dur_s", "identity_frac", "identity_ok",
          "identity_source", "known_at", "t_end_utc", "presser_id", "meeting_date", "chair", "sample_role"]
FEAT = ["arousal", "dominance", "valence", "voiced_frac", "f0_median_st", "intensity_db", "hnr_db"]

out = {"si_root": str(SI), "si_root_has_meetings": (SI / "meetings").is_dir(), "placebo_json": H.is_placebo(SI),
       "placebo_in_path": "placebo" in str(SI).lower(), "meetings": {}}
for pid in H.SI_MEETINGS:
    r = {}
    r["stage_state_si_voice"] = H.stage_state(SI, pid, "voice")
    d_si, d_or = H.read_done(SI, pid, "voice"), H.read_done(ROOT, pid, "voice")
    for k in ("status", "stage_fingerprint", "code_version", "models", "overrides", "config_hash", "run_id",
              "finished_utc"):
        r[f"done_{k}"] = d_si.get(k)
    r["fingerprint_matches_original"] = d_si.get("stage_fingerprint") == d_or.get("stage_fingerprint")
    r["code_version_matches_original"] = d_si.get("code_version") == d_or.get("code_version")
    r["models_match_original"] = d_si.get("models") == d_or.get("models")
    r["overrides_match_original"] = d_si.get("overrides") == d_or.get("overrides")
    md = H.table_meta(SI, pid, "voice/voice_chunks.parquet")
    r["table_meta"] = {k: md.get(k) for k in ("stage", "presser_id", "run_id", "stage_fingerprint", "code_version",
                                              "models", "config_hash", "created_utc", "latency_s")}
    r["model_prefix_ok"] = {k: all(str(v).startswith(p) for v in [(md.get("models") or {}).get(k)] if v)
                            and bool((md.get("models") or {}).get(k))
                            for k, p in H.EXPECTED_MODELS.items() if k == "audeering_msp_dim"}
    v = H.read_table(SI, pid, "voice/voice_chunks.parquet")
    o = H.read_table(ROOT, pid, "voice/voice_chunks.parquet")
    r["n_rows_si"], r["n_rows_orig"] = len(v), len(o)
    r["missing_needed_columns"] = [c for c in NEED if c not in v.columns]
    r["same_column_set_as_original"] = sorted(v.columns) == sorted(o.columns)
    r["chair_all_powell"] = bool((v.chair.astype(str) == "Powell").all())
    r["known_at_nulls"] = int(v.known_at.isna().sum())
    r["structural_columns_identical"] = {c: bool(v[c].equals(o[c])) for c in STRUCT if c in v.columns}
    r["feature_nonnull_si"] = {c: int(v[c].notna().sum()) for c in FEAT if c in v.columns}
    r["feature_nonnull_orig"] = {c: int(o[c].notna().sum()) for c in FEAT if c in o.columns}
    # only whether the re-encode changed the model input at all (share of rows not bit-identical; no magnitudes)
    r["share_rows_arousal_not_identical"] = round(float((v.arousal.to_numpy() != o.arousal.to_numpy()).mean()), 3)
    r["input_sha256"] = H.sha256(H.mdir(SI, pid) / "voice" / "voice_chunks.parquet")
    out["meetings"][pid] = r
print(json.dumps(out, indent=1, default=str))
