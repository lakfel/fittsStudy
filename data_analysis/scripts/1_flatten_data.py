import pandas as pd
from pathlib import Path

RAW = Path(__file__).parent.parent / "data" / "raw"
PROC = Path(__file__).parent.parent / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


trials_path = sorted(RAW.glob("trials_*.parquet"))[-1]
df_trials = pd.read_parquet(trials_path)

# explode cursorPositionsInterval -> positions table
pos_rows = []
for _, r in df_trials.iterrows():
    for src_field in ["cursorPositions"]:
        arr = r.get(src_field)
        if isinstance(arr, list):
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
df_trials.to_parquet(PROC / "trials_latest.parquet", index=False)
if not df_positions.empty:
    df_positions.to_parquet(PROC / "positions_latest.parquet", index=False)
