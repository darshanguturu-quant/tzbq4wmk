"""
Configuration settings for the Decision-Time Wind Forecast Portal backend.
"""

from pathlib import Path

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_PATH = DATA_DIR / "snapshot.sqlite"
MANIFEST_PATH = DATA_DIR / "manifest.json"


class PresetConfig(BaseModel):
    id: str
    name: str
    cutoff_time: str
    description: str


CUTOFF_PRESETS = [
    PresetConfig(
        id="epex_hourly",
        name="EPEX GB Hourly Day-Ahead",
        cutoff_time="09:20",
        description="Gate closure for EPEX SPOT GB Day-Ahead Hourly auction.",
    ),
    PresetConfig(
        id="n2ex",
        name="N2EX (Nord Pool) Day-Ahead",
        cutoff_time="09:50",
        description="Gate closure for Nord Pool GB Day-Ahead auction.",
    ),
    PresetConfig(
        id="epex_half_hourly",
        name="EPEX GB Half-Hourly Day-Ahead",
        cutoff_time="15:30",
        description="Gate closure for EPEX SPOT GB Day-Ahead Half-Hourly auction.",
    ),
]

DEFAULT_CUTOFF = "09:20"
MIN_BAND_SAMPLES = (
    48  # Minimum past residual points required before generating empirical band
)

DECISION_START_DATE = "2026-01-01"
DECISION_END_DATE = "2026-01-31"

DISCLAIMERS = {
    "cutoff": "Illustrative GB auction gate closure. Confirm your organisation's actual internal trading deadline.",
    "uncertainty": "Empirical residual-based range from past forecast errors. Not an Elexon probabilistic forecast. Not a guaranteed interval.",
    "scope": "The data reflects national wind generation only. It does not include customer demand, thermal contracts, or proprietary portfolios.",
    "actuals_revision": "Latest settlement actuals at extraction time.",
}
