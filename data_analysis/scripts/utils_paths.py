
from pathlib import Path
import pandas as pd

RAW_DATA = str(Path(__file__).parent.parent / "data" / "raw")
PROCESSED_DATA = str(Path(__file__).parent.parent / "data" / "processed")   
PROCESSED_CSV_DATA = str(Path(__file__).parent.parent / "data" / "processed" / "csv")   

TEST_FOLDER = str(Path(__file__).parent.parent / "test")  
TEST_QA_FILE = str(Path(TEST_FOLDER) / "test_qa.json")

TRIALS_FILE = str(Path(PROCESSED_DATA) / "trials_latest.parquet")
TRIALS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "trials_latest.csv")

PRE_TRIALS_FILE = str(Path(PROCESSED_DATA) / "pre_trials_latest.parquet")
PRE_TRIALS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "pre_trials_latest.csv")

ERROR_RATES_FILE = str(Path(PROCESSED_DATA) / "error_rates_latest.parquet")
ERROR_RATES_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "error_rates_latest.csv")

POSITIONS_FILE = str(Path(PROCESSED_DATA) / "positions_latest.parquet")
POSITIONS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "positions_latest.csv")

SEGMENTS_FILE = str(Path(PROCESSED_DATA) / "submovements.parquet")
SEGMENTS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "submovements.csv")
KINEMATICS_FILE = str(Path(PROCESSED_DATA) / "kinematics.parquet")
KINEMATICS_FILE_CSV = str(Path(PROCESSED_CSV_DATA) / "kinematics.csv")

ANALYSIS_FILE_1 = str(Path(PROCESSED_DATA) / "analysis_results.csv")

# Threshold for minimum acceptable success rate (participants below this are excluded)
MIN_SUCCESS_RATE_THRESHOLD = 0.70  # 70% success rate

def get_excluded_participants_by_error_rate(threshold=MIN_SUCCESS_RATE_THRESHOLD):
    """
    Read error rates file and return list of participant IDs that don't meet
    the minimum success rate threshold.
    
    Parameters:
    -----------
    threshold : float
        Minimum acceptable success rate (default: MIN_SUCCESS_RATE_THRESHOLD)
        
    Returns:
    --------
    list
        List of participant IDs to exclude
    """
    try:
        # Read error rates file
        df_errors = pd.read_csv(ERROR_RATES_FILE_CSV)
        
        # Calculate average success rate per participant across all conditions
        participant_avg_success = df_errors.groupby('participantId').agg({
            'success': 'sum',
            'total': 'sum'
        }).reset_index()
        
        # Calculate overall success rate
        participant_avg_success['avg_success_rate'] = (
            participant_avg_success['success'] / participant_avg_success['total']
        )
        
        # Filter participants below threshold
        excluded = participant_avg_success[
            participant_avg_success['avg_success_rate'] < threshold
        ]['participantId'].tolist()
        
        print(f"Excluded {len(excluded)} participants with success rate < {threshold:.0%}")
        for pid in excluded:
            rate = participant_avg_success[
                participant_avg_success['participantId'] == pid
            ]['avg_success_rate'].values[0]
            print(f"  - {pid}: {rate:.2%}")
        
        return excluded
        
    except Exception as e:
        print(f"Warning: Could not filter by error rate: {e}")
        print("Returning empty exclusion list")
        return []

# Legacy excluded participants list (manually identified)
EXLCUDED_PARTICIPANTS = [
            "5e31a1526ef37a1879a94441", # Incomplete data
            "6973653f34c609a7c3420e1c", # Incomplete data
            "615c4bfb2e8a77519a94d8f6", # Incomplete data
            ]