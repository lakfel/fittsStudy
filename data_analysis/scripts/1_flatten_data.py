import pandas as pd
from pathlib import Path
import utils_paths as up
import numpy as np

PROC = Path(up.PROCESSED_DATA)
RAW = Path(up.RAW_DATA)

PROC.mkdir(parents=True, exist_ok=True)

TRIALS = Path(up.TRIALS_FILE)
POSITIONS = Path(up.POSITIONS_FILE)


TRIALS = Path(up.TRIALS_FILE)
POSITIONS = Path(up.POSITIONS_FILE)
TRIALS_CSV = Path(up.TRIALS_FILE_CSV)
POSITIONS_CSV = Path(up.POSITIONS_FILE_CSV)

trials_path = sorted(RAW.glob("trials_*.parquet"))[-1]
df_trials = pd.read_parquet(trials_path)

pretrials_path = sorted(RAW.glob("pre_trials_*.parquet"))[-1]
df_pre_trials = pd.read_parquet(pretrials_path)

# explode cursorPositionsInterval -> positions table
pos_rows = []

success_rates = dict()

for _, r in df_trials.iterrows():
    if not r.get("participantId") in success_rates:
        success_rates[r.get("participantId")] = {"success": 0, "total": 0}
    if r.get("inTarget"):
        success_rates[r.get("participantId")]["success"] += 1
    success_rates[r.get("participantId")]["total"] += 1
    for src_field in ["cursorPositions"]:
        arr = r.get(src_field)
        if isinstance(arr, (list, np.ndarray)):
            print(f"Processing {src_field} - {type(arr)} for trial {r['__doc_id']}")
            for p in arr:
                pos_rows.append({
                    "trialDocId": r["__doc_id"], # Not sure I need this, but it can be useful to link back to trial info
                    "participantId": r.get("participantId"), # This should be linked to one of the registers in demotrphics in folder of prolific
                    "t": p.get("time"),
                    "x": p.get("x"),
                    "y": p.get("y"),
                    "ID": r.get("ID"), # in case positions have their own ID
                    "source": src_field
                })

for pid  in success_rates.keys():
    rates = success_rates[pid]
    total = rates["total"]
    success = rates["success"]
    rate = success / total if total > 0 else 0
    print(f"Participant {pid}: Success Rate = {rate:.2%} ({success}/{total})")  

df_positions = pd.DataFrame(pos_rows)

# guardar tabulados
df_trials.to_parquet(TRIALS, index=False)
df_trials.to_csv(TRIALS_CSV, index=False)

df_pre_trials.to_parquet(Path(up.PRE_TRIALS_FILE), index=False)
df_pre_trials.to_csv(Path(up.PRE_TRIALS_FILE_CSV), index=False)

if not df_positions.empty:
    df_positions.to_parquet(POSITIONS, index=False)
    df_positions.to_csv(POSITIONS_CSV, index=False)
