"""Shared constants for Variant A IS simulation. Cut is 2024-10-02 inclusive."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
TRIALS = ROOT / "trials"
LEXICON = ROOT / "lexicon"

IS_END = "2024-10-02"
MARKET_START = "2010-01-01"
SPEECH_YEAR0 = 2011
SPEECH_YEAR1 = 2024
Z_MIN_OBS = 252
Z_CLOCK_START = "2011-01-03"
HALF_LIFE = 20
VOL_TARGET = 0.10
VOL_FLOOR = 0.04
GROSS_CAP = 1.50
W_TLT = 0.75
W_UUP = 0.25
VOL_W_SHORT = 20
VOL_W_LONG = 60
POS_CLIP = 2.0
MIN_HD = 5
NEGATION_WINDOW = 5
COST_BPS = {"TLT": 1.5, "UUP": 5.0}
NO_TRADE_BAND = 0.10
RF = 0.0
ANN = 252

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BOARD_INDEX = "https://www.federalreserve.gov/newsevents/speech/{year}-speeches.htm"
BOARD_BASE = "https://www.federalreserve.gov"
FOMC_CAL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
