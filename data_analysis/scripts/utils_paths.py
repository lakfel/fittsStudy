
from pathlib import Path

RAW_DATA = str(Path(__file__).parent.parent / "data" / "raw")
PROCESSED_DATA = str(Path(__file__).parent.parent / "data" / "processed")   

TEST_FOLDER = str(Path(__file__).parent.parent / "test")  
TEST_QA_FILE = str(Path(TEST_FOLDER) / "test_qa.json")

TRIALS_FILE = str(Path(PROCESSED_DATA) / "trials_latest.parquet")
POSITIONS_FILE = str(Path(PROCESSED_DATA) / "positions_latest.parquet")

SEGMENTS_FILE = str(Path(PROCESSED_DATA) / "submovements.parquet")
KINEMATICS_FILE = str(Path(PROCESSED_DATA) / "kinematics.parquet")

