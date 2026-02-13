
from pathlib import Path

RAW_DATA = str(Path(__file__).parent.parent / "data" / "raw")
PROCESSED_DATA = str(Path(__file__).parent.parent / "data" / "processed")   
PROCESSED_CSV_DATA = str(Path(__file__).parent.parent / "data" / "processed" / "csv")   

TEST_FOLDER = str(Path(__file__).parent.parent / "test")  
TEST_QA_FILE = str(Path(TEST_FOLDER) / "test_qa.json")

TRIALS_FILE = str(Path(PROCESSED_DATA) / "trials_latest.parquet")
TRIALS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "trials_latest.csv")
PRE_TRIALS_FILE = str(Path(PROCESSED_DATA) / "pre_trials_latest.parquet")
PRE_TRIALS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "pre_trials_latest.csv")
POSITIONS_FILE = str(Path(PROCESSED_DATA) / "positions_latest.parquet")
POSITIONS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "positions_latest.csv")

SEGMENTS_FILE = str(Path(PROCESSED_DATA) / "submovements.parquet")
KINEMATICS_FILE = str(Path(PROCESSED_DATA) / "kinematics.parquet")

ANALYSIS_FILE_1 = str(Path(PROCESSED_DATA) / "analysis_results.csv")