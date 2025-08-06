import pandas as pd
from pathlib import Path
import utils_paths as up
import numpy as np

PROC = Path(up.PROCESSED_DATA)
RAW = Path(up.RAW_DATA)

PROC.mkdir(parents=True, exist_ok=True)

TRIALS = Path(up.TRIALS_FILE)
POSITIONS = Path(up.POSITIONS_FILE)

trials_path = sorted(RAW.glob("trials_*.parquet"))[-1]
df_trials = pd.read_parquet(trials_path)

# explode cursorPositionsInterval -> positions table
pos_rows = []
for _, r in df_trials.iterrows():
    for src_field in ["cursorPositions"]:
        arr = r.get(src_field)
        if isinstance(arr, (list, np.ndarray)):
            print(f"Processing {src_field} - {type(arr)} for trial {r['__doc_id']}")
            for p in arr:
                pos_rows.append({
                    "trialDocId": r["__doc_id"],
                    "participantId": r.get("participantId"),
                    "t": p.get("time"),
                    "x": p.get("x"),
                    "y": p.get("y"),
                    "source": src_field
                })

df_positions = pd.DataFrame(pos_rows)

# guardar tabulados
df_trials.to_parquet(TRIALS, index=False)
if not df_positions.empty:
    df_positions.to_parquet(POSITIONS, index=False)
