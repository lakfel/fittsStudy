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
ERROR_RATES_FILE_CSV = Path(up.ERROR_RATES_FILE_CSV)

TRIALS_CSV = Path(up.TRIALS_FILE_CSV)
POSITIONS_CSV = Path(up.POSITIONS_FILE_CSV)
ERROR_RATES_CSV = Path(up.ERROR_RATES_FILE_CSV)

trials_path = sorted(RAW.glob("trials_*.parquet"))[-1]
df_trials = pd.read_parquet(trials_path)

pretrials_path = sorted(RAW.glob("pre_trials_*.parquet"))[-1]
df_pre_trials = pd.read_parquet(pretrials_path)

# explode cursorPositionsInterval -> positions table
pos_rows = []

summarized_trials = []

success_rates = dict() 

for _, r in df_trials.iterrows():
    key = f"{r.get('participantId')}-{r.get('buffer')}-{r.get('indication')}-{r.get('feedbackMode')}-{r.get('W')}-{r.get('A')}"
    if not key in success_rates:
        success_rates[key] = {"success": 0, "total": 0, "Wrong_Indication": 0}
    if r.get("success"):
        success_rates[key]["success"] += 1
    success_rates[key]["total"] += 1
    success_rates[key]["Wrong_Indication"] += len(r.get("wrongIndications", []))

    indicationDown = r.get("indicationsDown", [])
    indicationUp = r.get("indicationsUp", [])
    reachingTimes = r.get("reachingTimes", [])
    outTimes = r.get("outTimes", [])
    bufferReachinTimes = r.get("bufferReachingTimes", [])
    bufferOutTimes = r.get("bufferOutTimes", [])

    summarized_trials.append({
        "trialDocId": r["__doc_id"],
        "participantId": r.get("participantId"),
        "buffer": r.get("buffer"),
        "indication": r.get("indication"),
        "feedbackMode": r.get("feedbackMode"),
        "W": r.get("W"),
        "A": r.get("A"),
        "Target_position_x": r.get("targetPosition", {}).get("x"),
        "Target_position_y": r.get("targetPosition", {}).get("y"),
        "Indication_down_x": indicationDown[-1].get("x") if len(indicationDown) > 0 else None,
        "Indication_down_y": indicationDown[-1].get("y") if len(indicationDown) > 0 else None,
        "Indication_down_t": indicationDown[-1].get("time") if len(indicationDown) > 0 else None,
        "Indication_down_in_target": indicationDown[-1].get("inTarget") if len(indicationDown) > 0 else None,
        "Indication_up_x": indicationUp[-1].get("x") if len(indicationUp) > 0 else None,
        "Indication_up_y": indicationUp[-1].get("y") if len(indicationUp) > 0 else None,
        "Indication_up_t": indicationUp[-1].get("time") if len(indicationUp) > 0 else None,
        "Indication_up_in_target": indicationUp[-1].get("inTarget") if len(indicationUp) > 0 else None,
        "Reaching_pos_x": reachingTimes[-1].get("x") if len(reachingTimes) > 0 else None,
        "Reaching_pos_y": reachingTimes[-1].get("y") if len(reachingTimes) > 0 else None,
        "Reaching_time": reachingTimes[-1].get("time") if len(reachingTimes) > 0 else None,
        "Buffer_reaching_time": bufferReachinTimes[-1].get("time") if len(bufferReachinTimes) > 0 else None,
        "Number_reaching_time": len(reachingTimes),
        "Number_out_time": len(outTimes),
        "Number_buffer_reaching_time": len(bufferReachinTimes),
        "Number_buffer_out_time": len(bufferOutTimes),
        "Start_position_x": r.get("cursorPositions", [{}])[0].get("x") if len(r.get("cursorPositions", [])) > 0 else None,
        "Start_position_y": r.get("cursorPositions", [{}])[0].get("y") if len(r.get("cursorPositions", [])) > 0 else None,
        "Distance_to_target_indication_down": np.sqrt((indicationDown[-1].get("x", 0) - r.get("targetPosition", {}).get("x", 0))**2 + (indicationDown[-1].get("y", 0) - r.get("targetPosition", {}).get("y", 0))**2) if len(indicationDown) > 0 else None,
        "Distance_to_target_indication_up": np.sqrt((indicationUp[-1].get("x", 0) - r.get("targetPosition", {}).get("x", 0))**2 + (indicationUp[-1].get("y", 0) - r.get("targetPosition", {}).get("y", 0))**2) if len(indicationUp) > 0 else None,
        "success": r.get("success", False),
        "wrongIndications": len(r.get("wrongIndications", [])),
        "Reaching_times": reachingTimes,
        "Out_times": outTimes,
        "Buffer_reaching_times": bufferReachinTimes,
        "Buffer_out_times": bufferOutTimes
    })

    for src_field in ["cursorPositions"]:
        arr = r.get(src_field)
        if isinstance(arr, (list, np.ndarray)):
            #print(f"Processing {src_field} - {type(arr)} for trial {r['__doc_id']}")
            for p in arr:
                pos_rows.append({
                    "trialDocId": r["__doc_id"], # Not sure I need this, but it can be useful to link back to trial info
                    "participantId": r.get("participantId"), # This should be linked to one of the registers in demotrphics in folder of prolific
                    "t": p.get("time"),
                    "x": p.get("x"),
                    "y": p.get("y"),
                    "Target_position_x": r.get("targetPosition", {}).get("x"),
                    "Target_position_y": r.get("targetPosition", {}).get("y"),
                    "Distance_to_target": np.sqrt((p.get("x") - r.get("targetPosition", {}).get("x", 0))**2 + (p.get("y") - r.get("targetPosition", {}).get("y", 0))**2),   
                    "Distance_to_target_indication_down": np.sqrt((indicationDown[-1].get("x", 0) - r.get("targetPosition", {}).get("x", 0))**2 + (indicationDown[-1].get("y", 0) - r.get("targetPosition", {}).get("y", 0))**2) if len(indicationDown) > 0 else None,
                    "Distance_to_target_indication_up": np.sqrt((indicationUp[-1].get("x", 0) - r.get("targetPosition", {}).get("x", 0))**2 + (indicationUp[-1].get("y", 0) - r.get("targetPosition", {}).get("y", 0))**2) if len(indicationUp) > 0 else None,
                    "Indication_down_x": indicationDown[-1].get("x") if len(indicationDown) > 0 else None,
                    "Indication_down_y": indicationDown[-1].get("y") if len(indicationDown) > 0 else None,
                    "Indication_up_x": indicationUp[-1].get("x") if len(indicationUp) > 0 else None,
                    "Indication_up_y": indicationUp[-1].get("y") if len(indicationUp) > 0 else None,
                    "W": r.get("W"),
                    "A": r.get("A"),
                    "ID": r.get("ID"), # in case positions have their own ID
                    "indication": r.get('indication'),
                    "feedbackMode": r.get('feedbackMode'),
                    "buffer": r.get('buffer'),
                    "source": src_field
                })

sucess_rates_summary = []
for pid  in success_rates.keys():
    rates = success_rates[pid]
    total = rates["total"]
    success = rates["success"]
    wrongIndications = rates["Wrong_Indication"]
    rate = success / total if total > 0 else 0
    pid_split = pid.split("-")
    sucess_rates_summary.append({
        "participantId": pid_split[0],
        "buffer": pid_split[1],
        "indication": pid_split[2],
        "feedback": pid_split[3],
        "W": pid_split[4],
        "A": pid_split[5],
        "success": success,
        "total": total,
        "success_rate": rate,
        "Wrong_Indication": wrongIndications
    })
    #print(f"Participant {pid}: Success Rate = {rate:.2%} ({success}/{total})")  

df_error_rates = pd.DataFrame(sucess_rates_summary)
df_error_rates.to_csv(up.ERROR_RATES_FILE_CSV, index=False)


df_positions = pd.DataFrame(pos_rows)

# guardar tabulados
df_trials = pd.DataFrame(summarized_trials)
df_trials.to_parquet(TRIALS, index=False)
df_trials.to_csv(TRIALS_CSV, index=False)

df_pre_trials.to_parquet(Path(up.PRE_TRIALS_FILE), index=False)
df_pre_trials.to_csv(Path(up.PRE_TRIALS_FILE_CSV), index=False)

if not df_positions.empty:
    df_positions.to_parquet(POSITIONS, index=False)
    #df_positions.to_csv(POSITIONS_CSV, index=False)
