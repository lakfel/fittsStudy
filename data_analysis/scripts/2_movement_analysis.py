
import argparse
from pathlib import Path
import pandas as pd
from submovements import ResampleCfg, Thresholds, analyze_trial_positions

def main():
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", required=True, help="Parquet with columns trialDocId, t, x, y, source (ms/px)")
    ap.add_argument("--outdir", default=str(Path(__file__).parent.parent / "data" / "processed"))
    ap.add_argument("--dt_ms", type=int, default=10)
    ap.add_argument("--slow_speed", type=float, default=0.05)
    ap.add_argument("--slow_ms", type=int, default=60)
    ap.add_argument("--fast_speed", type=float, default=0.35)
    ap.add_argument("--fast_ms", type=int, default=20)
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.positions)
    # Expect at least trialDocId,t,x,y
    required = {"trialDocId","t","x","y"}
    if not required.issubset(df.columns):
        raise ValueError(f"Positions parquet must include columns: {required}")

    thresholds = Thresholds(
        slow_speed_min=args.slow_speed,
        slow_min_duration_ms=args.slow_ms,
        fast_speed_min=args.fast_speed,
        fast_min_duration_ms=args.fast_ms
    )
    res_cfg = ResampleCfg(dt_ms=args.dt_ms)

    seg_rows = []
    for trial_id, grp in df.groupby("trialDocId"):
        out = analyze_trial_positions(grp[['t','x','y']].sort_values('t'),
                                      resample_cfg=res_cfg, thresholds=thresholds)
        segs = out['segments'].copy()
        if segs is None or segs.empty:
            continue
        segs.insert(0, "trialDocId", trial_id)
        seg_rows.append(segs)

    if seg_rows:
        seg_all = pd.concat(seg_rows, ignore_index=True)
        seg_path = outdir / "submovements.parquet"
        seg_all.to_parquet(seg_path, index=False)
        print(f"Saved segments -> {seg_path} ({len(seg_all)} rows)")
    else:
        print("No segments detected.")

if __name__ == "__main__":
    main()