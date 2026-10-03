"""Tests for the text and aggregate stages, the walk-forward stance plan, causal baselines and the dataset
build. No GPU, network, torch or model weights: the classifier is replaced by a keyword fake."""

from __future__ import annotations

import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fedpress import io
from fedpress import manifest as mf
from fedpress import stage as stage_mod
from fedpress.baselines import causal_z
from fedpress.clock import make_anchor, save_anchor, stamp
from fedpress.config import ConfigError, load
from fedpress.nlp import classify, lexicon, split, statement, vectors
from fedpress.stage import run_one
from fedpress.train import labels as lab
from fedpress.train import stance_walkforward as wf

STATEMENT_HTML = """<html><body><div id="article"><div class="heading"><p class="article__time">June 15, 2022</p>
<p class="releaseTime">For release at 2:00 p.m. EDT</p></div><div class="col-xs-12">
<p>Inflation remains elevated. The Committee decided to raise the target range for the federal funds rate.</p>
<p>The Committee anticipates that ongoing increases in the target range will be appropriate.</p>
<p>Voting for the monetary policy action were Jerome H. Powell, Chair; and others.</p>
<p>Implementation Note issued June 15, 2022</p></div></div></body></html>"""

TURNS = [  # speaker, role, is_chair, segment_kind, qa_idx, text
    ("CHAIR POWELL", "chair", True, "opening", -1, "Good afternoon. We decided to raise rates today by a large amount."),
    ("MICHELLE SMITH", "moderator", False, "moderator", -1, "Howard."),
    ("HOWARD SCHNEIDER", "reporter", False, "question", 0, "Will you raise rates again in July or will you cut them?"),
    ("CHAIR POWELL", "chair", True, "answer", 0,
     "We will raise rates further if inflation stays high. I think the labor market is strong. Yes."),
    ("HOWARD SCHNEIDER", "reporter", False, "question", 1, "And the balance sheet?"),
    ("CHAIR POWELL", "chair", True, "answer", 1, "We could cut purchases later--perhaps much later [this year]. "
     "Rates may be lower next year if the economy weakens a lot. The labor market remains very strong today."),
    ("MICHELLE SMITH", "moderator", False, "moderator", -1, "Last question."),
    ("CHAIR POWELL", "chair", True, "closing", -1, "Thank you."),
]


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDPRESS_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("FEDPRESS_CONFIG", raising=False)
    monkeypatch.delenv("FEDPRESS_LM_CSV", raising=False)
    for name in ("text", "aggregate", "turns", "voice", "face"):
        stage_mod._REGISTRY.pop(name, None)  # other test modules register fake stages under these names
    return load(overrides=["aggregate.wait_for=[]"])


# ------------------------------------------------------------------ helpers
def make_meeting(cfg, presser_id: str, words_per_s: float = 2.5) -> mf.Meeting:
    """Turns, words, anchor, statement HTML and done-markers for one fake meeting (upstream of text)."""
    m = mf.select(cfg, presser_id=presser_id)[0]
    paths = io.MeetingPaths.of(cfg, presser_id).ensure()
    t, trows, wrows = 12.0, [], []
    for k, (spk, role, is_chair, kind, qa, text) in enumerate(TURNS):
        toks = split.spoken_tokens(split.normalise(text))
        t0 = t
        for a, b in toks:
            wrows.append({"word_idx": len(wrows), "turn_idx": k, "word": split.normalise(text)[a:b], "matched": True,
                          "t_start_s": t, "t_end_s": t + 0.3})
            t += 1.0 / words_per_s
        trows.append({"turn_idx": k, "speaker": spk, "role": role, "is_chair": is_chair, "segment_kind": kind,
                      "qa_idx": qa, "text": text, "n_words": len(toks), "t_start_s": t0, "t_end_s": t,
                      "clock_source": "asr", "match_frac": 1.0, "timing_ok": True})
        t += 1.0
    anchor = make_anchor(cfg, m, greeting_media_s=12.0)
    save_anchor(paths.dir, anchor)
    for key, rows in (("turns", trows), ("words", wrows)):
        df = stamp(pd.DataFrame(rows), anchor, 30.0)
        for c, v in (("presser_id", m.presser_id), ("meeting_date", m.meeting_date.isoformat()), ("chair", m.chair),
                     ("sample_role", m.sample_role)):
            df[c] = v
        io.write_parquet(df, paths.file(key))
    paths.file("statement_html").write_text(STATEMENT_HTML, encoding="utf-8")
    io.mark_done(paths, "fetch", {"status": "ok", "outputs": ["raw/statement.html"]})
    io.mark_done(paths, "turns", {"status": "ok", "outputs": ["turns/turns.parquet", "turns/words.parquet",
                                                             "turns/anchor.json"],
                                  "notes": {"timing_ok": True, "wer_proxy": 0.1, "greeting_media_s": 12.0}})
    return m


def fake_predict(model_dirs, texts, **kw):
    """hawkish if the sentence says raise/higher, dovish for cut/lower, else neutral."""
    probs = []
    for t in texts:
        low = t.lower()
        h, d = ("raise" in low or "higher" in low), ("cut" in low or "lower" in low)
        probs.append([0.1, 0.8, 0.1] if h and not d else [0.8, 0.1, 0.1] if d and not h else [0.2, 0.2, 0.6])
    lengths = np.array([len(t.split()) + 2 for t in texts])
    return classify.Predictions(["dovish", "hawkish", "neutral"], np.array(probs), lengths, lengths > 256,
                                {"n_models": len(model_dirs), "device": "cpu"})


@pytest.fixture()
def fake_models(monkeypatch):
    from fedpress.stages import text as text_stage

    def resolve(ctx, key):
        if key == "fomc_roberta":
            raise FileNotFoundError("gated: no access")  # cross-check unavailable must not fail the meeting
        if key == "centralbank_roberta":
            return [Path("cbr")], "cbr@test", {}
        return [Path("a"), Path("b")], "chrono_wf:test", {}

    def predict(model_dirs, texts, **kw):
        if model_dirs == [Path("cbr")]:
            p = np.tile([0.3, 0.7], (len(texts), 1))
            ln = np.full(len(texts), 5)
            return classify.Predictions(["negative", "positive"], p, ln, ln > 256, {})
        return fake_predict(model_dirs, texts, **kw)

    monkeypatch.setattr(text_stage, "_resolve", resolve)
    monkeypatch.setattr(classify, "predict", predict)


# ------------------------------------------------------------------ pure helpers
def test_splitter_rules():
    t = split.normalise("Mr. Powell said the U.S. economy grew 2.5 percent. Did it? Jerome H. Powell agreed—yes. "
                        "“Inflation is high.” Done")
    assert [s.text for s in split.split_sentences(t)] == [
        "Mr. Powell said the U.S. economy grew 2.5 percent.", "Did it?", "Jerome H. Powell agreed--yes.",
        '"Inflation is high."', "Done"]
    toks = split.spoken_tokens("We could cut--perhaps [this year] later -- ok.")
    assert len(toks) == 6  # We could cut perhaps later ok. (brackets dropped, dashes split)
    assert split.n_words("3.5 percent -- yes") == 3


def test_statement_paragraphs():
    paras = statement.statement_paragraphs(STATEMENT_HTML, r"^(Voting for|Implementation Note)")
    assert len(paras) == 2 and paras[0].startswith("Inflation remains elevated")


def test_lexicon_and_hedges(tmp_path):
    csv = tmp_path / "lm.csv"
    csv.write_text("Word,Uncertainty,Weak_Modal,Negative\nMAYBE,2009,2009,0\nUNCERTAIN,2009,0,0\nWEAK,0,0,-2020\n")
    lm = lexicon.LMDictionary.load(csv, ["Uncertainty", "WeakModal", "Negative"])
    assert lm.counts(lexicon.words("Maybe it is uncertain, weak.")) == {"uncertainty": 2, "weakmodal": 1, "negative": 0}
    h = lexicon.HedgeMatcher(["i think", "i think that", "perhaps"])
    assert h.count(lexicon.words("I think that perhaps I think so")) == 3
    assert lexicon.tdw_filter("Monetary policy is tight") and not lexicon.tdw_filter("Good afternoon")


def test_vectors_novelty():
    a = vectors.hashed_tf("inflation remains elevated and rates rise")
    assert vectors.novelty(a, a) == pytest.approx(0.0)
    assert vectors.novelty(a, vectors.hashed_tf("baseball tickets weekend")) == pytest.approx(1.0)
    assert vectors.hashed_tf("the and of") == {}
    idx, val = vectors.to_lists(a)
    assert vectors.from_lists(idx, val) == a


# ------------------------------------------------------------------ walk-forward stance plan
def test_walkforward_years_and_keys(cfg):
    assert wf.key_for_year(cfg, 2016, 2022) == ("b2015_l2015", 2015, 2015)
    assert wf.key_for_year(cfg, 2023, 2022) == ("b2022_l2022", 2022, 2022)
    assert wf.key_for_year(cfg, 2025, 2022)[0] == wf.key_for_year(cfg, 2026, 2022)[0] == "b2024_l2022"
    with pytest.raises(ConfigError):
        wf.key_for_year(cfg, 2010, 2022)  # needs a 2009 checkpoint
    jobs = wf.plan(cfg, wf.sample_years(cfg), 2022)
    assert {j.seed for j in jobs} == {42, 43, 44}
    keys = sorted({j.key for j in jobs})
    assert keys[0] == "b2015_l2015" and keys[-1] == "b2024_l2022" and len(keys) == 10
    assert all(j.label_end < min(j.test_years) for j in jobs)  # labels strictly before every test year


def test_stratified_split():
    y = [0] * 40 + [1] * 20 + [2] * 60
    tr, va = wf.stratified_split(y, 0.15, 0)
    assert not set(tr) & set(va) and len(tr) + len(va) == 120
    assert [sum(y[i] == c for i in va) for c in (0, 1, 2)] == [6, 3, 9]
    assert wf.stratified_split(y, 0.15, 0) == (tr, va)


def _xlsx(path: Path, rows: list[list[str]]) -> None:
    shared = sorted({c for r in rows for c in r})
    sst = "".join(f"<si><t>{s}</t></si>" for s in shared)
    cells = "".join(f'<row r="{i + 1}">' + "".join(
        f'<c r="{chr(65 + j)}{i + 1}" t="s"><v>{shared.index(c)}</v></c>' for j, c in enumerate(r)) + "</row>"
        for i, r in enumerate(rows))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>{sst}</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{cells}</sheetData></worksheet>")


def test_labels_build(cfg, tmp_path, monkeypatch):
    x = tmp_path / "pc.xlsx"
    _xlsx(x, [["sentence", "year", "label"], ["Rates will rise.", "2019", "1"], ["Unlabelled.", "2019", "-"]])
    assert lab.read_xlsx(x)[0] == {"sentence": "Rates will rise.", "year": "2019", "label": "1"}
    hf = [{"sentence": "Rates will rise.", "label": 1, "year": 2019, "doc_type": "unknown", "source": "hf:train.csv"},
          {"sentence": "Growth is slow.", "label": 0, "year": 2015, "doc_type": "unknown", "source": "hf:train.csv"},
          {"sentence": "Growth is  slow.", "label": 2, "year": 2015, "doc_type": "unknown", "source": "hf:test.csv"},
          {"sentence": "Prices are stable.", "label": 2, "year": 2021, "doc_type": "unknown", "source": "hf:test.csv"}]
    gh = [{"sentence": "Rates will rise.", "label": 1, "year": 2019, "doc_type": "pc", "source": "github:pc"}]
    monkeypatch.setattr(lab, "_hf_rows", lambda cfg, src, fm: [dict(r) for r in hf])
    monkeypatch.setattr(lab, "_github_rows", lambda cfg, src, fm: [dict(r) for r in gh])
    plain = load(overrides=["train.stance_walkforward.data.redate.enabled=false"])
    lab.build(plain)
    df, meta = lab.load(plain)
    assert meta["conflicting_keys_dropped"] == 1 and len(df) == 2  # 'Growth is slow.' has two labels -> dropped
    assert df.set_index("sentence").loc["Rates will rise.", "doc_type"] == "pc"
    assert meta["max_year"] == 2021 and meta["year_basis"] == "dataset_year"
    with pytest.raises(FileNotFoundError, match="D1a"):  # the default config refuses labels without re-dating
        lab.load(cfg)


def test_labels_redate_d1a(cfg, monkeypatch):
    """D1a: year = source-document year from manifest/label_dates.parquet; undated rows only for 2023+ models."""
    import pandas as pd

    t = pd.read_parquet(cfg.pkg_path("manifest/label_dates.parquet"))
    moved = t[(t["dataset_year"] <= 2012) & (pd.to_datetime(t["source_date"]).dt.year >= 2019)].iloc[0]
    hf = [{"sentence": str(moved["sentence"]), "label": int(moved["label"]), "year": int(moved["dataset_year"]),
           "doc_type": "unknown", "source": "hf:train.csv"},
          {"sentence": "A sentence that no source document contains.", "label": 1, "year": 2005,
           "doc_type": "unknown", "source": "hf:test.csv"}]
    monkeypatch.setattr(lab, "_hf_rows", lambda cfg, src, fm: [dict(r) for r in hf])
    monkeypatch.setattr(lab, "_github_rows", lambda cfg, src, fm: [])
    lab.build(cfg, force=True)
    df, meta = lab.load(cfg)
    row = df[df["dataset_year"] == int(moved["dataset_year"])].iloc[0]
    assert row["year"] == pd.Timestamp(moved["source_date"]).year and row["doc_type"] == moved["source_type"]
    assert df.set_index("dataset_year").loc[2005, "year"] == 2022  # undated: never in a model for 2015-2022
    assert meta["year_basis"] == "source_date" and meta["redate"]["dated"] == 1 and meta["redate"]["undated"] == 1
    tbl = t.assign(sy=pd.to_datetime(t["source_date"]).dt.year)
    assert (tbl["sy"] != tbl["dataset_year"]).sum() == 2336 and tbl["source_date"].notna().all()


# ------------------------------------------------------------------ text stage
def test_text_stage(cfg, fake_models):
    m = make_meeting(cfg, "20220615")
    assert run_one(cfg, "text", m, run_id="t") == "done"
    paths = io.MeetingPaths.of(cfg, m.presser_id)
    sents, units = io.read_parquet(paths.file("text_sentences")), io.read_parquet(paths.file("text_units"))
    assert set(units["unit"]) == {"statement", "answer", "question"}  # opening and closing not scored
    st = units[units["unit"] == "statement"].iloc[0]
    assert st["known_at"] == pd.Timestamp(m.statement_utc) + pd.Timedelta(seconds=30)
    # 'Inflation remains elevated.' has 3 words (excluded); 'raise' hawkish; 'ongoing increases' neutral
    assert st["n_sentences"] == 3 and st["n_included"] == 2 and st["hawk"] == pytest.approx(0.5)
    a0 = units[(units["unit"] == "answer")].sort_values("turn_idx").iloc[0]
    # 'We will raise ...' hawkish, 'I think ...' neutral, 'Yes.' excluded (< 4 words)
    assert a0["n_sentences"] == 3 and a0["n_included"] == 2 and a0["hawk"] == pytest.approx(0.5)
    assert a0["cwf_hawk_prob"] == pytest.approx(((0.8 - 0.1) + 0.0) / 2)
    assert a0["hedge_count"] == 1 and a0["cbr_sentiment"] == pytest.approx(0.4)
    assert 0 <= a0["nov_stmt_lex"] <= 1 and bool(a0["in_classifier_train"]) is False
    assert "fomc_hawk_share" not in units.columns  # gated cross-check recorded as unavailable
    ans_s = sents[sents["unit"] == "answer"]
    assert (ans_s["time_method"] == "words").all()
    assert (ans_s["known_at"] == ans_s["t_end_utc"] + pd.Timedelta(seconds=30)).all()
    turn = io.read_parquet(paths.file("turns")).set_index("turn_idx")
    last = ans_s[ans_s["turn_idx"] == 3]["t_end_s"].max()
    assert last <= turn.loc[3, "t_end_s"] + 1e-9
    done = io.read_done(paths, "text")
    assert done["notes"]["models"]["fomc_roberta"]["available"] is False
    assert io.read_parquet(paths.file("text_vectors"))["tf_idx"].map(len).gt(0).all()


def test_text_primary_missing_fails(cfg, monkeypatch):
    from fedpress.stages import text as text_stage

    m = make_meeting(cfg, "20220615")
    monkeypatch.setattr(text_stage, "_resolve", lambda ctx, key: (_ for _ in ()).throw(FileNotFoundError("no model")))
    assert run_one(cfg, "text", m, run_id="t") == "failed"


# ------------------------------------------------------------------ aggregate stage
def _voice_face(cfg, m):
    paths = io.MeetingPaths.of(cfg, m.presser_id)
    turns = io.read_parquet(paths.file("turns"))
    anchor = make_anchor(cfg, m, greeting_media_s=12.0)
    v, f = [], []
    for r in turns[turns["segment_kind"] == "answer"].itertuples():
        for k, t in enumerate(np.arange(r.t_start_s + 3, r.t_end_s, 3.0)):
            v.append({"chunk_idx": len(v), "turn_idx": r.turn_idx, "qa_idx": r.qa_idx, "t_start_s": t - 3,
                      "t_end_s": t, "dur_s": 3.0, "arousal": 0.5 + 0.1 * k, "dominance": 0.4, "valence": 0.9,
                      "identity_ok": k != 1})
            f.append({"frame_idx": len(f), "turn_idx": r.turn_idx, "qa_idx": r.qa_idx, "t_start_s": t, "t_end_s": t,
                      "ex_valence": 0.2, "bs_browInnerUp": 0.3, "yaw_deg": 5.0, "gate_ok": True, "identity_ok": True})
    for key, rows, st in (("voice_chunks", v, "voice"), ("face_frames", f, "face")):
        df = stamp(pd.DataFrame(rows), anchor, 30.0)
        io.write_parquet(df, paths.file(key))
        io.mark_done(paths, st, {"status": "ok", "outputs": [io.FILES[key]]})


def test_aggregate_stage(cfg, fake_models):
    m = make_meeting(cfg, "20220615")
    assert run_one(cfg, "text", m, run_id="t") == "done"
    _voice_face(cfg, m)
    assert run_one(cfg, "aggregate", m, run_id="t") == "done"
    paths = io.MeetingPaths.of(cfg, m.presser_id)
    ans = io.read_parquet(paths.file("answers")).sort_values("t_end_s")
    assert list(ans["turn_idx"]) == [3, 5] and (ans["segment_kind"] == "answer").all()
    assert ans["hawk_gap"].iloc[0] == pytest.approx(ans["hawk"].iloc[0] - ans["hawk_statement"].iloc[0])
    # A-10 sentence weights: answer 1 = hawkish + neutral, answer 2 = dovish, dovish, neutral
    assert ans["hawk"].tolist() == pytest.approx([0.5, -2 / 3])
    assert ans["hawk_qa_running"].iloc[0] == pytest.approx(0.5)  # only the answers that have ended
    assert ans["hawk_qa_running"].iloc[1] == pytest.approx((1 - 2) / 5)
    assert ans["question_turn_idx"].tolist() == [2, 4]
    assert "voice_valence" not in ans.columns and ans["voice_n_chunks"].iloc[0] >= 1  # A-31: valence excluded
    assert (ans["known_at"] == ans["t_end_utc"] + pd.Timedelta(seconds=30)).all()
    meet = io.read_parquet(paths.file("meeting")).iloc[0]
    assert meet["h1_weighting"] == "sentence" and meet["hawk_qa_sent"] == pytest.approx(-0.2)
    assert meet["h1_gap"] == pytest.approx(-0.2 - meet["hawk_statement"])
    assert meet["hawk_qa_answer_mean"] == pytest.approx(ans["hawk"].mean())
    cfg_a = load(overrides=["aggregate.wait_for=[]", "aggregate.h1_weighting=answer"])
    assert run_one(cfg_a, "aggregate", m, run_id="t", force=True) == "done"
    meet_a = io.read_parquet(paths.file("meeting")).iloc[0]
    assert meet_a["h1_gap"] == pytest.approx(ans["hawk"].mean() - meet_a["hawk_statement"])
    assert run_one(cfg, "aggregate", m, run_id="t", force=True) == "done"
    assert meet["t_end_s"] == pytest.approx(ans["t_end_s"].max()) and meet["turns_timing_ok"]
    win = io.read_parquet(paths.file("windows"))
    assert set(win["window_s"]) == {30.0, 60.0}
    assert (win["t_end_s"] - win["t_start_s"]).round(6).isin([30.0, 60.0]).all()
    assert (win["known_at"] == win["t_end_utc"] + pd.Timedelta(seconds=30)).all()
    assert (win["chair_speech_s"] <= win["window_s"] + 1e-9).all()


def test_aggregate_waits_for_pending_voice(cfg, fake_models):
    m = make_meeting(cfg, "20220615")
    assert run_one(cfg, "text", m, run_id="t") == "done"
    cfg2 = load(overrides=["aggregate.wait_for=[voice]"])
    assert run_one(cfg2, "aggregate", m, run_id="t") == "failed"  # voice pending for a Powell meeting
    io.mark_done(io.MeetingPaths.of(cfg, m.presser_id), "voice", {"status": "not_applicable", "outputs": []})
    assert run_one(cfg2, "aggregate", m, run_id="t") == "done"


# ------------------------------------------------------------------ baselines and dataset
def test_causal_z_uses_only_earlier_meetings():
    rows = []
    for k in range(7):
        for j in range(3):
            rows.append({"presser_id": f"m{k}", "chair": "Powell", "x": float(10 * k + j), "known_at": k})
    rows.append({"presser_id": "w0", "chair": "Warsh", "x": 100.0, "known_at": 99})
    df = pd.DataFrame(rows)
    z = causal_z(df, ["x"], burn_in=4, robust=False)
    assert z.loc[z["presser_id"].isin(["m0", "m1", "m2", "m3", "w0"]), "z_x"].isna().all()
    prior = df[df["presser_id"].isin(["m0", "m1", "m2", "m3"])]["x"]
    m4 = z[z["presser_id"] == "m4"]
    assert m4["z_x"].iloc[0] == pytest.approx((40.0 - prior.mean()) / prior.std(ddof=1))
    assert m4["baseline_n_meetings"].iloc[0] == 4
    # changing a later meeting never changes an earlier z
    df2 = df.copy()
    df2.loc[df2["presser_id"] == "m6", "x"] = 1e6
    z2 = causal_z(df2, ["x"], burn_in=4, robust=False)
    pd.testing.assert_series_equal(z.loc[z["presser_id"] != "m6", "z_x"], z2.loc[z2["presser_id"] != "m6", "z_x"])
    # an explicit order is respected
    zr = causal_z(df, ["x"], burn_in=1, order=[f"m{k}" for k in reversed(range(7))])
    assert zr.loc[zr["presser_id"] == "m6", "z_x"].isna().all() and zr.loc[zr["presser_id"] == "m0", "z_x"].notna().all()


def test_dataset_build(cfg, fake_models):
    ms = [make_meeting(cfg, pid) for pid in ("20220504", "20220615")]
    for m in ms:
        assert run_one(cfg, "text", m, run_id="t") == "done"
        assert run_one(cfg, "aggregate", m, run_id="t") == "done"
    from fedpress.stages.aggregate import finalize
    from fedpress.log import Log

    written = finalize(cfg, ms, Log("test"))
    names = {Path(p).name for p in written}
    assert {"answers.parquet", "meetings.parquet", "windows.parquet", "text_units.parquet"} <= names
    ans = pd.read_parquet(cfg.root_path("panel") / "answers.parquet")
    assert not ans["calibration_only"].any() and ans["in_study"].all()
    second = ans[ans["presser_id"] == "20220615"]
    assert (second["prev_presser_id"] == "20220504").all()
    assert second["nov_prev_lex"].between(0, 1).all()  # one answer vs the previous presser's pooled answers
    first = ans[ans["presser_id"] == "20220504"]
    assert first["nov_prev_lex"].isna().all()  # previous presser (20220316) has no outputs -> NaN, not older
    meets = pd.read_parquet(cfg.root_path("panel") / "meetings.parquet")
    assert len(meets) == 88 and meets["h1_gap"].notna().sum() == 2  # the team plan's 88-meeting calendar
    row = meets.set_index("presser_id").loc["20220615"]
    assert row["nov_prev_lex"] == pytest.approx(0.0) and row["stmt_nov_prev_lex"] == pytest.approx(0.0)  # same text
    z = pd.read_parquet(cfg.root_path("panel") / "answers_causal_z.parquet")
    assert "baseline_n_meetings" in z.columns and z["baseline_n_meetings"].max() == 1
