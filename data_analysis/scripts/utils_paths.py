
from pathlib import Path

RAW_DATA = str(Path(__file__).parent.parent / "data" / "raw")
PROCESSED_DATA = str(Path(__file__).parent.parent / "data" / "processed")   


TRIALS_FILE = str(Path(PROCESSED_DATA) / "trials_latest.parquet")
POSITIONS_FILE = str(Path(PROCESSED_DATA) / "positions_latest.parquet")


