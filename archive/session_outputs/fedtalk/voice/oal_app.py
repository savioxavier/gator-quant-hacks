import gradio as gr
import pandas as pd
from pathlib import Path
from constants import BANNER, INTRODUCTION_TEXT, CITATION_TEXT, METRICS_TAB_TEXT, LEADERBOARD_CSS, LANGUAGES, MULTILINGUAL_TAB_TEXT, LONGFORM_TAB_TEXT, PRIVATE_DATA_TAB_TEXT, TTS_PROMO_BANNER
from init import load_all_info_for_version, get_version_choices, LATEST_VERSION, CHANGELOG_TEXT
from utils_display import make_clickable_model
import numpy as np
import plotly.graph_objects as go
import re
import json

gr.set_static_paths(paths=["assets"])

# Extract the most recent date from the changelog (first bold date entry)
_changelog_date_match = re.search(r"\*\*(.+?)\*\*", CHANGELOG_TEXT)
LAST_UPDATED = _changelog_date_match.group(1) if _changelog_date_match else "19 April 2026"

# Multilingual benchmark data, populated by build_multilingual_data().
# Structure:
#   MULTI["codes"]         -> ordered list of language codes present in the data
#   MULTI["lang_datasets"] -> {code: [dataset display name, ...]} for that language
#   MULTI["details"]       -> {model: {code: {"avg": float|"NA",
#                                             "datasets": {dataset name: float},
#                                             "rtfx": float|"NA"}}}
#   MULTI["html"]          -> {model: clickable HTML}
#   MULTI["display"]       -> {code: "🇩🇪 German"}
#   MULTI["display_to_code"] -> reverse of display
MULTI = {}
OVERVIEW_LABEL = "Language averages"
DATASET_DISPLAY = {"covost": "CoVoST", "mls": "MLS", "fleurs": "FLEURS"}
# Display-name overrides for per-language datasets, applied after the ' WER'
# suffix is stripped (e.g. Hindi's 'Monsoon' set is VoiceArena's).
PER_LANGUAGE_DATASET_DISPLAY = {"Monsoon": "Voice Arena Monsoon"}

# Synthetic "language" in the multilingual views whose scores come from the
# main English leaderboard. Off by default in the language selectors.
ENGLISH_CODE = "en"
ENGLISH_DISPLAY = "🇬🇧 English"

# VoiceArena private Hindi set: a column in the voicearena CSV surfaced as an
# extra dataset in the Hindi breakdown and folded into the Hindi average.
HINDI_CODE = "hi"
HINDI_PRIVATE_CSV_COLUMN = "HF_Hindi_Private_Set"
HINDI_PRIVATE_DISPLAY = "Voice Arena Private"

# Armenian: off by default in the language selectors, like English.
ARMENIAN_CODE = "hy"

# Medals for the top-3 models in each performance column.
MEDAL_ICONS = ["🥇", "🥈", "🥉"]
# Columns that never get medals (rank, model, coverage, ranking-delta,
# metadata). Average WER, per-dataset, per-language and RTFx columns get medals.
MEDAL_SKIP_COLS = {
    "Rank", "Model", "model", "Rank Δ", "Coverage",
    "License", "Size (B)", "# Languages", "Encoder", "Decoder",
}
# Every table builds its datatype per-render via _style_table so
# performance columns keep a "number" type and thus sort numerically, while
# medals are shown via a pandas Styler (display-only, leaving the value numeric).

column_names = {
    "MODEL": "Model",
    "RTFx": "RTFx ⬆️️",
    "AMI WER": "AMI",
    "AMI-Cleaned WER": "AMI-Cleaned",
    "Earnings22 WER": "Earnings22",
    "Earnings22-Cleaned-AA-chunked WER": "Earnings22-Cleaned-AA-chunked",
    "Gigaspeech WER": "Gigaspeech",
    "Gigaspeech-Cleaned WER": "Gigaspeech-Cleaned",
    "LS Clean WER": "LS Clean",
    "LS Other WER": "LS Other",
    "SPGISpeech WER": "SPGISpeech",
    "Voice Arena Monsoon WER": "Voice Arena Monsoon",
    "Voxpopuli WER": "Voxpopuli",
    "Voxpopuli-AA-Cleaned WER": "Voxpopuli-AA-Cleaned",
}
always_visible = ["model", "Average WER ⬇️", "Rank Δ"]

AUDIO_LM_MODELS = {
    "nvidia/canary-qwen-2.5b",
    "mistralai/Voxtral-Small-24B-2507",
    "mistralai/Voxtral-Mini-3B-2507",
    "microsoft/VibeVoice-ASR-HF",
    "ibm-granite/granite-speech-4.1-2b",
    "ibm-granite/granite-4.0-1b-speech",
    "ibm-granite/granite-speech-3.3-8b",
    "ibm-granite/granite-speech-3.3-2b",
    "microsoft/Phi-4-multimodal-instruct",
}

METADATA_COLUMNS = {
    "Model",
    "License",
    "Size (B)",
    "# Languages",
    "Encoder",
    "Decoder",
}

AVG_COLUMNS = {
    "Average WER ⬇️",
    "RTFx ⬆️️",
    "Rank Δ",
}

# Total audio duration per public split, in seconds. Constants of the datasets,
# so they are the same for every model. Keyed by the leaderboard display name
# (matching the "<split> WER"/"<split> RTFx" CSV columns). Used to recompute the
# pooled RTFx over a subset of splits:
#     pooled = sum(d[i] for i in sel) / sum(d[i] / rtfx[i] for i in sel)
SPLIT_DURATIONS_S = {
    "AMI-Cleaned":                    28727.6,
    "Earnings22-Cleaned-AA-chunked":   6900.9,
    "Gigaspeech-Cleaned":            126515.2,
    "LS Clean":                       19452.5,
    "LS Other":                       19229.6,
    "SPGISpeech":                     360007.5,
    "Voice Arena Monsoon":            20247.6,
    "Voxpopuli-AA-Cleaned":            7122.4,
}

EXCLUDED_AVG_COLS = METADATA_COLUMNS | AVG_COLUMNS

# Private aggregate WER columns (added onto the leaderboard from the private data).
PRIVATE_DATA_COLUMNS = {"Private (scripted)", "Private (conversational)"}
# Recognized per-dataset WER columns that can be averaged / toggled (the mapped
# dataset display names plus the private aggregates). Excludes model, RTFx,
# aggregates and metadata.
DATASET_COLUMNS = (set(column_names.values()) - {"Model", "RTFx ⬆️️"}) | PRIVATE_DATA_COLUMNS
# Everything allowed to appear as a toggleable leaderboard column: recognized
# datasets, RTFx and model metadata. Any other CSV column (e.g. 'avg',
# 'Training data disclosure') is ignored rather than shown as a toggle.
KNOWN_LEADERBOARD_COLUMNS = DATASET_COLUMNS | METADATA_COLUMNS | {"RTFx ⬆️️"}
LEGACY_UNCLEANED_DATASETS = {"AMI", "Earnings22", "Gigaspeech", "Voxpopuli"}


def _toggleable_columns(columns, known_datasets):
    """Columns eligible as a leaderboard toggle, given the active version's
    default_datasets (``known_datasets``) — excludes the legacy uncleaned
    datasets unless that version still defaults to them."""
    return [c for c in columns if c in KNOWN_LEADERBOARD_COLUMNS and c not in always_visible
            and (c not in LEGACY_UNCLEANED_DATASETS or c in known_datasets)]


# Main-leaderboard columns rendered as numbers (so they sort numerically) with a
# medal shown only in the displayed text (via a Styler). Every per-dataset WER,
# the aggregate WER and RTFx.
NUMERIC_SORT_COLS = DATASET_COLUMNS | {"Average WER ⬇️", "RTFx ⬆️️"}

csv_results, multilingual_csv_path, longform_csv_path, appen_csv_path, dataocean_csv_path, voicearena_csv_path, voxpopuli_fitting_csv_path, rendering_fitting_csv_paths, default_datasets = load_all_info_for_version(LATEST_VERSION)

if not csv_results.exists():
    raise Exception(f"CSV file {csv_results} does not exist locally")
# Get csv with data and parse columns
original_df = pd.read_csv(csv_results)


def _compute_average_wer_from_default_datasets(df):
    """Compute Average WER from the default leaderboard datasets."""
    df = df.copy()
    wer_cols = [c for c in default_datasets if c in df.columns]

    if wer_cols:
        def compute_avg(row):
            values = []
            for col in wer_cols:
                value = row[col]
                if value == "NA" or value is None:
                    return "NA"
                try:
                    values.append(float(value))
                except (TypeError, ValueError):
                    return "NA"
            return round(np.mean(values), 2) if values else "NA"

        df["Average WER ⬇️"] = df.apply(compute_avg, axis=1)
    else:
        df["Average WER ⬇️"] = "NA"

    return df

# Formats the columns
def formatter(x, col=None):
    # Special rule for "# Languages"
    if col == "# Languages":
        try:
            if pd.isna(x) or str(x).strip() in ["", "0", "0.0", "-1", "NA"]:
                return 1
            return int(float(x))  # safer conversion
        except (ValueError, TypeError):
            return 1  # fallback if anything unexpected

    # RTFx: keep it numeric so the leaderboard column sorts numerically (not
    # lexicographically). API-only services with no reported throughput
    # (missing / -1 / non-positive) become -1 so they sort to the bottom.
    if col in ("RTFx", "RTFx ⬆️️"):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return -1
        return round(v, 2) if not pd.isna(v) and v > 0 else -1

    # Generic NA handling
    if x is None or pd.isna(x) or str(x).strip() in ["", "0", "0.0", "-1"]:
        return "NA"

    # Keep strings
    if isinstance(x, str):
        return x

    # Numeric
    return round(x, 2)


def _format_medal_number(v):
    """Render a numeric WER/RTFx value as a compact string (drops a trailing .0)."""
    v = round(float(v), 2)
    return str(int(v)) if v == int(v) else str(v)


for col in original_df.columns:
    if col == "model":
        original_df[col] = original_df[col].apply(lambda x: x.replace(x, make_clickable_model(x)))
    else:
        original_df[col] = original_df[col].apply(lambda x: formatter(x, col))
original_df.rename(columns=column_names, inplace=True)
if "Avg. WER" in original_df.columns:
    original_df = original_df.drop(columns=["Avg. WER"])
for _drop_col in ["avg cleaned", "avg original"]:
    if _drop_col in original_df.columns:
        original_df = original_df.drop(columns=[_drop_col])
original_df = _compute_average_wer_from_default_datasets(original_df)
original_df = original_df.sort_values(by='Average WER ⬇️', key=lambda col: pd.to_numeric(col, errors="coerce"), na_position="last")

# Dataset classification for private data
APPEN_SCRIPTED = ["Scripted-US", "Scripted-AU", "Scripted-CA", "Scripted-IN"]
APPEN_CONVERSATIONAL = ["Conversational-US003", "Conversational-US004", "Conversational-IN"]
APPEN_US = ["Scripted-US", "Conversational-US003", "Conversational-US004"]
APPEN_NON_US = ["Scripted-AU", "Scripted-CA", "Scripted-IN", "Conversational-IN"]

DATAOCEAN_SCRIPTED = ["Scripted-US", "Scripted-GB"]
DATAOCEAN_CONVERSATIONAL = ["Conversational-US", "Conversational-GB"]
DATAOCEAN_US = ["Scripted-US", "Conversational-US"]
DATAOCEAN_NON_US = ["Scripted-GB", "Conversational-GB"]

# VoiceArena: a single English conversational, non-US set. Only its
# HF_English_Private_Set column feeds the conversational and non-US
# group averages (not the scripted or US groups).
VOICEARENA_CONVERSATIONAL = ["HF_English_Private_Set"]
VOICEARENA_NON_US = ["HF_English_Private_Set"]

def _clean_wer(value):
    """Return a positive rounded WER, or None if missing/zero/negative/NaN."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or f <= 0:
        return None
    return round(f, 2)


# Column name(s) a per-language multilingual CSV may use to declare a model's
# parameter count (case-insensitive). Kept out of the per-language dataset list.
SIZE_COL_NAMES = {"size (b)", "size"}


def _parse_size(value):
    """Parse a 'Size (B)' cell to a positive float, or 'NA'. Unlike WER, sizes
    aren't rounded (a 0.6B model shouldn't display as 0.6 rounded to 2dp loss)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "NA"
    if np.isnan(f) or f <= 0:
        return "NA"
    return f


def _lang_display(code):
    """Human-readable label for a language code, e.g. '🇩🇪 German'."""
    info = LANGUAGES.get(code)
    if info:
        return f"{info['flag']} {info['name']}"
    return code.upper()


def _clean_rtfx(value):
    """Return a positive rounded RTFx, or 'NA' (e.g. -1 for API-only services)."""
    r = _clean_wer(value)
    return r if r is not None else "NA"


def _order_codes(present):
    """Order language codes: known (LANGUAGES) order first, then extras."""
    codes = [c for c in LANGUAGES if c in present]
    codes += [c for c in present if c not in codes]
    return codes


def _finalize_multi(codes, lang_datasets, details, html, size_by_model=None):
    """Assemble the MULTI dict from the parsed pieces (shared by both formats).

    ``details[model][code]`` is expected to be ``{"avg", "datasets", "rtfx"}``;
    any language a model is missing entirely is backfilled as NA so every model
    has an entry for every language. ``size_by_model`` holds any model sizes
    declared in the language CSVs (they take precedence over the main CSV).
    """
    for model in details:
        for code in codes:
            details[model].setdefault(code, {"avg": "NA", "datasets": {}, "rtfx": "NA"})
    return {
        "codes": codes,
        "lang_datasets": lang_datasets,   # {code: [dataset display name, ...]}
        "details": details,               # {model: {code: {avg, datasets, rtfx}}}
        "html": html,
        "display": {c: _lang_display(c) for c in codes},
        "display_to_code": {_lang_display(c): c for c in codes},
        "size_by_model": size_by_model or {},  # {model: size} from language CSVs
    }


def _build_multilingual_combined(path):
    """Legacy format: one combined CSV with '{lang_code}_{dataset_key}' columns
    (e.g. 'de_covost', 'fr_fleurs') plus a single global RTFx per model."""
    raw_df = pd.read_csv(path)

    non_lang_cols = {"model", "rtfx", "avg"}
    raw_datasets = {}  # code -> [raw dataset key, ...] in column order
    for col in raw_df.columns:
        if col.lower() in non_lang_cols or "_" not in col:
            continue
        code, dkey = col.split("_", 1)
        raw_datasets.setdefault(code, [])
        if dkey not in raw_datasets[code]:
            raw_datasets[code].append(dkey)

    codes = _order_codes(list(raw_datasets.keys()))

    # Order each language's datasets by a preferred order, then extras.
    ds_pref = ["covost", "mls", "fleurs"]
    for code in codes:
        ds = raw_datasets[code]
        raw_datasets[code] = [d for d in ds_pref if d in ds] + [d for d in ds if d not in ds_pref]

    # Display names for the columns we'll expose.
    lang_datasets = {
        code: [DATASET_DISPLAY.get(d, d.upper()) for d in raw_datasets[code]]
        for code in codes
    }

    details, html = {}, {}
    for _, row in raw_df.iterrows():
        model = row["model"]
        html[model] = make_clickable_model(model)
        rtfx = _clean_rtfx(row.get("RTFx", row.get("rtfx")))  # single global RTFx

        model_langs = {}
        for code in codes:
            scores = {}
            for dkey in raw_datasets[code]:
                s = _clean_wer(row.get(f"{code}_{dkey}"))
                if s is not None:
                    scores[DATASET_DISPLAY.get(dkey, dkey.upper())] = s
            avg = round(np.mean(list(scores.values())), 2) if scores else "NA"
            # Legacy CSVs report one RTFx per model, so reuse it for every language.
            model_langs[code] = {"avg": avg, "datasets": scores, "rtfx": rtfx}
        details[model] = model_langs

    return _finalize_multi(codes, lang_datasets, details, html)


def _build_multilingual_per_language(path_by_code):
    """Per-language format: one CSV per language, each with its own 'model',
    'RTFx', and display-ready '<DATASET> WER' columns. Datasets (and RTFx) vary
    by language, so they're stored per language."""
    codes = _order_codes(list(path_by_code.keys()))

    lang_datasets, details, html = {}, {}, {}
    size_by_model = {}  # model -> Size (B), when a language CSV declares it
    for code in codes:
        df = pd.read_csv(path_by_code[code])
        # Every column other than model/RTFx/size is a dataset; strip the ' WER'
        # suffix for a clean display name (e.g. 'FLEURS WER' -> 'FLEURS'). A
        # 'Size (B)' column (optional) is captured separately, not as a dataset.
        size_col = next((c for c in df.columns if c.strip().lower() in SIZE_COL_NAMES), None)
        dataset_cols = [c for c in df.columns
                        if c.lower() not in ("model", "rtfx", "avg") and c != size_col]
        disp_names = [c.removesuffix(" WER").strip() if c.strip().endswith("WER") else c
                      for c in dataset_cols]
        disp_names = [PER_LANGUAGE_DATASET_DISPLAY.get(d, d) for d in disp_names]
        lang_datasets[code] = disp_names

        for _, row in df.iterrows():
            model = row["model"]
            html.setdefault(model, make_clickable_model(model))
            model_langs = details.setdefault(model, {})

            if size_col is not None:
                size = _parse_size(row.get(size_col))
                if size != "NA":
                    size_by_model[model] = size

            scores = {}
            for col, disp in zip(dataset_cols, disp_names):
                s = _clean_wer(row.get(col))
                if s is not None:
                    scores[disp] = s
            avg = round(np.mean(list(scores.values())), 2) if scores else "NA"
            model_langs[code] = {
                "avg": avg,
                "datasets": scores,
                "rtfx": _clean_rtfx(row.get("RTFx", row.get("rtfx"))),
            }

    return _finalize_multi(codes, lang_datasets, details, html, size_by_model)


def build_multilingual_data():
    """Parse the multilingual source(s) into the global MULTI structure.

    Two source shapes are supported:
      * a single combined CSV path (legacy '{lang}_{dataset}' columns), or
      * a {language_code: csv_path} mapping (one CSV per language).
    """
    global MULTI

    src = multilingual_csv_path
    if isinstance(src, dict):
        if not src:
            raise Exception("No multilingual CSV files found")
        MULTI = _build_multilingual_per_language(src)
    else:
        if src is None or not Path(src).exists():
            raise Exception("Multilingual CSV file not found")
        MULTI = _build_multilingual_combined(src)

    # English is injected separately, after original_df's Private-data columns
    # have been added, so its average matches the version's leaderboard average.


def _inject_english(multi):
    """Add (or refresh) a synthetic 'English' language whose per-model scores
    come from the main leaderboard (``original_df``): the average over the
    version's default datasets, those datasets as the breakdown, and the
    leaderboard RTFx.

    The average intentionally matches the leaderboard's default Average WER for
    the current version — so if the version's ``default_datasets`` include the
    Private-data columns (and they've been added to original_df), those are
    included too. Call this *after* the Private columns are attached.

    Idempotent: re-running replaces any previous English injection. Matched to
    the multilingual models by plain name; models absent from the main
    leaderboard get NA. English is appended last and is off by default (the
    language selectors exclude it from their initial value)."""
    # Drop any prior English injection so this can be safely re-run.
    if ENGLISH_CODE in multi["codes"]:
        multi["codes"].remove(ENGLISH_CODE)
    multi["lang_datasets"].pop(ENGLISH_CODE, None)
    multi["display"].pop(ENGLISH_CODE, None)
    multi["display_to_code"].pop(ENGLISH_DISPLAY, None)
    for langs in multi["details"].values():
        langs.pop(ENGLISH_CODE, None)

    # Default datasets present on the main leaderboard (English sets, plus the
    # Private-data columns when the version includes them and they're attached).
    en_cols = [c for c in default_datasets if c in original_df.columns]
    model_col = original_df.columns[0]

    en_avg, en_rtfx, en_dsets = {}, {}, {}
    for _, row in original_df.iterrows():
        name = re.sub(r"<[^>]+>", "", str(row[model_col]))
        scores = {}
        complete = True
        for col in en_cols:
            v = _clean_wer(row.get(col))
            if v is None:
                complete = False
            else:
                scores[col] = v
        # Require all default datasets (matches the leaderboard's Average WER).
        en_avg[name] = round(np.mean([scores[c] for c in en_cols]), 2) if complete and en_cols else "NA"
        en_dsets[name] = scores
        en_rtfx[name] = _clean_rtfx(row.get("RTFx ⬆️️"))

    for model, langs in multi["details"].items():
        langs[ENGLISH_CODE] = {
            "avg": en_avg.get(model, "NA"),
            "datasets": en_dsets.get(model, {}),
            "rtfx": en_rtfx.get(model, "NA"),
        }

    multi["codes"].append(ENGLISH_CODE)
    multi["lang_datasets"][ENGLISH_CODE] = en_cols
    multi["display"][ENGLISH_CODE] = ENGLISH_DISPLAY
    multi["display_to_code"][ENGLISH_DISPLAY] = ENGLISH_CODE


def _inject_hindi_private(multi):
    """Add the VoiceArena private Hindi set (``HF_Hindi_Private_Set`` in the
    voicearena CSV) as an extra dataset column in the Hindi (``hi``) breakdown,
    matched to models by plain name, and refold it into the Hindi average so it
    counts alongside the public datasets.

    No-op if Hindi isn't present or the CSV / column is unavailable. Idempotent:
    re-running replaces any previous injection."""
    code = HINDI_CODE
    disp = HINDI_PRIVATE_DISPLAY
    if code not in multi["codes"]:
        return
    if voicearena_csv_path is None or not Path(voicearena_csv_path).exists():
        return

    va_df = pd.read_csv(voicearena_csv_path)
    if HINDI_PRIVATE_CSV_COLUMN not in va_df.columns or "model" not in va_df.columns:
        return

    private_by_model = {}
    for _, row in va_df.iterrows():
        wer = _clean_wer(row.get(HINDI_PRIVATE_CSV_COLUMN))
        if wer is not None:
            private_by_model[row["model"]] = wer

    # Expose the private column once in the Hindi dataset list.
    ds_list = multi["lang_datasets"].setdefault(code, [])
    if disp not in ds_list:
        ds_list.append(disp)

    for model, langs in multi["details"].items():
        info = langs.get(code)
        if info is None:
            continue
        # Drop any prior injection so this can be safely re-run.
        info["datasets"].pop(disp, None)
        wer = private_by_model.get(model)
        if wer is not None:
            info["datasets"][disp] = wer
        # Average over all Hindi datasets present (public + private).
        vals = list(info["datasets"].values())
        info["avg"] = round(np.mean(vals), 2) if vals else "NA"


# Model sizes (total params, in B) hardcoded for models that don't appear in
# the English leaderboard data (which is where sizes normally come from).
# omniASR counts are from the omnilingual-asr architectures table — note the LLM
# variants include the language-model head, so they're much larger than the
# encoder size in the name. https://github.com/facebookresearch/omnilingual-asr
EXTRA_MODEL_SIZES = {
    "facebook/omniASR-CTC-300M-v2": 0.33,
    "facebook/omniASR-CTC-1B-v2": 0.98,
    "facebook/omniASR-CTC-3B-v2": 3.08,
    "facebook/omniASR-LLM-300M-v2": 1.63,
    "facebook/omniASR-LLM-1B-v2": 2.28,
    "facebook/omniASR-LLM-3B-v2": 4.38,
}


def _size_by_model():
    """Map plain model name -> "Size (B)". Sizes come from the main leaderboard;
    models missing there (or with an NA size) fall back to EXTRA_MODEL_SIZES."""
    col = original_df.columns[0]
    result = {
        re.sub(r"<[^>]+>", "", str(row[col])): row.get("Size (B)", "NA")
        for _, row in original_df.iterrows()
    }
    for name, size in EXTRA_MODEL_SIZES.items():
        if result.get(name, "NA") == "NA":
            result[name] = size
    return result


def _multi_size_map():
    """Model -> Size (B) for the multilingual views. A size declared in a
    language CSV wins (needed for language-only models absent from the main
    leaderboard); otherwise fall back to the main leaderboard (incl.
    EXTRA_MODEL_SIZES), else "NA"."""
    merged = dict(_size_by_model())
    for model, size in MULTI.get("size_by_model", {}).items():
        if size != "NA":
            merged[model] = size
    return merged


def _multilingual_overview_df(codes):
    """Overview: one average-WER column per selected language.

    A model is *ranked* only if it has an average for every selected language
    (require-all semantics), and its Average WER is the mean of those
    per-language averages — an apples-to-apples comparison over the same set.

    Models that cover only *some* of the selected languages are not dropped:
    they are shown below the ranked models as unranked rows (Average WER = NA)
    with NA in the languages they don't cover, so nothing silently disappears.
    Models covering none of the selected languages are omitted entirely.

    When more than one language is selected, a "Coverage" column (e.g. "3/5")
    makes it explicit how many of the selected languages each model is evaluated on.

    The 🇬🇧 English "language" (code ``en``) is injected from the main
    leaderboard by ``_inject_english``: its per-model value is the average over
    the version's ``default_datasets`` — the same number as the main
    leaderboard's Average WER.
    """
    n = len(codes)
    show_coverage = n > 1
    lang_cols = [MULTI["display"][c] for c in codes]
    base_cols = ["Model", "Average WER ⬇️"]
    if show_coverage:
        base_cols.append("Coverage")
    base_cols += ["RTFx ⬆️️", "Size (B)"] + lang_cols

    size_map = _multi_size_map()

    ranked, partial = [], []
    for model, model_langs in MULTI["details"].items():
        if not codes:
            continue
        per_lang = {c: model_langs[c]["avg"] for c in codes}
        supported = [v for v in per_lang.values() if v != "NA"]
        n_cov = len(supported)
        if n_cov == 0:
            continue  # covers none of the selected languages -> nothing to show

        # RTFx across the selected languages is the macro-average of the
        # per-language RTFx values the model actually reports.
        rtfx_vals = [model_langs[c]["rtfx"] for c in codes if model_langs[c]["rtfx"] != "NA"]
        rtfx = round(np.mean(rtfx_vals), 2) if rtfx_vals else "NA"

        row = {"Model": MULTI["html"][model], "RTFx ⬆️️": rtfx,
               "Size (B)": size_map.get(model, "NA")}
        for c, col in zip(codes, lang_cols):
            row[col] = per_lang[c]
        if show_coverage:
            row["Coverage"] = f"{n_cov}/{n}"

        if n_cov == n:
            row["Average WER ⬇️"] = round(np.mean(supported), 2)
            ranked.append(row)
        else:
            row["Average WER ⬇️"] = "NA"
            row["_ncov"] = n_cov
            row["_partial_avg"] = round(np.mean(supported), 2)
            partial.append(row)

    if not ranked and not partial:
        return pd.DataFrame(columns=base_cols)

    ranked_df = (
        pd.DataFrame(ranked)[base_cols].sort_values(by="Average WER ⬇️")
        if ranked else pd.DataFrame(columns=base_cols)
    )
    if partial:
        # Most-covered first, then best partial average — purely for row order.
        partial_df = pd.DataFrame(partial).sort_values(
            by=["_ncov", "_partial_avg"], ascending=[False, True]
        )[base_cols]
    else:
        partial_df = pd.DataFrame(columns=base_cols)

    return pd.concat([ranked_df, partial_df], ignore_index=True)


def _multilingual_zoom_df(code):
    """Zoom: a single language's per-dataset breakdown, no other languages.

    Shows the language average plus one column per dataset, with NA where a
    supported model lacks a particular dataset. RTFx is that language's own
    RTFx. Models with no data at all for this language are dropped.
    """
    disp = MULTI["display"][code]
    dataset_cols = MULTI["lang_datasets"][code]  # already display names
    base_cols = ["Model", f"{disp} Avg", "RTFx ⬆️️", "Size (B)"] + dataset_cols

    size_map = _multi_size_map()

    rows = []
    for model, model_langs in MULTI["details"].items():
        info = model_langs[code]
        if info["avg"] == "NA":
            continue  # model doesn't cover this language
        row = {
            "Model": MULTI["html"][model],
            f"{disp} Avg": info["avg"],
            "RTFx ⬆️️": info["rtfx"],
            "Size (B)": size_map.get(model, "NA"),
        }
        for col in dataset_cols:
            row[col] = info["datasets"].get(col, "NA")
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=base_cols)
    df = pd.DataFrame(rows)[base_cols]
    return df.sort_values(by=f"{disp} Avg")


def _multilingual_view(search_query, show_proprietary, selected_display, zoom_display):
    """Build the (dataframe, datatype) pair for the current multilingual state."""
    if zoom_display and zoom_display != OVERVIEW_LABEL:
        code = MULTI["display_to_code"].get(zoom_display)
        if code:
            df = _multilingual_zoom_df(code)
            metric_col = f"{MULTI['display'][code]} Avg"
        else:
            df = _multilingual_overview_df(MULTI["codes"])
            metric_col = "Average WER ⬇️"
    else:
        selected = set(selected_display or [])
        codes = [c for c in MULTI["codes"] if MULTI["display"][c] in selected]
        df = _multilingual_overview_df(codes)
        metric_col = "Average WER ⬇️"

    df = _finalize_table(df, metric_col, search_query, show_proprietary)
    return _style_table(df)


def render_multilingual(search_query, show_proprietary, selected_display, zoom_display):
    """Gradio callback: return an update carrying the current multilingual view."""
    df, datatype = _multilingual_view(search_query, show_proprietary, selected_display, zoom_display)
    return gr.update(value=df, datatype=datatype)


# Initialize multilingual data
build_multilingual_data()

def create_longform_dataframe():
    """Create longform dataframe from CSV data"""
    if longform_csv_path is not None and longform_csv_path.exists():
        longform_raw_df = pd.read_csv(longform_csv_path)
        longform_data = []
        
        for _, row_data in longform_raw_df.iterrows():
            model_name = row_data['model_id']
            
            # Get values from CSV, similar to other tabs
            earnings21_wer = row_data.get('earnings21', -1)
            earnings22_wer = row_data.get('earnings22', -1)
            coraal_wer = row_data.get('coraal_avg', -1)
            rtfx_value = row_data.get('RTFx', 0)
            
            # Calculate average WER from available datasets
            available_wers = [w for w in [earnings21_wer, earnings22_wer, coraal_wer] if w != -1 and w > 0]
            avg_wer = round(np.mean(available_wers), 2) if available_wers else 0.0
            
            row = {
                "Model": make_clickable_model(model_name),
                "Average WER ⬇️": avg_wer,
                "RTFx ⬆️️": rtfx_value if rtfx_value > 0 else "NA",
                "Earnings21": earnings21_wer if earnings21_wer != -1 else "NA",
                "Earnings22": earnings22_wer if earnings22_wer != -1 else "NA",
                "CORAAL": coraal_wer if coraal_wer != -1 else "NA",
            }
            longform_data.append(row)
        
        longform_df = pd.DataFrame(longform_data)
    
    longform_df = longform_df.sort_values(by='Average WER ⬇️')
    return longform_df

# Initialize longform dataframe
longform_df = create_longform_dataframe()

# Benchmark-fitting analysis data (per-version; may be absent for old versions).
def _load_benchmark_fitting_df():
    if voxpopuli_fitting_csv_path is not None and Path(voxpopuli_fitting_csv_path).exists():
        return pd.read_csv(voxpopuli_fitting_csv_path)
    return None

def _load_rendering_fitting_data():
    """Map dataset label -> per-split rendering-agreement dataframe."""
    return {
        label: pd.read_csv(path)
        for label, path in (rendering_fitting_csv_paths or {}).items()
        if path is not None and Path(path).exists()
    }

benchmark_fitting_df = _load_benchmark_fitting_df()
rendering_fitting_data = _load_rendering_fitting_data()
# Splits unchecked by default in the rendering-agreement section. We default to
# the original (noisy-reference) VoxPopuli and toggle off the AA-cleaned split so
# the spelling-copying / benchmaxing phenomenon is more apparent.
RENDERING_DEFAULT_OFF = {"Voxpopuli-AA-Cleaned"}


def _safe_mean(values):
    """Compute mean of non-NA, positive values. Return None if empty."""
    valid = [v for v in values if v is not None and v != "NA" and v > 0]
    return round(np.mean(valid), 2) if valid else None


def create_private_data_dataframe():
    """Create private data dataframe by merging Appen and DataoceanAI benchmarks.
    
    Averages are computed as follows:
    - Avg Scripted: macro-average of all scripted datasets
    - Avg Conversational: macro-average of all conversational datasets (incl. VoiceArena)
    - Avg US: macro-average of all US-accent datasets
    - Avg Non-US: macro-average of all non-US-accent datasets (incl. VoiceArena)

    The Private-data tab's headline "Average WER" is the mean of a *grouping* pair
    (Scripted/Conversational or US/Non-US), computed per view in
    _private_view — not the per-provider macro-average below.
    """
    appen_df = None
    dataocean_df = None
    voicearena_df = None

    # Only keep the model column and the raw per-dataset score columns;
    # ignore any pre-computed average columns in the CSVs.
    appen_keep_cols = ["model"] + APPEN_SCRIPTED + APPEN_CONVERSATIONAL
    dataocean_keep_cols = ["model"] + DATAOCEAN_SCRIPTED + DATAOCEAN_CONVERSATIONAL
    voicearena_keep_cols = ["model"] + VOICEARENA_CONVERSATIONAL + VOICEARENA_NON_US

    if appen_csv_path is not None and Path(appen_csv_path).exists():
        appen_df = pd.read_csv(appen_csv_path)
        appen_df = appen_df[[c for c in appen_keep_cols if c in appen_df.columns]]
    if dataocean_csv_path is not None and Path(dataocean_csv_path).exists():
        dataocean_df = pd.read_csv(dataocean_csv_path)
        dataocean_df = dataocean_df[[c for c in dataocean_keep_cols if c in dataocean_df.columns]]
    if voicearena_csv_path is not None and Path(voicearena_csv_path).exists():
        voicearena_df = pd.read_csv(voicearena_csv_path)
        # de-dup the keep list (HF_English_Private_Set appears in both splits)
        voicearena_df = voicearena_df[[c for c in dict.fromkeys(voicearena_keep_cols) if c in voicearena_df.columns]]

    if appen_df is None and dataocean_df is None:
        raise Exception("No private data CSV files found")

    # Determine the set of models present in any provider
    models = set()
    if appen_df is not None:
        models |= set(appen_df["model"].tolist())
    if dataocean_df is not None:
        models |= set(dataocean_df["model"].tolist())
    if voicearena_df is not None:
        models |= set(voicearena_df["model"].tolist())

    # Only keep models that also appear on the public (English short-form)
    # leaderboard, matched by plain model name. (original_df's model column
    # holds clickable HTML, so strip the tags before comparing.)
    main_model_names = {
        re.sub(r"<[^>]+>", "", str(m)) for m in original_df[original_df.columns[0]]
    }
    models = {m for m in models if m in main_model_names}

    private_data_rows = []
    private_scripted_map = {}  # model -> avg scripted WER
    private_conversational_map = {}  # model -> avg conversational WER
    
    for model_name in sorted(models):
        appen_row = None
        dataocean_row = None
        voicearena_row = None
        if appen_df is not None and model_name in appen_df["model"].values:
            appen_row = appen_df[appen_df["model"] == model_name].iloc[0]
        if dataocean_df is not None and model_name in dataocean_df["model"].values:
            dataocean_row = dataocean_df[dataocean_df["model"] == model_name].iloc[0]
        if voicearena_df is not None and model_name in voicearena_df["model"].values:
            voicearena_row = voicearena_df[voicearena_df["model"] == model_name].iloc[0]
        
        # Collect all scores per category
        all_scripted = []
        all_conversational = []
        all_us = []
        all_non_us = []

        if appen_row is not None:
            for col in APPEN_SCRIPTED:
                v = appen_row.get(col, None)
                if v is not None and v > 0:
                    all_scripted.append(v)
            for col in APPEN_CONVERSATIONAL:
                v = appen_row.get(col, None)
                if v is not None and v > 0:
                    all_conversational.append(v)
            for col in APPEN_US:
                v = appen_row.get(col, None)
                if v is not None and v > 0:
                    all_us.append(v)
            for col in APPEN_NON_US:
                v = appen_row.get(col, None)
                if v is not None and v > 0:
                    all_non_us.append(v)
        
        if dataocean_row is not None:
            for col in DATAOCEAN_SCRIPTED:
                v = dataocean_row.get(col, None)
                if v is not None and v > 0:
                    all_scripted.append(v)
            for col in DATAOCEAN_CONVERSATIONAL:
                v = dataocean_row.get(col, None)
                if v is not None and v > 0:
                    all_conversational.append(v)
            for col in DATAOCEAN_US:
                v = dataocean_row.get(col, None)
                if v is not None and v > 0:
                    all_us.append(v)
            for col in DATAOCEAN_NON_US:
                v = dataocean_row.get(col, None)
                if v is not None and v > 0:
                    all_non_us.append(v)

        # VoiceArena is a single English conversational, non-US set: it feeds the
        # conversational and non-US group averages.
        if voicearena_row is not None:
            for col in VOICEARENA_CONVERSATIONAL:
                v = voicearena_row.get(col, None)
                if v is not None and v > 0:
                    all_conversational.append(v)
            for col in VOICEARENA_NON_US:
                v = voicearena_row.get(col, None)
                if v is not None and v > 0:
                    all_non_us.append(v)

        avg_scripted = _safe_mean(all_scripted) if all_scripted else "NA"
        avg_conversational = _safe_mean(all_conversational) if all_conversational else "NA"
        avg_us = _safe_mean(all_us) if all_us else "NA"
        avg_non_us = _safe_mean(all_non_us) if all_non_us else "NA"
        
        private_data_rows.append({
            "Model": make_clickable_model(model_name),
            "Avg Scripted": avg_scripted,
            "Avg Conversational": avg_conversational,
            "Avg US": avg_us,
            "Avg Non-US": avg_non_us,
        })

        private_scripted_map[model_name] = avg_scripted
        private_conversational_map[model_name] = avg_conversational

    # Order doesn't matter here — _private_view re-sorts per grouping.
    private_df = pd.DataFrame(private_data_rows).sort_values(by="Model")
    return private_df, private_scripted_map, private_conversational_map


# Initialize private data dataframe
private_data_df, private_scripted_map, private_conversational_map = create_private_data_dataframe()

# Add "Private (scripted)" and "Private (conversational)" columns to main leaderboard
# Match by plain model name (strip HTML from original_df's model column)
def _get_plain_model_name(html_str):
    import re
    return re.sub(r"<[^>]+>", "", str(html_str))

original_df["Private (scripted)"] = original_df[original_df.columns[0]].apply(
    lambda x: private_scripted_map.get(_get_plain_model_name(x), "NA")
)
original_df["Private (conversational)"] = original_df[original_df.columns[0]].apply(
    lambda x: private_conversational_map.get(_get_plain_model_name(x), "NA")
)

# Inject the English "language" now that original_df has its Private columns,
# so the English average matches the version's leaderboard Average WER.
_inject_english(MULTI)

# Fold the VoiceArena private Hindi set into the Hindi breakdown + average.
_inject_hindi_private(MULTI)


# Default ranking is computed lazily after default_columns is known
_default_rank = {}


def _compute_default_rank():
    """Compute the baseline ranking using the default dataset selection."""
    global _default_rank
    if _default_rank:
        return  # already computed

    # Use default_datasets as the source of truth for which WER columns define the baseline
    df = original_df.copy()
    wer_cols = [c for c in default_datasets if c in df.columns]
    if wer_cols:
        for c in wer_cols:
            df = df[df[c] != "NA"]

        def compute_avg(row):
            vals = [float(row[c]) for c in wer_cols]
            return round(np.mean(vals), 2) if vals else "NA"
        df["Average WER ⬇️"] = df.apply(compute_avg, axis=1)

    df = df.sort_values(by="Average WER ⬇️")
    model_col = df.columns[0]
    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        _default_rank[row[model_col]] = rank


def _pooled_rtfx(row, split_names):
    """Duration-pooled RTFx over the given (display-named) public splits:
        pooled = Σ d[i] / Σ (d[i] / rtfx[i])
    using the per-split '<split> RTFx' CSV columns and SPLIT_DURATIONS_S. Splits
    without a positive per-split RTFx are skipped; if none remain (e.g. old
    versions with no per-split RTFx, or an API model), falls back to the single
    CSV RTFx ('RTFx ⬆️️'). Returns -1 when nothing is available."""
    total_dur = 0.0
    total_time = 0.0
    for ds in split_names:
        r = pd.to_numeric(row.get(f"{ds} RTFx"), errors="coerce")
        if pd.isna(r) or r <= 0:
            continue
        d = SPLIT_DURATIONS_S[ds]
        total_dur += d
        total_time += d / r
    if total_time > 0:
        return round(total_dur / total_time, 2)
    fb = pd.to_numeric(row.get("RTFx ⬆️️"), errors="coerce")
    return round(float(fb), 2) if not pd.isna(fb) and fb > 0 else -1


def filter_main_table(search_query, show_proprietary, show_llm, selected_columns):  # Uncomment show_llm parameter for show_llm feature
    filtered_df = original_df.copy()
    model_col = filtered_df.columns[0]

    # NOTE: the model-name search is applied *last*, so the Rank column below is
    # computed over the full (proprietary + dataset) ranking and stays fixed
    # while searching. Toggling datasets changes the average and thus the rank.

    # Filter proprietary models if needed
    if not show_proprietary and "License" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["License"].str.lower() != "proprietary"]

    # Uncomment below for show_llm feature
    # Filter to only audio language models if checked
    # if show_llm:
    #     filtered_df = filtered_df[filtered_df[model_col].apply(
    #         lambda x: strip_html(x) in AUDIO_LM_MODELS
    #     )]

    # Recompute RTFx as the duration-pooled RTFx over the selected public splits.
    # Done here, before the unchecked columns are hidden below, while the raw
    # per-split '<split> RTFx' columns are still present. Falls back to the CSV RTFx.
    rtfx_splits = [c for c in selected_columns if c in SPLIT_DURATIONS_S]
    filtered_df["RTFx ⬆️️"] = filtered_df.apply(
        lambda row: _pooled_rtfx(row, rtfx_splits), axis=1)

    # Hide toggleable columns that the user unchecked
    all_toggleable = [c for c in filtered_df.columns if c not in always_visible]
    columns_to_hide = set(all_toggleable) - set(selected_columns)
    filtered_df = filtered_df[[c for c in filtered_df.columns if c not in columns_to_hide]]

    # Recompute average WER from the selected WER benchmark columns (exclude RTFx)
    wer_cols = [c for c in selected_columns if c in filtered_df.columns and c not in EXCLUDED_AVG_COLS]
    if wer_cols:
        # Drop models that have NA for any selected WER benchmark column
        for c in wer_cols:
            filtered_df = filtered_df[filtered_df[c] != "NA"]

        def compute_avg(row):
            vals = [float(row[c]) for c in wer_cols]
            return round(np.mean(vals), 2) if vals else "NA"
        filtered_df["Average WER ⬇️"] = filtered_df.apply(compute_avg, axis=1)
    else:
        filtered_df["Average WER ⬇️"] = "NA"

    filtered_df = filtered_df.sort_values(by="Average WER ⬇️")

    # Absolute Rank over the current (pre-search) ordering — leftmost column.
    filtered_df = _add_rank_column(filtered_df, "Average WER ⬇️")

    # Compute Rank Δ compared to default ranking, among the current models
    # (pre-search, so it too is stable while searching).
    current_models = set(filtered_df[model_col].tolist())
    default_subset_rank = {}
    rank = 1
    for model_html in sorted(_default_rank, key=_default_rank.get):
        if model_html in current_models:
            default_subset_rank[model_html] = rank
            rank += 1

    new_ranks = {}
    for new_rank, (_, row) in enumerate(filtered_df.iterrows(), start=1):
        new_ranks[row[model_col]] = new_rank

    def rank_delta(model_html):
        old = default_subset_rank.get(model_html)
        new = new_ranks.get(model_html)
        if old is None or new is None:
            return "—"
        delta = old - new  # positive = model rose, negative = model dropped
        if delta > 0:
            return f"▲{delta}"
        elif delta < 0:
            return f"▼{abs(delta)}"
        return "—"

    filtered_df["Rank Δ"] = filtered_df[model_col].apply(rank_delta)

    # Compute the medal value→icon maps over the full (pre-search) set so the
    # podium stays with the same models while searching. The medal is applied at
    # display time by _style_table (the underlying values stay numeric so the
    # columns sort numerically); RTFx is higher-better, WER lower-better.
    medal_maps = {}
    for c in [c for c in filtered_df.columns if c in NUMERIC_SORT_COLS]:
        numeric = pd.to_numeric(filtered_df[c], errors="coerce")
        if "RTFx" in c:
            numeric = numeric.where(numeric > 0)  # API-only (-1) isn't ranked
        vals = numeric.dropna()
        if vals.empty:
            continue
        top = sorted(set(vals), reverse=("RTFx" in c))[:3]
        medal_maps[c] = {v: MEDAL_ICONS[i] for i, v in enumerate(top)}

    filtered_df = _apply_search_filter(filtered_df, search_query, model_col)

    # Reorder columns: Rank, Rank Δ (right next to Rank), model, Avg WER, RTFx,
    # then metadata (if toggled on), non-default datasets, then default datasets.
    visible_cols = list(filtered_df.columns)
    header = ["Rank", "Rank Δ", model_col, "Average WER ⬇️", "RTFx ⬆️️"]
    header_cols = [c for c in header if c in visible_cols]
    rest = [c for c in visible_cols if c not in header_cols]
    metadata = [c for c in rest if c in METADATA_COLUMNS]
    non_default_wer = [c for c in rest if c not in metadata and c not in default_datasets and c not in EXCLUDED_AVG_COLS]
    default_wer = [c for c in rest if c in default_datasets]
    reordered = header_cols + metadata + non_default_wer + default_wer
    filtered_df = filtered_df[reordered]

    # Stash the (pre-search) medal maps for _style_table to apply at display time.
    filtered_df.attrs["medal_maps"] = medal_maps
    return filtered_df


def _num_text(v):
    """Render a numeric value at its own precision (values are already rounded
    upstream): drop a trailing '.0' and any trailing zeros, no re-rounding."""
    return ("%f" % v).rstrip("0").rstrip(".")


def _medal_formatter(medal_by_value):
    """Build a Styler cell formatter: NaN → 'NA', otherwise the number with a
    🥇🥈🥉 appended if it's one of the medal values. Only the *display* changes;
    the underlying numeric value is untouched (so the column sorts numerically)."""
    def _fmt(v):
        v = pd.to_numeric(v, errors="coerce")
        if pd.isna(v):
            return "NA"
        text = _num_text(v)
        medal = medal_by_value.get(v)
        return f"{text} {medal}" if medal else text

    return _fmt


def _main_table_update(search_query, show_proprietary, show_llm, selected_columns):
    """filter_main_table wrapped as a component update carrying the numeric
    datatype (so numeric columns sort numerically) and the medal-styled display."""
    df = filter_main_table(search_query, show_proprietary, show_llm, selected_columns)
    return _styled_update(df)

def strip_html(text):
    """Remove HTML tags to get plain model name."""
    return re.sub(r"<[^>]+>", "", str(text))

def _shortform_model_names():
    """Plain names of models shown on the short-form leaderboard — i.e. those
    with a (non-NA) result for every default dataset of the current version."""
    cols = [c for c in default_datasets if c in original_df.columns]
    if not cols:
        return set()
    model_col = original_df.columns[0]
    return {
        strip_html(row[model_col])
        for _, row in original_df.iterrows()
        if all(str(row.get(c)) != "NA" for c in cols)
    }

def _get_proprietary_models():
    """Return the set of plain model names marked as 'Proprietary' in the main leaderboard."""
    if "License" in original_df.columns:
        model_col = original_df.columns[0]
        prop_mask = original_df["License"].str.lower() == "proprietary"
        return set(original_df.loc[prop_mask, model_col].apply(strip_html))
    return set()

def _get_known_model_names():
    """Return the set of plain model names that appear on the main leaderboard."""
    model_col = original_df.columns[0]
    return set(original_df[model_col].apply(strip_html))

def _is_rtfx_missing(value):
    """RTFx of -1/NA/empty indicates an API-only (proprietary) service with no reported throughput."""
    if value is None:
        return True
    text = str(value).strip().lower()
    if text in ["", "na", "nan", "-1", "-1.0"]:
        return True
    try:
        return float(value) <= 0
    except (TypeError, ValueError):
        return False

def _apply_generic_proprietary(df, show_proprietary):
    """Drop proprietary models from a leaderboard-style dataframe (model col at 0)."""
    if show_proprietary or df.empty:
        return df
    model_col = df.columns[0]
    proprietary_models = _get_proprietary_models()
    known_models = _get_known_model_names()
    rtfx_col = next((c for c in df.columns if "RTFx" in c), None)

    def _is_proprietary(row):
        name = strip_html(row[model_col])
        if name in proprietary_models:
            return True
        if name in known_models:
            # Present on the main leaderboard but not flagged proprietary there.
            return False
        # Model isn't on the main leaderboard at all, so there's no License to
        # check. Fall back to treating a missing/-1 RTFx (no measured
        # throughput) as a signal that it's an API-only, proprietary service.
        if rtfx_col is not None:
            return _is_rtfx_missing(row[rtfx_col])
        return False

    return df[~df.apply(_is_proprietary, axis=1)]


def _apply_search_filter(df, search_query, model_col):
    """Keep rows whose (HTML) model cell matches any comma-separated search term."""
    if not search_query or df.empty:
        return df
    terms = [t.strip().lower() for t in search_query.split(",") if t.strip()]
    if not terms:
        return df
    mask = df[model_col].str.lower().apply(lambda cell: any(term in cell for term in terms))
    return df[mask]


def _add_rank_column(df, metric_col):
    """Insert a leftmost 1-based "Rank" column based on the current row order
    (the df must already be sorted by ``metric_col`` ascending). Rows whose
    metric is non-numeric (NA / unranked) get "—". Computed before any search
    filter so the rank stays fixed while searching."""
    if df.empty:
        df.insert(0, "Rank", [])
        return df
    ranks, r = [], 0
    for val in df[metric_col]:
        v = pd.to_numeric(val, errors="coerce")
        if pd.isna(v):
            ranks.append("—")
        else:
            r += 1
            ranks.append(r)
    df.insert(0, "Rank", ranks)
    return df


def _perf_cols(df):
    """Numeric, medal-able performance columns of a table (WER / RTFx / rate
    columns) — excludes the model, rank, coverage and metadata columns. Used to
    decide which columns get a medal, not which sort numerically."""
    return [c for c in df.columns
            if c not in MEDAL_SKIP_COLS
            and pd.to_numeric(df[c], errors="coerce").notna().any()]


# Columns that never render as numbers even if they parse: the model, the Rank
# index (kept as the presentation order, shown as "—" when unranked) and the
# categorical Rank Δ ("▲2") / Coverage ("3/5") columns.
_NON_NUMERIC_COLS = {"model", "Model", "Rank", "Rank Δ", "Coverage"}


def _numeric_cols(df):
    """Every column holding numbers, so it renders as a 'number' datatype and
    sorts numerically (WER, RTFx, rates, agreement, Size, # Languages, …)."""
    return [c for c in df.columns
            if c not in _NON_NUMERIC_COLS
            and pd.to_numeric(df[c], errors="coerce").notna().any()]


def _compute_medal_maps(df, cols):
    """Pre-search {column: {value: 🥇/🥈/🥉}} maps. WER is lower-better, RTFx
    higher-better; API-only RTFx (-1/≤0) is not ranked."""
    maps = {}
    for c in cols:
        numeric = pd.to_numeric(df[c], errors="coerce")
        if "RTFx" in c:
            numeric = numeric.where(numeric > 0)
        vals = numeric.dropna()
        if vals.empty:
            continue
        top = sorted(set(vals), reverse=("RTFx" in c))[:3]
        maps[c] = {v: MEDAL_ICONS[i] for i, v in enumerate(top)}
    return maps


def _style_table(df):
    """Return ``(value, datatype)`` for any leaderboard-style table. Every
    numeric column is kept numeric (datatype 'number' → sorts numerically) and
    shown via a Styler: NaN → 'NA', with a 🥇🥈🥉 appended for the pre-search
    medal values stashed on ``df.attrs`` (performance columns only). The model
    column renders as markdown; the Rank/Coverage/Rank Δ columns stay text."""
    numeric = _numeric_cols(df)
    datatype = ["markdown" if c in ("Model", "model")
                else ("number" if c in numeric else "str") for c in df.columns]
    if not numeric:
        return df, datatype
    maps = df.attrs.get("medal_maps", {})
    df = df.copy()
    fmts = {}
    for c in numeric:
        s = pd.to_numeric(df[c], errors="coerce")
        if "RTFx" in c:
            s = s.where(s > 0)  # API-only (-1) → NaN → 'NA'
        df[c] = s
        fmts[c] = _medal_formatter(maps.get(c, {}))  # empty map ⇒ no medal
    return df.style.format(fmts), datatype


def _styled_update(df):
    """gr.update for a finalized non-main table (Styler value + numeric datatype)."""
    value, datatype = _style_table(df)
    return gr.update(value=value, datatype=datatype)


def _finalize_table(df, metric_col, search_query, show_proprietary):
    """Shared pipeline for the non-main tables: proprietary filter, then a Rank
    column computed over the full (pre-search) order, then the search filter.
    Search never renumbers; toggling datasets/languages (which changes the sort
    upstream) does. Performance columns are kept numeric with pre-search medal
    maps on ``df.attrs`` (applied at display by _style_table) so they sort
    numerically."""
    df = df.copy()
    df = _apply_generic_proprietary(df, show_proprietary)
    model_col = df.columns[0]
    df = _add_rank_column(df, metric_col)
    # Medal maps over the full (pre-search) set so the podium stays with the same
    # models while searching, then apply the search filter.
    perf = _perf_cols(df)
    maps = _compute_medal_maps(df, perf)
    df = _apply_search_filter(df, search_query, model_col)
    df.attrs["medal_maps"] = maps
    df.attrs["perf_cols"] = perf
    return df


def filter_generic_table(df, search_query, show_proprietary):
    """Model-name search + proprietary filter, no Rank column (used by the
    Pareto plots, which only need the filtered point set)."""
    filtered = df.copy()
    if filtered.empty:
        return filtered
    model_col = filtered.columns[0]
    filtered = _apply_search_filter(filtered, search_query, model_col)
    filtered = _apply_generic_proprietary(filtered, show_proprietary)
    return filtered

def filter_longform_table(search_query, show_proprietary):
    return _finalize_table(longform_df, "Average WER ⬇️", search_query, show_proprietary)

# Private-data groupings: each shows two group averages and ranks by their mean.
PRIVATE_GROUPINGS = {
    "Scripted vs. Conversational": ("Avg Scripted", "Avg Conversational"),
    "US vs. Non-US":   ("Avg US", "Avg Non-US"),
}
DEFAULT_PRIVATE_GROUPING = "Scripted vs. Conversational"


def _private_view(search_query, show_proprietary, grouping):
    """Private-data table for the chosen grouping: shows the two group-average
    columns and ranks by their mean ('Average WER ⬇️'). Each group average is a
    macro-average of its datasets (VoiceArena is already folded into the
    conversational / non-US groups upstream), so the two groups get equal
    weight regardless of how many datasets each contains."""
    c1, c2 = PRIVATE_GROUPINGS.get(grouping, PRIVATE_GROUPINGS[DEFAULT_PRIVATE_GROUPING])
    df = private_data_df[["Model", c1, c2]].copy()

    def _grouped_avg(row):
        vals = [v for v in (pd.to_numeric(row[c1], errors="coerce"),
                            pd.to_numeric(row[c2], errors="coerce")) if not pd.isna(v)]
        return round(float(np.mean(vals)), 2) if vals else "NA"

    df["Average WER ⬇️"] = df.apply(_grouped_avg, axis=1)
    df = df[["Model", "Average WER ⬇️", c1, c2]]
    df = df.sort_values(by="Average WER ⬇️",
                        key=lambda col: pd.to_numeric(col, errors="coerce"),
                        na_position="last")
    return _finalize_table(df, "Average WER ⬇️", search_query, show_proprietary)


def _private_update(search_query, show_proprietary, grouping):
    """gr.update for the private table (Styler value + numeric datatype)."""
    return _styled_update(_private_view(search_query, show_proprietary, grouping))

def _pareto_dataset_choices():
    """WER dataset columns of the main leaderboard that can be averaged over
    (recognized per-dataset scores + private aggregates only, so stray CSV
    columns like 'avg' / 'Training data disclosure' don't leak in)."""
    return [c for c in original_df.columns if c in DATASET_COLUMNS]


PARETO_XMAX_DEFAULT = 10
# The multilingual Pareto x-axis: default view and slider cap. The cap reaches
# far enough for the higher-WER (lattice-scored) Hindi models when dragged.
MULTI_PARETO_XMAX_DEFAULT = 15
MULTI_PARETO_XMAX_MAX = 50
# RTFx (y-axis) bounds for the main-leaderboard WER-vs-RTFx Pareto. Log scale, so
# these are raw RTFx values. Raise PARETO_RTFX_YMAX if a faster model is clipped
# off the top (e.g. current max RTFx ≈ 20600).
PARETO_RTFX_YMIN = 10
PARETO_RTFX_YMAX = 50000
# The multilingual RTFx Pareto uses a lower range than the English one:
# multilingual models don't reach the very high throughputs some English-only
# models do, and the slowest (e.g. lattice-scored Hindi) dip below RTFx 10.
MULTI_PARETO_RTFX_YMIN = 5
MULTI_PARETO_RTFX_YMAX = 4000


def _pareto_scatter(points, y_higher_better, y_title, y_axis, title, y_hover_label, x_max):
    """Build a Pareto figure from a dataframe of points with ``_name``, ``_wer``
    and ``_y`` columns. Rows with a missing WER/y or a non-positive y are
    dropped. Lower WER is always better; the y direction is set by
    ``y_higher_better``. ``x_max`` caps the WER axis."""
    plot_df = points.dropna(subset=["_wer", "_y"]).copy()
    plot_df = plot_df[plot_df["_y"] > 0]

    # Pareto front: no other model dominates on both axes.
    wer = plot_df["_wer"].values
    yv = plot_df["_y"].values
    is_pareto = np.ones(len(wer), dtype=bool)
    for i in range(len(wer)):
        for j in range(len(wer)):
            if i == j:
                continue
            y_dominates = yv[j] >= yv[i] if y_higher_better else yv[j] <= yv[i]
            y_strictly = yv[j] > yv[i] if y_higher_better else yv[j] < yv[i]
            if wer[j] <= wer[i] and y_dominates and (wer[j] < wer[i] or y_strictly):
                is_pareto[i] = False
                break

    pareto_df = plot_df[is_pareto].sort_values("_wer")
    non_pareto_df = plot_df[~is_pareto]

    hovertemplate = ("<b>%{text}</b><br>WER: %{x}<br>"
                     + y_hover_label + ": %{y}<extra></extra>")

    fig = go.Figure()

    # Non-Pareto models: no text labels, name shown on hover
    fig.add_trace(go.Scatter(
        x=non_pareto_df["_wer"],
        y=non_pareto_df["_y"],
        mode="markers",
        marker=dict(size=8, color="lightblue", opacity=0.7),
        text=non_pareto_df["_name"],
        hovertemplate=hovertemplate,
        name="Other models",
    ))

    # Pareto front models: text labels always visible. Nudge the edge labels
    # inward (leftmost extends right, rightmost extends left) so they don't get
    # clipped at the plot edges; the rest stay centered above their marker.
    textpositions = ["top center"] * len(pareto_df)
    if textpositions:
        textpositions[0] = "top right"
        textpositions[-1] = "top left"

    fig.add_trace(go.Scatter(
        x=pareto_df["_wer"],
        y=pareto_df["_y"],
        mode="markers+text+lines",
        marker=dict(size=10, color="dodgerblue", symbol="star"),
        text=pareto_df["_name"],
        textposition=textpositions,
        textfont=dict(size=9),
        line=dict(dash="dash", color="dodgerblue", width=1),
        hovertemplate=hovertemplate,
        name="Pareto frontier",
    ))

    # X-range: capped at the user-chosen x_max (higher WER isn't practically
    # useful), with an adaptive lower bound so a low-WER subset still zooms in.
    # Models with WER > x_max simply fall off the right edge.
    if len(plot_df):
        wmin = plot_df["_wer"].min()
        lower = max(wmin - 0.5, 0)
        if lower >= x_max:  # every model is above the cap; show the full range
            lower = 0
        x_range = [lower, x_max]
    else:
        x_range = [0, x_max]

    fig.update_layout(
        title=title,
        xaxis_title="Average WER (lower is better)",
        yaxis_title=y_title,
        xaxis=dict(range=x_range),
        yaxis=y_axis,
        hovermode="closest",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
    )

    return fig


def _pareto_figure(selected_datasets, search_query, x_max,
                   y_col, y_higher_better, y_title, y_axis, title, y_hover_label):
    """Pareto plot from the main leaderboard: Average WER (x) vs ``y_col``.

    The WER axis is the macro-average over ``selected_datasets`` (defaulting to
    the version's default datasets); a model is plotted only if it has a value
    for every selected dataset and a positive ``y_col``. ``search_query``
    restricts to models whose name matches any comma-separated term.
    """
    df = original_df.copy()
    model_col = df.columns[0]

    # Restrict to searched models (comma-separated, case-insensitive, matched
    # against the plain model name).
    if search_query:
        terms = [t.strip().lower() for t in search_query.split(",") if t.strip()]
        if terms:
            df = df[df[model_col].apply(
                lambda cell: any(term in strip_html(cell).lower() for term in terms)
            )]

    if selected_datasets is None:
        selected_datasets = default_datasets
    wer_cols = [c for c in selected_datasets
                if c in df.columns and c not in EXCLUDED_AVG_COLS]

    # WER = macro-average over the selected datasets; NA if any selected dataset
    # is missing for the model (apples-to-apples, matching the leaderboard).
    def _row_wer(row):
        vals = []
        for c in wer_cols:
            v = pd.to_numeric(row[c], errors="coerce")
            if pd.isna(v):
                return np.nan
            vals.append(v)
        return round(np.mean(vals), 2) if vals else np.nan

    points = pd.DataFrame({
        "_name": df[model_col].apply(strip_html),
        "_wer": df.apply(_row_wer, axis=1) if wer_cols else np.nan,
        "_y": pd.to_numeric(df[y_col], errors="coerce"),
    })
    return _pareto_scatter(points, y_higher_better, y_title, y_axis, title, y_hover_label, x_max)


def create_pareto_plot(selected_datasets=None, search_query="", x_max=PARETO_XMAX_DEFAULT):
    """Pareto plot of Average WER vs RTFx (higher RTFx is better)."""
    return _pareto_figure(
        selected_datasets, search_query, x_max,
        y_col="RTFx ⬆️️",
        y_higher_better=True,
        y_title="RTFx (higher is better)",
        y_axis=dict(type="log", range=[np.log10(PARETO_RTFX_YMIN), np.log10(PARETO_RTFX_YMAX)]),
        title="Pareto Front: Average WER vs RTFx",
        y_hover_label="RTFx",
    )


def create_size_pareto_plot(selected_datasets=None, search_query="", x_max=PARETO_XMAX_DEFAULT):
    """Pareto plot of Average WER vs model size in B params (smaller is better).

    Only open models that report a size appear (API/proprietary models without
    a published parameter count are dropped)."""
    return _pareto_figure(
        selected_datasets, search_query, x_max,
        y_col="Size (B)",
        y_higher_better=False,
        y_title="Model size / B params (lower is better)",
        y_axis=dict(type="log"),
        title="Pareto Front: Average WER vs Model Size",
        y_hover_label="Size (B)",
    )


def render_pareto_plots(selected_datasets=None, search_query="", x_max=PARETO_XMAX_DEFAULT):
    """Build both Pareto figures (WER vs RTFx and WER vs size) from one set of
    controls, in the order [rtfx_plot, size_plot]."""
    return (
        create_pareto_plot(selected_datasets, search_query, x_max),
        create_size_pareto_plot(selected_datasets, search_query, x_max),
    )


def create_ref_error_agreement_plot(search_query="", show_proprietary=True,
                                     wer_col="wer_official",
                                     x_title="Voxpopuli WER (original with noisy references)",
                                     title="Reference-error agreement vs. Voxpopuli WER"):
    """Scatter of reference-error agreement (``rate`` from the benchmark-fitting
    dataset) vs a model's Voxpopuli WER (``wer_col``) from the same benchmark-fitting
    dataset. One point per model.

    The WER (``wer_official`` / ``wer_corrected``) is computed only on the
    relevant reference-error clips, so it lines up directly with ``rate``.
    Only models shown on the short-form leaderboard are plotted — i.e. those
    with a result for every default dataset — and the point set honours the
    shared model-name search and the "show proprietary" toggle."""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis=dict(title="Reference-error agreement (rate)", range=[-0.04, 1.04]),
        hovermode="closest",
        template="plotly_white",
    )
    if benchmark_fitting_df is None or "rate" not in benchmark_fitting_df.columns:
        fig.update_layout(title=f"{title} (data unavailable)")
        return fig

    eligible = _shortform_model_names()  # models with a result for every default dataset
    proprietary = _get_proprietary_models() if not show_proprietary else set()
    terms = [t.strip().lower() for t in (search_query or "").split(",") if t.strip()]

    names, xs, ys = [], [], []
    for _, row in benchmark_fitting_df.iterrows():
        name = row["model"]
        if name not in eligible:
            continue
        if terms and not any(t in name.lower() for t in terms):
            continue
        if not show_proprietary and name in proprietary:
            continue
        wer = pd.to_numeric(row.get(wer_col), errors="coerce")
        rate = pd.to_numeric(row.get("rate"), errors="coerce")
        if pd.isna(wer) or pd.isna(rate):
            continue
        names.append(name)
        xs.append(wer)
        ys.append(rate)

    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers",
        marker=dict(
            size=9,
            color=ys,                # higher reference-error agreement -> redder
            colorscale="YlOrRd",
            cmin=0, cmax=1,
            line=dict(width=0.6, color="#6b7683"),
            colorbar=dict(title="Ref-error<br>agreement"),
            showscale=True,
        ),
        text=names,
        hovertemplate="<b>%{text}</b><br>" + x_title + ": %{x}<br>Ref-error agreement: %{y:.3f}<extra></extra>",
        name="Models",
    ))
    return fig


def create_ref_error_table(search_query="", show_proprietary=True):
    """Table of reference-error agreement (``rate``) per model, with each model's Voxpopuli
    WER before/after reference cleaning (computed on the relevant clips only, from the
    benchmark-fitting dataset). Restricted to short-form leaderboard models; honours search / proprietary."""
    base_cols = ["Rank", "Model", "Ref-error agreement", "Voxpopuli WER", "Voxpopuli-AA-Cleaned WER", "Δ WER"]
    if benchmark_fitting_df is None or "rate" not in benchmark_fitting_df.columns:
        return pd.DataFrame(columns=base_cols)

    eligible = _shortform_model_names()
    proprietary = _get_proprietary_models() if not show_proprietary else set()
    terms = [t.strip().lower() for t in (search_query or "").split(",") if t.strip()]

    def _fmt(v):
        return round(float(v), 2) if v is not None and not pd.isna(v) else "NA"

    # Score over the full (pre-search) set so the Rank is computed before the
    # model-name search is applied — searching then hides rows but keeps each
    # model's original rank. The proprietary toggle still renumbers.
    scored = []
    for _, row in benchmark_fitting_df.iterrows():
        name = row["model"]
        if name not in eligible:
            continue
        if not show_proprietary and name in proprietary:
            continue
        rate = pd.to_numeric(row.get("rate"), errors="coerce")
        if pd.isna(rate):
            continue
        # WERs computed only on the relevant (reference-error) clips.
        wer_off = pd.to_numeric(row.get("wer_official"), errors="coerce")
        wer_corr = pd.to_numeric(row.get("wer_corrected"), errors="coerce")
        scored.append((float(rate), name, wer_off, wer_corr))

    scored.sort(key=lambda x: -x[0])

    def _delta(off, corr):
        # Δ = original − cleaned: positive means cleaning references lowers WER,
        # a higher number = the model benefits more from the cleaned references.
        if pd.isna(off) or pd.isna(corr):
            return "NA"
        return round(float(off) - float(corr), 2)

    rows = [
        {"Rank": i, "Model": make_clickable_model(name),
         "Ref-error agreement": round(rate, 3),
         "Voxpopuli WER": _fmt(wer_off),
         "Voxpopuli-AA-Cleaned WER": _fmt(wer_corr),
         "Δ WER": _delta(wer_off, wer_corr)}
        for i, (rate, name, wer_off, wer_corr) in enumerate(scored, start=1)
        if not terms or any(t in name.lower() for t in terms)
    ]
    return pd.DataFrame(rows)[base_cols] if rows else pd.DataFrame(columns=base_cols)


def render_benchmark_fitting_plots(search_query="", show_proprietary=True):
    """Section-1 outputs: the two reference-error scatters (original, cleaned)
    and the reference-error table, in that order."""
    return (
        create_ref_error_agreement_plot(search_query, show_proprietary,
                                        "wer_official", "Voxpopuli WER (original with noisy references)",
                                        "Reference-error agreement vs. Voxpopuli WER"),
        create_ref_error_agreement_plot(search_query, show_proprietary,
                                        "wer_corrected", "Voxpopuli-AA-Cleaned WER",
                                        "Reference-error agreement vs. Voxpopuli-AA-Cleaned WER"),
        create_ref_error_table(search_query, show_proprietary),
    )


# ----------------------------------------------------------------------------
# Rendering-agreement (spelling-copying / benchmaxing) section
# ----------------------------------------------------------------------------
def rendering_split_choices():
    """Split labels available in the rendering-agreement data, in a stable order."""
    return list(rendering_fitting_data.keys())


def rendering_default_splits():
    """Default-checked splits: everything except the non-clean VoxPopuli split."""
    return [s for s in rendering_split_choices() if s not in RENDERING_DEFAULT_OFF]


def _rendering_points(search_query, show_proprietary, selected_splits, apply_search=True):
    """Per-model rendering-agreement points after the shared filters.

    Returns (selected_labels, [ {model, avg, rates:{split:rate}, wer} ... ]).
    ``avg`` is the mean overall copy-rate over the selected splits the model has;
    ``wer`` is the model's WER averaged over the *same* selected splits (the
    split labels are the leaderboard's WER columns), or None. Restricted to
    models on the short-form leaderboard (a result for every default dataset).

    When ``apply_search`` is False the model-name search is skipped, so callers
    that assign a Rank can compute it over the full (pre-search) set and filter
    afterwards (keeping each model's original rank)."""
    labels = [s for s in rendering_split_choices() if s in set(selected_splits or [])]

    # model -> {split: overall rate}
    per_model = {}
    for label in labels:
        df = rendering_fitting_data.get(label)
        if df is None:
            continue
        for _, r in df.iterrows():
            rate = pd.to_numeric(r.get("rate"), errors="coerce")
            if not pd.isna(rate):
                per_model.setdefault(r["model"], {})[label] = float(rate)

    eligible = _shortform_model_names()
    proprietary = _get_proprietary_models() if not show_proprietary else set()
    terms = [t.strip().lower() for t in (search_query or "").split(",") if t.strip()]

    # WER averaged over the selected splits (split labels == leaderboard WER
    # columns), so the scatter's x-axis tracks the same dataset selection.
    model_col = original_df.columns[0]
    wer_cols = [l for l in labels if l in original_df.columns]
    wer_by_name = {}
    for _, row in original_df.iterrows():
        vals = [pd.to_numeric(row.get(c), errors="coerce") for c in wer_cols]
        vals = [v for v in vals if not pd.isna(v)]
        wer_by_name[strip_html(row[model_col])] = round(float(np.mean(vals)), 2) if vals else None

    points = []
    for model, rates in per_model.items():
        if model not in eligible:
            continue
        if not show_proprietary and model in proprietary:
            continue
        if apply_search and terms and not any(t in model.lower() for t in terms):
            continue
        if not rates:
            continue
        points.append({
            "model": model,
            "avg": round(float(np.mean(list(rates.values()))), 3),
            "rates": rates,
            "wer": wer_by_name.get(model),
        })
    return labels, points


def create_rendering_table(search_query="", show_proprietary=True, selected_splits=None):
    """Table of average spelling-copy rate per model over the selected splits
    (higher = more copying), most-copying first,
    with one column per selected split."""
    # Rank over the full (pre-search) set so searching keeps each model's
    # original rank; the search filter is applied when building the rows below.
    labels, points = _rendering_points(search_query, show_proprietary, selected_splits,
                                       apply_search=False)
    base_cols = ["Rank", "Model", "Avg rate"] + labels
    if not points:
        return pd.DataFrame(columns=base_cols)

    terms = [t.strip().lower() for t in (search_query or "").split(",") if t.strip()]
    points.sort(key=lambda p: -p["avg"])  # most-copying first
    rows = []
    for i, p in enumerate(points, start=1):
        if terms and not any(t in p["model"].lower() for t in terms):
            continue
        row = {"Rank": i, "Model": make_clickable_model(p["model"]),
               "Avg rate": p["avg"]}
        for label in labels:
            row[label] = round(p["rates"][label], 3) if label in p["rates"] else "NA"
        rows.append(row)
    return pd.DataFrame(rows)[base_cols] if rows else pd.DataFrame(columns=base_cols)


def create_rendering_scatter(search_query="", show_proprietary=True, selected_splits=None):
    """Scatter of average spelling-copy rate (y) vs Average WER (x, over the same
    selected splits). Diverging color centered at the ~0.5 chance line: pale near
    chance, red above (copies the reference), blue below. One point per short-form
    model."""
    _, points = _rendering_points(search_query, show_proprietary, selected_splits)
    fig = go.Figure()
    fig.update_layout(
        title="Spelling-copy rate vs Average WER",
        xaxis_title="Average WER (over selected splits)",
        yaxis=dict(title="Avg spelling-copy rate (higher = more copying)", range=[-0.04, 1.04]),
        hovermode="closest",
        template="plotly_white",
    )
    # Shade the "more copying" region above chance, and mark the chance line.
    fig.add_hrect(y0=0.5, y1=1.04, fillcolor="#d7301f", opacity=0.06,
                  line_width=0, layer="below")
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray", line_width=1,
                  annotation_text="≈ chance (50%)", annotation_position="top left")

    pts = [p for p in points if p["wer"] is not None]
    if not pts:
        return fig
    xs = [p["wer"] for p in pts]
    ys = [p["avg"] for p in pts]
    names = [p["model"] for p in pts]
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="markers",
        marker=dict(
            # Diverging scale centered on the 0.5 chance line: pale ~0.5,
            # red toward 1 (copies reference), blue toward 0 (avoids it).
            size=9, color=ys, colorscale="RdBu", reversescale=True, cmin=0, cmax=1,
            line=dict(width=0.6, color="#6b7683"),
            colorbar=dict(title="Copy<br>rate"), showscale=True,
        ),
        text=names,
        hovertemplate="<b>%{text}</b><br>Average WER: %{x}<br>Avg rate: %{y:.3f}<extra></extra>",
        name="Models",
    ))
    return fig


def render_rendering_fitting(search_query="", show_proprietary=True, selected_splits=None):
    """Build the rendering-agreement table update and scatter for the current
    controls, in the order [table_update, scatter_fig]."""
    df = create_rendering_table(search_query, show_proprietary, selected_splits)
    scatter = create_rendering_scatter(search_query, show_proprietary, selected_splits)
    return _styled_update(df), scatter


def _multilingual_pareto_points(search_query, show_proprietary, selected_display):
    """Point set for the multilingual Pareto plots: plain name, multilingual
    Average WER (over the selected languages), RTFx and model size — the same
    numbers as the overview table, after the shared search / proprietary filter."""
    codes = MULTI.get("codes", [])
    if selected_display is None:
        selected = {MULTI["display"][c] for c in codes}
    else:
        selected = set(selected_display)
    codes = [c for c in codes if MULTI["display"][c] in selected]

    df = _multilingual_overview_df(codes)
    df = filter_generic_table(df, search_query, show_proprietary)
    return pd.DataFrame({
        "_name": df["Model"].map(strip_html),
        "_wer": pd.to_numeric(df["Average WER ⬇️"], errors="coerce"),
        "_rtfx": pd.to_numeric(df["RTFx ⬆️️"], errors="coerce"),
        "_size": pd.to_numeric(df["Size (B)"], errors="coerce"),
    })


def create_multilingual_pareto_plot(search_query="", show_proprietary=True,
                                     selected_display=None, x_max=PARETO_XMAX_DEFAULT):
    """Pareto plot of multilingual Average WER vs RTFx (higher RTFx is better)."""
    p = _multilingual_pareto_points(search_query, show_proprietary, selected_display)
    points = pd.DataFrame({"_name": p["_name"], "_wer": p["_wer"], "_y": p["_rtfx"]})
    return _pareto_scatter(
        points,
        y_higher_better=True,
        y_title="RTFx (higher is better)",
        # Fixed RTFx bounds, capped lower than the main-leaderboard Pareto.
        y_axis=dict(type="log", range=[np.log10(MULTI_PARETO_RTFX_YMIN), np.log10(MULTI_PARETO_RTFX_YMAX)]),
        title="Multilingual Pareto: Average WER (selected languages) vs RTFx",
        y_hover_label="RTFx",
        x_max=x_max,
    )


def create_multilingual_size_pareto_plot(search_query="", show_proprietary=True,
                                         selected_display=None, x_max=PARETO_XMAX_DEFAULT):
    """Pareto plot of multilingual Average WER vs model size (smaller is better).

    Only open models that report a size appear (API/proprietary models without
    a published parameter count are dropped)."""
    p = _multilingual_pareto_points(search_query, show_proprietary, selected_display)
    points = pd.DataFrame({"_name": p["_name"], "_wer": p["_wer"], "_y": p["_size"]})
    return _pareto_scatter(
        points,
        y_higher_better=False,
        y_title="Model size / B params (lower is better)",
        y_axis=dict(type="log"),
        title="Multilingual Pareto: Average WER (selected languages) vs Model Size",
        y_hover_label="Size (B)",
        x_max=x_max,
    )


def render_multilingual_paretos(search_query="", show_proprietary=True,
                                selected_display=None, x_max=PARETO_XMAX_DEFAULT):
    """Both multilingual Pareto figures from one set of controls, in the order
    [rtfx_plot, size_plot]."""
    return (
        create_multilingual_pareto_plot(search_query, show_proprietary, selected_display, x_max),
        create_multilingual_size_pareto_plot(search_query, show_proprietary, selected_display, x_max),
    )


def _sync_multilingual_langs(search_query, show_proprietary, selected_langs, zoom, multi_pareto_xmax):
    """Shared handler for the two (kept-in-sync) multilingual language selectors.

    Rebuilds the multilingual table and both multilingual Pareto plots for the
    given language selection, and returns a value-update to mirror that
    selection onto the *other* selector. Returns
    ``(table_update, rtfx_fig, size_fig, mirror_update)``."""
    table = render_multilingual(search_query, show_proprietary, selected_langs, zoom)
    rtfx_fig, size_fig = render_multilingual_paretos(
        search_query, show_proprietary, selected_langs, multi_pareto_xmax)
    return table, rtfx_fig, size_fig, gr.update(value=selected_langs)


def _english_help_text(datasets):
    """User-facing note describing the optional 🇬🇧 English toggle, listing the
    version's default datasets (the same set the main leaderboard averages)."""
    return (
        f"Toggle **🇬🇧 English** (off by default) to include English alongside the other "
        f"languages. Its score is the average over the same datasets as the main leaderboard: "
        f"{', '.join(datasets)}."
    )


def _tab_title_with_link(title_md, slug, md_classes="markdown-text"):
    """Render a tab's title markdown with a small 🔗 link icon inline, right after
    the heading, that copies a shareable deep link to this tab.

    Copies ``<app-origin>/?tab=<slug>`` — the app's own URL (the direct
    ``*.hf.space`` domain, or localhost). We can't use the prettier
    ``huggingface.co/spaces/...`` URL: on the wrapped Space page the app runs in
    a cross-origin iframe, so JS can neither read nor change the parent address
    bar. The copied ``?tab=`` link still lands on the right tab (HF forwards
    query params into the iframe on load). The click is handled by the delegated
    listener in demo.load (copy + fire the "copied" toast)."""
    # A <span> (not <a>): Gradio's frontend has a click router that follows <a>
    # links via JS — which preventDefault can't stop — reloading the page. A span
    # has no such behaviour. The slug rides in the id (ids survive the markdown
    # sanitizer, unlike data-* attributes); the click is handled in demo.load.
    icon = (f' <span class="tab-link-icon" id="copy-tab-{slug}" '
            f'title="Copy link to this tab" role="button">🔗</span>')
    # Inject the icon at the end of the first (heading) line so it sits inline,
    # just to the right of the title text. lstrip first: several titles come
    # from triple-quoted constants that start with a newline, which would
    # otherwise put the icon on an empty line *above* the heading.
    first, sep, rest = title_md.lstrip("\n").partition("\n")
    return gr.Markdown(first + icon + sep + rest, elem_classes=md_classes)


# Render the inline copy-link icon subtly (an <a>, not a button).
_TAB_LINK_CSS = """
.tab-link-icon {
    text-decoration: none; font-size: 0.8em; opacity: 0.45; cursor: pointer;
    margin-left: 0.35em; vertical-align: middle; user-select: none;
}
.tab-link-icon:hover { opacity: 1; }
.hidden-trigger { display: none !important; }
"""


with gr.Blocks(css=LEADERBOARD_CSS + _TAB_LINK_CSS) as demo:
    gr.HTML(BANNER, elem_id="banner")
    gr.HTML(TTS_PROMO_BANNER, elem_id="tts-promo-banner")
    gr.Markdown(INTRODUCTION_TEXT, elem_classes="markdown-text")

    with gr.Row():
        version_dropdown = gr.Dropdown(
            choices=get_version_choices(),
            value=LATEST_VERSION,
            label="Version",
            scale=1,
            min_width=200,
        )

    search_box = gr.Textbox(
        label="Search models",
        placeholder="Filter by model name — separate multiple terms with commas, e.g. whisper, parakeet",
    )
    with gr.Row():
        show_proprietary_checkbox = gr.Checkbox(
            label="Show proprietary (API) models",
            value=True,
            elem_id="show-proprietary-checkbox"
        )
        # show_llm_checkbox = gr.Checkbox(
        #     label="LLM-capabilities (e.g., prompt, translation, etc)",
        #     value=False,
        #     elem_id="show-alm-checkbox"
        # )

    with gr.Tabs(elem_classes="tab-buttons") as tabs:
        with gr.TabItem("🏅 Leaderboard", elem_id="od-benchmark-tab-table", id=0):
            toggleable_columns = _toggleable_columns(list(original_df.columns), default_datasets)
            default_columns = [c for c in toggleable_columns if c in default_datasets or c == "RTFx ⬆️️"]
            _compute_default_rank()
            def _columns_help_text(datasets):
                return (
                    f"**Select columns to display:**\n"
                    f"- Toggling datasets will change the Average WER. Default datasets: {', '.join(datasets)}.\n"
                    f"- **Rank Δ** shows how the ranking changes compared to the average over the default datasets.\n"
                    f"- **Private (scripted)** and **Private (conversational)** columns show aggregated WER on private datasets from [Appen Inc.](https://huggingface.co/AppenAIResearch), [DataoceanAI](https://huggingface.co/DataoceanAI1), and [Voice Arena](https://huggingface.co/VoiceArena) (see the 'Private data' tab for more info).\n"
                    f"- We would like to thank [Voice Arena](https://huggingface.co/VoiceArena) for providing 'Voice Arena Monsoon' (conversational English with Indian accent) specificially for this leaderboard, and [Artificial Analysis](https://huggingface.co/ArtificialAnalysis) for preparing 'Earnings22-Cleaned-AA-chunked' and 'Voxpopuli-AA-Cleaned' 🙏\n"
                )
            columns_help_md = gr.Markdown(_columns_help_text(default_datasets))
            column_checkboxes = gr.CheckboxGroup(
                choices=toggleable_columns,
                value=default_columns,
                label="Columns",
            )
            initial_df = filter_main_table("", True, False, default_columns)  # False for show_llm (uncomment show_llm_checkbox to use)
            _lb_val, _lb_dt = _style_table(initial_df)
            leaderboard_table = gr.components.Dataframe(
                value=_lb_val,
                datatype=_lb_dt,
                elem_id="leaderboard-table",
                interactive=False,
                visible=True,
                wrap=False,
            )

            # Uncomment show_llm_checkbox in filter_inputs for show_llm feature
            filter_inputs = [search_box, show_proprietary_checkbox, gr.Checkbox(value=False, visible=False), column_checkboxes]  # Hidden checkbox placeholder for show_llm
            # filter_inputs = [search_box, show_proprietary_checkbox, show_llm_checkbox, column_checkboxes]  # Use this line instead when enabling show_llm feature
            column_checkboxes.change(_main_table_update, inputs=filter_inputs, outputs=leaderboard_table)

        with gr.TabItem("🌍 Multilingual", elem_id="multilingual-benchmark-tab-table", id=1):
            _tab_title_with_link(MULTILINGUAL_TAB_TEXT, "multilingual")

            gr.Markdown(
                "**Select languages** to include in the ranking. The **Average WER** is the "
                "mean over the selected languages, and a model is ranked only if it supports "
                "**all** of them (apples-to-apples over the same set).\n\n"
                "Models that cover only *some* of the selected languages aren't dropped — they "
                "appear below the ranked models as unranked rows (Average WER `NA`), with `NA` "
                "in the languages they don't cover. The **Coverage** column (e.g. `3/5`) shows "
                "how many of the selected languages each model supports.\n\n"
                "Use **Language dataset breakdown** to break down the results for a single language's per-dataset "
                "results; the other languages are hidden when specifying a single language.\n\n " \
                "🇮🇳 Hindi contains public and private splits of conversational speech provided by [Voice Arena](https://huggingface.co/VoiceArena), which were collected under similar conditions but with different speakers ([blog](https://huggingface.co/blog/open-asr-leaderboard-global-south))."
            )

            multilingual_english_help_md = gr.Markdown(_english_help_text(default_datasets))

            # All language choices (English included), and the default-checked
            # subset (English and Armenian off by default).
            multilingual_lang_display = [MULTI["display"][c] for c in MULTI["codes"]]
            multilingual_lang_default = [MULTI["display"][c] for c in MULTI["codes"]
                                         if c not in (ENGLISH_CODE, ARMENIAN_CODE)]

            with gr.Row():
                multilingual_lang_checkboxes = gr.CheckboxGroup(
                    choices=multilingual_lang_display,
                    value=multilingual_lang_default,
                    label="Languages",
                )
            with gr.Row():
                multilingual_zoom = gr.Dropdown(
                    choices=[OVERVIEW_LABEL] + multilingual_lang_display,
                    value=OVERVIEW_LABEL,
                    label="Language dataset breakdown",
                    scale=1,
                    min_width=280,
                )

            _init_multi_df, _init_multi_dt = _multilingual_view(
                "", True, multilingual_lang_default, OVERVIEW_LABEL
            )
            multilingual_table = gr.components.Dataframe(
                value=_init_multi_df,
                datatype=_init_multi_dt,
                elem_id="multilingual-table",
                interactive=False,
                visible=True,
                wrap=True,
            )

            multilingual_control_inputs = [
                search_box,
                show_proprietary_checkbox,
                multilingual_lang_checkboxes,
                multilingual_zoom,
            ]
            # The language selector's change handler is wired below, after the
            # Pareto components exist (it keeps the two selectors in sync). The
            # zoom dropdown only affects the table.
            multilingual_zoom.change(
                render_multilingual,
                inputs=multilingual_control_inputs,
                outputs=multilingual_table,
            )

            # Pareto plots for the multilingual average (over the selected
            # languages) vs RTFx and vs model size. They have their OWN language
            # selector right here so users don't have to scroll back up to the
            # table's checkboxes.
            gr.Markdown("### Pareto Fronts: multilingual Average WER vs RTFx and Model Size\nAverage WER is taken over the languages selected **below** (a model is included only if it covers all of them). Names are shown for frontier models; hover over the rest. The size plot only includes open models that report a parameter count.")
            multilingual_pareto_lang_checkboxes = gr.CheckboxGroup(
                choices=multilingual_lang_display,
                value=multilingual_lang_default,
                label="Languages to average over",
            )
            multilingual_pareto_xmax_slider = gr.Slider(
                minimum=2,
                maximum=MULTI_PARETO_XMAX_MAX,
                value=MULTI_PARETO_XMAX_DEFAULT,
                step=0.5,
                label="Max WER shown on x-axis",
            )
            _init_multi_rtfx, _init_multi_size = render_multilingual_paretos(
                "", True, multilingual_lang_default, MULTI_PARETO_XMAX_DEFAULT
            )
            multilingual_pareto_plot = gr.Plot(value=_init_multi_rtfx)
            multilingual_size_pareto_plot = gr.Plot(value=_init_multi_size)

            multilingual_pareto_inputs = [
                search_box,
                show_proprietary_checkbox,
                multilingual_pareto_lang_checkboxes,
                multilingual_pareto_xmax_slider,
            ]
            multilingual_pareto_outputs = [multilingual_pareto_plot, multilingual_size_pareto_plot]
            multilingual_pareto_xmax_slider.change(
                render_multilingual_paretos,
                inputs=multilingual_pareto_inputs,
                outputs=multilingual_pareto_outputs,
            )

            # Keep the table's and the Pareto's language selectors in sync:
            # editing either rebuilds the table and both plots, and mirrors the
            # selection onto the other selector. (A programmatic value update via
            # outputs does not re-fire the other selector's change event, so
            # there is no feedback loop.)
            multilingual_lang_checkboxes.change(
                _sync_multilingual_langs,
                inputs=[search_box, show_proprietary_checkbox, multilingual_lang_checkboxes,
                        multilingual_zoom, multilingual_pareto_xmax_slider],
                outputs=[multilingual_table, multilingual_pareto_plot,
                         multilingual_size_pareto_plot, multilingual_pareto_lang_checkboxes],
            )
            multilingual_pareto_lang_checkboxes.change(
                _sync_multilingual_langs,
                inputs=[search_box, show_proprietary_checkbox, multilingual_pareto_lang_checkboxes,
                        multilingual_zoom, multilingual_pareto_xmax_slider],
                outputs=[multilingual_table, multilingual_pareto_plot,
                         multilingual_size_pareto_plot, multilingual_lang_checkboxes],
            )

        with gr.TabItem("📝 Long-form", elem_id="longform-benchmark-tab-table", id=2):
            _tab_title_with_link(LONGFORM_TAB_TEXT, "longform")

            _lf_val, _lf_dt = _style_table(filter_longform_table("", True))
            longform_table = gr.components.Dataframe(
                value=_lf_val,
                datatype=_lf_dt,
                elem_id="longform-table",
                interactive=False,
                visible=True,
            )

        with gr.TabItem("🔒 Private data", elem_id="private-data-benchmark-tab-table", id=3):
            _tab_title_with_link(PRIVATE_DATA_TAB_TEXT, "private")

            private_grouping = gr.Radio(
                choices=list(PRIVATE_GROUPINGS.keys()),
                value=DEFAULT_PRIVATE_GROUPING,
                label="Grouping — Average WER is the mean of the two columns shown",
            )
            _pd_val, _pd_dt = _style_table(_private_view("", True, DEFAULT_PRIVATE_GROUPING))
            private_data_table = gr.components.Dataframe(
                value=_pd_val,
                datatype=_pd_dt,
                elem_id="private-data-table",
                interactive=False,
                visible=True,
            )
            private_grouping.change(
                _private_update,
                inputs=[search_box, show_proprietary_checkbox, private_grouping],
                outputs=private_data_table,
            )

        with gr.TabItem("📊 Pareto", elem_id="pareto-tab", id=4):
            _tab_title_with_link("# Pareto Fronts\nModels on a Pareto frontier achieve the best trade-off between accuracy (WER) and, respectively, **speed** (RTFx, higher is better) and **model size** (B params, smaller is better). Names are shown for frontier models; hover over other points to see their names.\n\nSelect which datasets the Average WER is computed over — a model is plotted only if it has a score for every selected dataset. The size plot only includes open models that report a parameter count.", "pareto")

            pareto_dataset_choices = _pareto_dataset_choices()
            pareto_default_datasets = [c for c in pareto_dataset_choices if c in default_datasets]
            pareto_dataset_checkboxes = gr.CheckboxGroup(
                choices=pareto_dataset_choices,
                value=pareto_default_datasets,
                label="Datasets to average over",
            )
            pareto_xmax_slider = gr.Slider(
                minimum=2,
                maximum=16,
                value=PARETO_XMAX_DEFAULT,
                step=0.5,
                label="Max WER shown on x-axis",
            )
            pareto_plot = gr.Plot(
                value=create_pareto_plot(pareto_default_datasets, "", PARETO_XMAX_DEFAULT)
            )
            pareto_size_plot = gr.Plot(
                value=create_size_pareto_plot(pareto_default_datasets, "", PARETO_XMAX_DEFAULT)
            )

            pareto_inputs = [pareto_dataset_checkboxes, search_box, pareto_xmax_slider]
            pareto_outputs = [pareto_plot, pareto_size_plot]
            pareto_dataset_checkboxes.change(
                render_pareto_plots, inputs=pareto_inputs, outputs=pareto_outputs,
            )
            pareto_xmax_slider.change(
                render_pareto_plots, inputs=pareto_inputs, outputs=pareto_outputs,
            )

        with gr.TabItem("🧩 Benchmark fitting", elem_id="benchmark-fitting-tab", id=5):
            _tab_title_with_link(
                "# Benchmark fitting", "benchmark-fitting",
            )
            gr.Markdown(
                "In collaboration with [Hume AI](https://huggingface.co/HumeAI), this section quantifies different ways a model may over-fit a benchmark dataset, with higher scores indicating a higher fit. " \
                "Scripts for reproducing the raw results can be found on [GitHub](https://github.com/huggingface/open_asr_leaderboard/tree/main/benchmark_fitting).\n\n"
                "**Jump to:**\n\n" \
                "1. [Outputting incorrect reference transcripts](#bf-ref-errors) (VoxPopuli case study)\n" \
                "2. [Copying spelling conventions](#bf-spelling)\n\n" \
                "⚠️ **IMPORTANT: A higher score does not imply that a model trained on the test set.** There are various factors that contribute to the score." \
                " For instance, some form of benchmark fitting is almost inevitable when training data overlaps with the benchmark's characteristics (e.g. the corresponding train split), as models will mimic behavior they've seen during training." \
                " This highlights the importance of held-out sets for measuring untainted model performance, which is why we introduced the 'Private Data' tab." \
                " For more information on this analysis, check out our [blog post](https://huggingface.co/blog/asr-benchmark-optimization) and Hume AI's [technical report](https://huggingface.co/papers/2608.19936).\n\n"
                "<div id=\"bf-ref-errors\"></div>\n\n"
                "## 1. Outputting incorrect reference transcripts (VoxPopuli case study)\n"
                "VoxPopuli is known to contain a high number of transcription errors. This is why Artificial Analysis released a " \
                "[cleaned version](https://huggingface.co/datasets/ArtificialAnalysis/VoxPopuli-Cleaned-AA), which is used in this " \
                "leaderboard as `Voxpopuli-AA-Cleaned`.\n\n" \
                "This analysis quantifies how often a model outputs the incorrect reference transcript from the original VoxPopuli dataset (`VoxPopuli` in this leaderboard), which we call **reference-error agreement**.\n\nThe scatterplot below shows:\n" \
                "- x-axis: original Voxpopuli WER (on the same subset of clips kept in `Voxpopuli-AA-Cleaned`)\n" \
                "- y-axis: reference-error agreement (the rate at which a model outputs the same incorrect reference transcript)\n\n" \
                "Note how models with a lower WER on the original Voxpopuli dataset (x-axis) have a higher reference-error agreement (y-axis)."
            )
            _init_bench_orig, _init_bench_clean, _init_bench_table = render_benchmark_fitting_plots()
            benchmark_fitting_plot = gr.Plot(value=_init_bench_orig)
            gr.Markdown(
                "Below, the same reference-error agreement is plotted against the "
                "`Voxpopuli-AA-Cleaned` WER. **Note how models with a higher reference-error agreement shift towards the center**, namely they are no longer 'rewarded' for outputting incorrect reference transcripts." \
            )
            benchmark_fitting_cleaned_plot = gr.Plot(value=_init_bench_clean)
            gr.Markdown("Per-model reference-error agreement (higher = more often reproduces the incorrect reference), with each model's original and cleaned VoxPopuli WER on the subset of 628 clips within `Voxpopuli-AA-Cleaned`.\n\n" \
            "Δ WER = (original - cleaned) with **higher being better**. All models improve thanks to the cleaned references, and a higher number indicates that a model benefits more from the cleaned transcripts and is less likely to reproduce incorrect reference transcripts.")
            _re_val, _re_dt = _style_table(_init_bench_table)
            ref_error_table = gr.components.Dataframe(
                value=_re_val,
                datatype=_re_dt,
                elem_id="ref-error-table",
                interactive=False,
                visible=True,
            )

            gr.Markdown(
                "<div id=\"bf-spelling\"></div>\n\n"
                "## 2. Copying spelling conventions\n"
                "This analysis quantifies how often a model reproduces the reference's exact "
                "**spelling / rendering** (American vs. British English, initialisms, numbers, lexical choices) "
                "rather than a valid alternative, for example `colour`/`color`, `Mr.`/`mister`, `T. V.`/`TV`, `twenty`/`20`, and `e-mail`/`email`. In theory, models should consistently prefer one spelling over another, or alternate between them at roughly random rates. If models systematically switch to match what is in each benchmark's reference transcript, that suggest the models are picking up on which spelling the test expects.\n\n"
                "Below we plot each model's WER (x-axis) against the copy rate averaged over the selected splits. "
                "**Higher = more copying**"
            )
            rendering_split_checkboxes = gr.CheckboxGroup(
                choices=rendering_split_choices(),
                value=rendering_default_splits(),
                label="Splits to average over",
            )
            _init_rendering_scatter = create_rendering_scatter(
                "", True, rendering_default_splits())
            rendering_scatter_plot = gr.Plot(value=_init_rendering_scatter)
            _init_rendering_df = create_rendering_table("", True, rendering_default_splits())
            _rt_val, _rt_dt = _style_table(_init_rendering_df)
            rendering_table = gr.components.Dataframe(
                value=_rt_val,
                datatype=_rt_dt,
                elem_id="rendering-fitting-table",
                interactive=False,
                visible=True,
            )

            rendering_inputs = [search_box, show_proprietary_checkbox, rendering_split_checkboxes]
            rendering_outputs = [rendering_table, rendering_scatter_plot]
            rendering_split_checkboxes.change(
                render_rendering_fitting, inputs=rendering_inputs, outputs=rendering_outputs,
            )

        with gr.TabItem("🤗 About", elem_id="od-benchmark-tab-table", id=6):
            _tab_title_with_link(METRICS_TAB_TEXT, "about")

    def _refresh_all_tables(search_query, show_proprietary, show_llm, selected_columns,
                            selected_langs, zoom, pareto_datasets, pareto_xmax,
                            multi_pareto_langs, multi_pareto_xmax, rendering_splits,
                            private_grouping):
        """Re-apply the current search/proprietary filters to every tab's table.

        Gradio does not repaint components inside a hidden Tab until it becomes
        active, so re-run all filters whenever the user switches tabs to make
        sure the currently displayed table always reflects the latest filter
        state (e.g. "Show proprietary models") instead of a stale value.
        """
        main = _main_table_update(search_query, show_proprietary, show_llm, selected_columns)
        multi = render_multilingual(search_query, show_proprietary, selected_langs, zoom)
        longform = _styled_update(filter_longform_table(search_query, show_proprietary))
        private = _private_update(search_query, show_proprietary, private_grouping)
        # The Pareto plots follow the same model-name search; dataset/language
        # selection and x-axis cap are driven by their own controls.
        pareto, pareto_size = render_pareto_plots(pareto_datasets, search_query, pareto_xmax)
        multi_pareto, multi_pareto_size = render_multilingual_paretos(
            search_query, show_proprietary, multi_pareto_langs, multi_pareto_xmax)
        bench, bench_clean, bench_table = render_benchmark_fitting_plots(search_query, show_proprietary)
        rendering_table_upd, rendering_scatter = render_rendering_fitting(
            search_query, show_proprietary, rendering_splits)
        return (main, multi, longform, private, pareto, pareto_size, multi_pareto,
                multi_pareto_size, bench, bench_clean, _styled_update(bench_table),
                rendering_table_upd, rendering_scatter)

    # Inputs for the shared refresh: the main-tab filter inputs plus the
    # multilingual language selection / zoom state and the Pareto / rendering controls.
    refresh_inputs = filter_inputs + [multilingual_lang_checkboxes, multilingual_zoom,
                                      pareto_dataset_checkboxes, pareto_xmax_slider,
                                      multilingual_pareto_lang_checkboxes,
                                      multilingual_pareto_xmax_slider,
                                      rendering_split_checkboxes,
                                      private_grouping]

    # Wire the shared search box / proprietary checkbox to every data tab.
    # Use a single listener per trigger (instead of one per table) so typing
    # in the search box doesn't queue up 4x the work per keystroke — on
    # Spaces' limited/shared queue this backlog can make the UI appear stuck
    # "processing" indefinitely.
    all_tables_outputs = [leaderboard_table, multilingual_table, longform_table, private_data_table, pareto_plot, pareto_size_plot, multilingual_pareto_plot, multilingual_size_pareto_plot, benchmark_fitting_plot, benchmark_fitting_cleaned_plot, ref_error_table, rendering_table, rendering_scatter_plot]
    # Debounce the search box so we don't recompute on every keystroke.
    search_box.change(_refresh_all_tables, inputs=refresh_inputs, outputs=all_tables_outputs, trigger_mode="always_last")
    show_proprietary_checkbox.change(_refresh_all_tables, inputs=refresh_inputs, outputs=all_tables_outputs)

    tabs.select(
        fn=_refresh_all_tables,
        inputs=refresh_inputs,
        outputs=all_tables_outputs,
    )

    def _on_version_change(version_id):
        """Reload all data sources for the selected version and refresh every tab."""
        global original_df, longform_df, private_data_df, benchmark_fitting_df, rendering_fitting_data
        global private_scripted_map, private_conversational_map
        global csv_results, multilingual_csv_path, longform_csv_path, appen_csv_path, dataocean_csv_path
        global voicearena_csv_path, voxpopuli_fitting_csv_path, rendering_fitting_csv_paths, default_datasets

        try:
            (
                new_csv, new_multi, new_longform, new_appen, new_dataocean, new_voicearena,
                new_voxpopuli_fitting, new_rendering_fitting, new_default_datasets,
            ) = load_all_info_for_version(version_id)

            # --- Update default_datasets before rebuilding any dataframes ---
            if new_default_datasets is not None:
                default_datasets = new_default_datasets

            # --- Rebuild English short-form ---
            if new_csv is not None and Path(new_csv).exists():
                csv_results = new_csv
                df = pd.read_csv(csv_results)
                for col in df.columns:
                    if col == "model":
                        df[col] = df[col].apply(lambda x: x.replace(x, make_clickable_model(x)))
                    else:
                        df[col] = df[col].apply(lambda x: formatter(x, col))
                df.rename(columns=column_names, inplace=True)
                if "Avg. WER" in df.columns:
                    df = df.drop(columns=["Avg. WER"])
                for _drop_col in ["avg cleaned", "avg original"]:
                    if _drop_col in df.columns:
                        df = df.drop(columns=[_drop_col])
                df = _compute_average_wer_from_default_datasets(df)
                df = df.sort_values(by='Average WER ⬇️', key=lambda col: pd.to_numeric(col, errors="coerce"), na_position="last")
                original_df = df

            # --- Rebuild multilingual ---
            if new_multi is not None:
                multilingual_csv_path = new_multi
                build_multilingual_data()

            # --- Rebuild longform ---
            if new_longform is not None:
                longform_csv_path = new_longform
                longform_df = create_longform_dataframe()

            # --- Reload benchmark-fitting data (may be absent for old versions) ---
            voxpopuli_fitting_csv_path = new_voxpopuli_fitting
            benchmark_fitting_df = _load_benchmark_fitting_df()
            rendering_fitting_csv_paths = new_rendering_fitting
            rendering_fitting_data = _load_rendering_fitting_data()

            # --- Rebuild private data ---
            if new_appen is not None:
                appen_csv_path = new_appen
            if new_dataocean is not None:
                dataocean_csv_path = new_dataocean
            # Set unconditionally: versions predating VoiceArena return None, so
            # switching to them must clear it rather than keep a stale path.
            voicearena_csv_path = new_voicearena
            private_data_df, private_scripted_map, private_conversational_map = create_private_data_dataframe()

            # Add private-data columns back onto the main leaderboard
            original_df["Private (scripted)"] = original_df[original_df.columns[0]].apply(
                lambda x: private_scripted_map.get(_get_plain_model_name(x), "NA")
            )
            original_df["Private (conversational)"] = original_df[original_df.columns[0]].apply(
                lambda x: private_conversational_map.get(_get_plain_model_name(x), "NA")
            )

            # Refresh the English "language" now that original_df is complete
            # (English average matches this version's leaderboard average).
            _inject_english(MULTI)

            # Re-fold the VoiceArena private Hindi set into the Hindi breakdown
            # (build_multilingual_data above rebuilt MULTI from scratch).
            _inject_hindi_private(MULTI)

            # Recompute default rank for the new data
            global _default_rank
            _default_rank = {}
            _compute_default_rank()

            # Recompute column choices for the new version's dataframe
            new_toggleable = _toggleable_columns(list(original_df.columns), default_datasets)
            new_default = [c for c in new_toggleable if c in default_datasets or c == "RTFx ⬆️️"]

            new_main = _main_table_update("", True, False, new_default)

            # Reset the multilingual controls to the new version's languages
            # (all languages except English and Armenian selected, overview
            # mode) and rebuild its table.
            new_lang_display = [MULTI["display"][c] for c in MULTI["codes"]]
            new_lang_default = [MULTI["display"][c] for c in MULTI["codes"]
                                 if c not in (ENGLISH_CODE, ARMENIAN_CODE)]
            new_multi_view = render_multilingual("", True, new_lang_default, OVERVIEW_LABEL)

            # Reset the Pareto dataset selection to the new version's defaults
            # and the x-axis cap to its default.
            new_pareto_choices = _pareto_dataset_choices()
            new_pareto_default = [c for c in new_pareto_choices if c in default_datasets]
            new_pareto, new_pareto_size = render_pareto_plots(new_pareto_default, "", PARETO_XMAX_DEFAULT)
            new_multi_pareto, new_multi_pareto_size = render_multilingual_paretos(
                "", True, new_lang_default, MULTI_PARETO_XMAX_DEFAULT)
            _bench_orig, _bench_clean, _bench_table = render_benchmark_fitting_plots("", True)
            return (
                new_main,
                new_multi_view,
                _styled_update(filter_longform_table("", True)),
                _private_update("", True, DEFAULT_PRIVATE_GROUPING),
                new_pareto,
                new_pareto_size,
                gr.update(choices=new_toggleable, value=new_default),
                gr.update(value=_columns_help_text(default_datasets)),
                gr.update(value=""),
                gr.update(choices=new_lang_display, value=new_lang_default),
                gr.update(choices=[OVERVIEW_LABEL] + new_lang_display, value=OVERVIEW_LABEL),
                gr.update(choices=new_pareto_choices, value=new_pareto_default),
                gr.update(value=PARETO_XMAX_DEFAULT),
                new_multi_pareto,
                new_multi_pareto_size,
                gr.update(value=MULTI_PARETO_XMAX_DEFAULT),
                gr.update(choices=new_lang_display, value=new_lang_default),
                gr.update(value=_english_help_text(default_datasets)),
                _bench_orig, _bench_clean, _styled_update(_bench_table),
                gr.update(choices=rendering_split_choices(), value=rendering_default_splits()),
                *render_rendering_fitting("", True, rendering_default_splits()),
                gr.update(value=DEFAULT_PRIVATE_GROUPING),
            )
        except Exception as e:
            print(f"Error switching version: {e}")
            # Return current state unchanged
            return (
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            )

    version_dropdown.change(
        fn=_on_version_change,
        inputs=[version_dropdown],
        outputs=[leaderboard_table, multilingual_table, longform_table, private_data_table, pareto_plot, pareto_size_plot, column_checkboxes, columns_help_md, search_box, multilingual_lang_checkboxes, multilingual_zoom, pareto_dataset_checkboxes, pareto_xmax_slider, multilingual_pareto_plot, multilingual_size_pareto_plot, multilingual_pareto_xmax_slider, multilingual_pareto_lang_checkboxes, multilingual_english_help_md, benchmark_fitting_plot, benchmark_fitting_cleaned_plot, ref_error_table, rendering_split_checkboxes, rendering_table, rendering_scatter_plot, private_grouping],
    )

    # Deep-linking: open a specific tab via ?tab=<slug> in the URL, e.g.
    # https://huggingface.co/spaces/hf-audio/open_asr_leaderboard?tab=multilingual
    # (Query params are forwarded by HF into the Space iframe; URL hashes are not.)
    TAB_SLUGS = {
        "leaderboard": 0,
        "multilingual": 1,
        "longform": 2,
        "private": 3,
        "pareto": 4,
        "benchmark-fitting": 5,
        "about": 6,
    }

    def _select_tab_from_url(request: gr.Request):
        slug = (request.query_params.get("tab") or "").lower()
        return gr.Tabs(selected=TAB_SLUGS.get(slug, 0))

    demo.load(_select_tab_from_url, inputs=None, outputs=tabs)

    # Hidden button fired by the inline 🔗 icons (via JS) to show the copy toast.
    _copy_toast_trigger = gr.Button("", elem_id="copy-toast-trigger",
                                    elem_classes="hidden-trigger")
    _copy_toast_trigger.click(
        fn=lambda: gr.Info("Tab link copied to clipboard!", duration=2),
        inputs=None,
        outputs=None,
    )

    # Reflect tab clicks into the URL's ?tab= query param so the address bar
    # always shows a directly-pasteable deep link (round-trips with the
    # inbound handler above). Uses replaceState so it doesn't spam history.
    _SLUG_ORDER = list(TAB_SLUGS.keys())
    demo.load(
        None,
        None,
        None,
        js=f"""
        () => {{
          const slugs = {json.dumps(_SLUG_ORDER)};
          // Delegated listeners so they survive re-renders and load-order timing.
          // 1) Tab clicks -> ?tab= query param.
          document.addEventListener('click', (e) => {{
            const nav = document.querySelector('.tab-buttons .tab-nav') ||
                        document.querySelector('.tab-buttons [role="tablist"]');
            if (!nav) return;
            const btn = e.target.closest('button');
            if (!btn || !nav.contains(btn)) return;
            const i = Array.from(nav.querySelectorAll('button')).indexOf(btn);
            if (i < 0 || !slugs[i]) return;
            const url = new URL(window.location.href);
            url.searchParams.set('tab', slugs[i]);
            url.hash = '';  // drop any leftover in-page anchor (e.g. #bf-ref-errors)
            window.history.replaceState(null, '', url);
          }});
          // 2) In-page "Jump to" links -> smooth scroll. Native #hash anchor
          //    navigation is unreliable inside the Spaces iframe / Gradio SPA,
          //    so scroll the target element into view ourselves.
          document.addEventListener('click', (e) => {{
            const link = e.target.closest('a[href^="#"]');
            if (!link) return;
            const id = decodeURIComponent((link.getAttribute('href') || '').slice(1));
            const target = id && document.getElementById(id);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({{behavior: 'smooth', block: 'start'}});
          }});
          // 3) Inline 🔗 title icons (span#copy-tab-<slug>) -> copy this tab's
          //    deep link, then fire the "copied" toast via the hidden trigger.
          document.addEventListener('click', (e) => {{
            const el = e.target.closest('.tab-link-icon');
            if (!el) return;
            e.preventDefault();
            const slug = el.id.replace('copy-tab-', '');
            navigator.clipboard.writeText(
              window.location.origin + window.location.pathname + '?tab=' + slug);
            const trigger = document.getElementById('copy-toast-trigger');
            if (trigger) trigger.click();
          }});
        }}
        """,
    )

    gr.Markdown(f"Last updated on **{LAST_UPDATED}**", elem_classes="markdown-text")

    with gr.Row():
        with gr.Accordion("📙 Citation", open=False):
            gr.Textbox(
                value=CITATION_TEXT, lines=7,
                label="Copy the BibTeX snippet to cite this source",
                elem_id="citation-button",
                show_label=True,
            )
        with gr.Accordion("📋 Changelog", open=False):
            gr.Markdown(CHANGELOG_TEXT)

if __name__ == "__main__":
    demo.launch()