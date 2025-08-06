"""
Submovement detection for goal-oriented cursor motions (Woodworth-style).
Reads per-trial cursor positions (t, x, y) and computes velocities, accelerations,
segments submovements by threshold rules, and applies an optional merge heuristic.

All thresholds are PARAMETRIC so you can adjust units and values easily.
By default we assume time in milliseconds, positions in pixels.

Author: J. Felipe González
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd

@dataclass
class Thresholds:
    # Units assumed: px/ms for speed thresholds unless you pass per-second and set convert=True
    slow_speed_min: float = 0.05      # px/ms  (== 50 px/s)
    slow_min_duration_ms: int = 60    # ms

    fast_speed_min: float = 0.35      # px/ms (== 350 px/s)  # NOTE: If you meant 0.35 px/s, set convert=True
    fast_min_duration_ms: int = 20    # ms

    epsilon_speed: float = 1e-6       # px/ms considered as zero
    gap_zero_inject_ms: int = 25      # if sampling gap > this, inject virtual zero-velocity boundary

    accel_sign_flip_end: int = 2      # end submovement if accel sign changes this many times

    # Merge heuristic
    merge_midpoint_ratio: float = 0.90  # 90% of extrapolated peaks
    merge_max_gap_ms: int = 40          # only consider merges if gap between segments <= this

@dataclass
class ResampleCfg:
    dt_ms: int = 10          # uniform resampling step (ms)
    interp: str = "linear"   # 'linear' interpolation for x,y
    smooth_window: int = 5   # moving average window over velocity (samples); set 1 to disable
    smooth_poly: Optional[int] = None   # reserved if you add savgol

def resample_uniform(
        df: pd.DataFrame, 
        dt_ms: int = 2, 
        gap_ms: int = 15
        ) -> pd.DataFrame:
    """
    df: DataFrame with columns ['t','x','y'] in ms, px
    Returns DF with uniform timeline (t0..tN step dt), interpolated x,y.
    """
    if df.empty:
        return df.copy()

    df = df[['t','x','y']].sort_values('t').reset_index(drop=True)
    if df['t'].iloc[0] > 0:
        first_row = df.iloc[[0]].copy()
        first_row['t'] = 0
        df = pd.concat([first_row, df], ignore_index=True)


    # Detect gaps in the original time series
    dt = df['t'].diff().fillna(0.0)
    is_gap = dt > gap_ms

    print(f"Detecting gaps in {df} \n dt - {dt} \n is_gap - {is_gap}")

    # Segment the time series by gaps
    seg_id = is_gap.cumsum()
    df_segs = df.copy()
    df_segs['segment_id'] = seg_id

    # Build uniform resampling 
    t0, tN = df['t'].iloc[0], df['t'].iloc[-1]
    grid = np.arange(t0, tN + dt_ms, dt_ms)
    out = pd.DataFrame({'t': grid})
    out['x'] = np.nan
    out['y'] = np.nan
    out['imputed'] = False  # will mark where we interpolate
    out['gap_fill'] = 'none'  # will mark where we fill gaps
    out['segment_id'] = np.nan  # will fill segment id later
    out['gap_boundary'] = False  # will mark where we have gap boundaries

    # For each segment, interpolate x,y only inside the segment
    for s in df_segs['segment_id'].unique():
        seg_df= df_segs[df_segs['segment_id'] == s]
        t_start, t_end = seg_df['t'].iloc[0], seg_df['t'].iloc[-1]
        mask = (out['t'] >= t_start) & (out['t'] <= t_end)
        tmp = out.loc[mask, ['t']].merge(seg_df[['t','x','y']], on='t', how='left').set_index('t')
        tmp[['x','y']] = tmp[['x','y']].interpolate(method='linear', limit_direction='both')
        imputed = tmp[['x','y']].isna().any(axis=1)
        tmp[['x','y']] = tmp[['x','y']].ffill().bfill()

        out.loc[mask, 'x'] = tmp['x'].to_numpy()
        out.loc[mask, 'y'] = tmp['y'].to_numpy
        out.loc[mask, 'imputed'] = imputed.to_numpy()
        out.loc[mask, 'segment_id'] = s

    seg_change = out['segment_id'].diff().fillna(0) != 0
    boundary_idx = np.where(seg_change & (~out['segment_id'].isna()))[0]

    if len(boundary_idx) > 0:
        boundary_idx = boundary_idx[1:] if len(boundary_idx) > 1 else []
    for bi in boundary_idx:
        out.loc[bi, 'gap_boundary'] = True

    nan_mask = out['x'].isna()
    xf = out['x'].copy(); yf = out['y'].copy()
    xf = xf.ffill(); yf = yf.ffill()
    xb = out['x'].copy(); yb = out['y'].copy()
    xb = xb.bfill(); yb = yb.bfill()
    
    filled_x = xf.where(~nan_mask, xb)
    filled_y = yf.where(~nan_mask, yb)

    out.loc[nan_mask, 'x'] = filled_x[nan_mask]
    out.loc[nan_mask, 'y'] = filled_y[nan_mask]
    #out.loc[nan_mask, 'gap_fill'] = policy

    if len(boundary_idx) > 0:
        pad_steps = max(1, int(np.round(plateau_pad_ms / dt_ms)))
        # Fuerza plateau (repetición) en una pequeña ventana alrededor de cada boundary
        for bi in boundary_idx:
            l0 = max(0, bi - pad_steps)
            l1 = min(len(out)-1, bi + pad_steps)
            # fijar a la posición en el límite para crear meseta de v≈0
            out.loc[l0:l1, 'x'] = out.loc[bi, 'x']
            out.loc[l0:l1, 'y'] = out.loc[bi, 'y']
            #out.loc[l0:l1, 'gap_fill'] = 'zero_plateau'
    out[['x','y']] = out[['x','y']].ffill().bfill()
    return out

def analyze_trial_positions(df_trial: pd.DataFrame,
                            resample_cfg: ResampleCfg = ResampleCfg(),
                            thresholds: Thresholds = Thresholds()) -> Dict[str, pd.DataFrame]:
    """
    df_trial: columns ['t','x','y'] (ms, px)
    Returns dict with:
      - 'uniform': resampled positions with speed/accel
      - 'segments': DataFrame of detected submovements
    """
    uni = resample_uniform(df_trial[['t','x','y']].sort_values('t'))
    return {"uniform": uni}
    #kin = compute_kinematics(uni, dt_ms=resample_cfg.dt_ms, smooth_window=resample_cfg.smooth_window)
    #segs = detect_submovements(kin, thresholds, dt_ms=resample_cfg.dt_ms)
    #segs_df = pd.DataFrame(segs)
    #return {"uniform": kin, "segments": segs_df}