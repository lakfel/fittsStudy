
import utils_paths as up
from pathlib import Path
import pandas as pd
from submovements import analyze_trial_positions
import matplotlib.pyplot as plt
import  math

def main():
    

    outdir = Path(up.PROCESSED_DATA); outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(up.POSITIONS_FILE)
    #print(df.columns)

    # Expect at least trialDocId,t,x,y
    required = {"trialDocId","t","x","y"}
    if not required.issubset(df.columns):
        raise ValueError(f"Positions parquet must include columns: {required}")

    seg_rows = []
    kinematic_rows = []

    for trial_id, grp in df.groupby("trialDocId"):
    #for trial_id, grp in [next(iter(df.groupby("trialDocId")))]:
    #for trial_id, grp in list(df.groupby("trialDocId"))[56:65]:

        grp_sorted = grp[['t','x','y']].sort_values('t')
        if grp_sorted['t'].iloc[0] > 0:
            first_t = grp_sorted.iloc[[0]].copy()
            first_t['t'] = 0
            grp_sorted = pd.concat([first_t, grp_sorted], ignore_index=True)

        #plot_trial_positions(grp_sorted)
        #plot_trial_velocities(calculate_velocity(grp_sorted))
        tempo = analyze_trial_positions(grp_sorted)
        #print(f"Trial {trial_id} analyzed: {tempo.keys()}")
        #plot_trial_velocities(tempo['uniform'], tempo['segments'])
        #print(f'Segments: {len(tempo["segments"]) if tempo["segments"] is not None else 0} -- {tempo["segments"]}')
        segs = tempo['segments'].copy()
        kinems = tempo['uniform'].copy()

        if segs is None or segs.empty:
            continue
        #print(segs)
        segs.insert(0, "trialDocId", trial_id)
        kinems.insert(0, "trialDocId", trial_id)
        seg_rows.append(segs)
        kinematic_rows.append(kinems)
    #return
    if seg_rows:
        seg_all = pd.concat(seg_rows, ignore_index=True)
        seg_all.to_parquet(up.SEGMENTS_FILE, index=False)
        seg_all.to_csv(up.SEGMENTS_FILE_CSV, index=False)
        kins_all = pd.concat(kinematic_rows, ignore_index=True)
        kins_all.to_parquet(up.KINEMATICS_FILE, index = False)
        kins_all.to_csv(up.KINEMATICS_FILE_CSV, index=False)

        #print(f"Saved segments -> {seg_path} ({len(seg_all)} rows)")
    else:
        print("No segments detected.")

def plot_trial_positions(df_trial: pd.DataFrame):
    """
    df_trial: columns ['t','x','y'] (ms, px)
    """
    plt.figure(figsize=(8,4))
    plt.plot(df_trial['t'], df_trial['x'], label='x')
    plt.plot(df_trial['t'], df_trial['y'], label='y')
    plt.scatter(df_trial['t'], df_trial['x'], color='blue', s=30, marker='o', alpha=0.7)
    plt.scatter(df_trial['t'], df_trial['y'], color='orange', s=30, marker='o', alpha=0.7)
    for t, x, y in zip(df_trial['t'], df_trial['x'], df_trial['y']):
        plt.annotate(f"{t:.1f}", (t, x), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8, color='blue')
        plt.annotate(f"{t:.1f}", (t, y), textcoords="offset points", xytext=(0,-12), ha='center', fontsize=8, color='orange')

    plt.xlabel('t')
    plt.ylabel('x / y')
    plt.title("Trial positions: t vs x and y")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_trial_velocities(df_trial: pd.DataFrame, segments: pd.DataFrame=None):
    """
    df_trial: columns ['t','x','y'] (ms, px)
    """

    #print(f"Plotting velocities for trial with {len(df_trial)} points \n {df_trial} ")

    plt.figure(figsize=(8,4))
    plt.plot(df_trial['t'], df_trial['v'], label='velocity', color='green')

    #print(f"{df_trial.head()}")

    #print(f"{segments.head()}")

    if segments is not None:
        for _, seg in segments.iterrows():
            
            color = 'blue' if 'rapid' in seg['type'] else 'red'
            plt.axvline(x=seg['t_start'], color=color, linestyle='--', alpha=0.6)
            plt.axvline(x=seg['t_end'], color=color, linestyle='--', alpha=0.6)


    
    plt.xlabel('t')
    plt.ylabel('velocity (px/ms)')
    plt.title("Trial velocities: t vs velocity")
    plt.legend()
    plt.tight_layout()
    plt.show()

        

def calculate_velocity (df_trial: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate velocity from positions DataFrame.
    df_trial: DataFrame with columns ['t','x','y'] (ms, px)
    Returns DataFrame with additional 'vx', 'vy' columns for velocity.
    """
    df_trial = df_trial.copy()
    for i in range(1, len(df_trial)):
        df_trial.at[i, 'v'] = math.sqrt((df_trial.at[i, 'x'] - df_trial.at[i-1, 'x']) ** 2 + (df_trial.at[i, 'y'] - df_trial.at[i-1, 'y']) ** 2) / (df_trial.at[i, 't'] - df_trial.at[i-1, 't'])
    return df_trial

if __name__ == "__main__":
    main()