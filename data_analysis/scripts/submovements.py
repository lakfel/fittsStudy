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
        dt_ms: int = 10, 
        gap_ms: int = 60
        ) -> pd.DataFrame:
    """
    df: DataFrame with columns ['t','x','y'] in ms, px
    Returns DF with uniform timeline (t0..tN step dt), interpolated x,y.
    """
    if df.empty:
        return df.copy()

    df = df[['t','x','y']].sort_values('t').reset_index(drop=True)

    # Detect gaps in the original time series
    dt = df['t'].diff().fillna(0.0)
    is_gap = dt > gap_ms

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
    out.loc[nan_mask, 'gap_fill'] = policy

    if len(boundary_idx) > 0:
        pad_steps = max(1, int(np.round(plateau_pad_ms / dt_ms)))
        # Fuerza plateau (repetición) en una pequeña ventana alrededor de cada boundary
        for bi in boundary_idx:
            l0 = max(0, bi - pad_steps)
            l1 = min(len(out)-1, bi + pad_steps)
            # fijar a la posición en el límite para crear meseta de v≈0
            out.loc[l0:l1, 'x'] = out.loc[bi, 'x']
            out.loc[l0:l1, 'y'] = out.loc[bi, 'y']
            out.loc[l0:l1, 'gap_fill'] = 'zero_plateau'
    out[['x','y']] = out[['x','y']].ffill().bfill()
    return out

def compute_kinematics(df: pd.DataFrame, dt_ms: int, smooth_window: int=5) -> pd.DataFrame:
    """
    grid = np.arange(t0, tN + dt_ms, dt_ms)
    out = pd.DataFrame({'t': grid})
    out = out.merge(df[['t','x','y']], how='left', on='t').sort_values('t')
    out[['x','y']] = out[['x','y']].interpolate(method='linear', limit_direction='both')
    out['imputed'] = out[['x','y']].isna().any(axis=1)
    out[['x','y']] = out[['x','y']].fillna(method='ffill').fillna(method='bfill')
    return out

def compute_kinematics(df: pd.DataFrame, dt_ms: int, smooth_window: int=5) -> pd.DataFrame:
    """
    Adds speed (px/ms) and acceleration (px/ms^2) columns.
    Uses simple finite differences on uniform samples.
    """
    out = df.copy()
    # Finite differences
    dx = out['x'].diff().fillna(0.0)
    dy = out['y'].diff().fillna(0.0)
    dt = dt_ms  # constant
    speed = np.sqrt(dx*dx + dy*dy) / dt  # px/ms
    if smooth_window and smooth_window > 1:
        speed = speed.rolling(window=smooth_window, min_periods=1, center=True).mean()
    out['speed'] = speed

    accel = out['speed'].diff().fillna(0.0) / dt  # (px/ms) per ms == px/ms^2
    if smooth_window and smooth_window > 1:
        accel = accel.rolling(window=smooth_window, min_periods=1, center=True).mean()
    out['accel'] = accel
    return out

def _label_runs(bool_series: pd.Series) -> List[Tuple[int,int]]:
    """
    Returns list of (start_idx, end_idx) inclusive of contiguous True runs.
    """
    runs = []
    in_run = False
    start = 0
    for i, val in enumerate(bool_series.to_numpy(dtype=bool)):
        if val and not in_run:
            in_run = True
            start = i
        elif not val and in_run:
            runs.append((start, i-1))
            in_run = False
    if in_run:
        runs.append((start, len(bool_series)-1))
    return runs

def detect_submovements(dfk: pd.DataFrame, thr: Thresholds, dt_ms: int) -> List[Dict]:
    """
    Heuristic segmentation:
    - Identify candidate 'slow' and 'rapid' runs by speed thresholds & min duration
    - Cut/end a submovement if speed ~ 0 OR an injected zero (gap) OR accel sign flips twice
    - Then apply merge heuristic on adjacent segments
    Returns list of dicts with start_idx, end_idx, t_start, t_end, type, v_peak, etc.
    """
    n = len(dfk)
    if n == 0:
        return []

    # Inject zero-speed markers where large gaps were present in the original (if available)
    # We assume dfk has uniform resampling. To emulate 'gaps', check consecutive original times if provided.
    zero_like = dfk['speed'] <= thr.epsilon_speed
    # Build acceleration sign sequence
    accel_sign = np.sign(dfk['accel'].to_numpy())
    accel_sign[accel_sign == 0] = np.nan  # treat zeros as missing for sign-flip counting

    # Speed-based candidate masks
    slow_mask = dfk['speed'] >= thr.slow_speed_min
    fast_mask = dfk['speed'] >= thr.fast_speed_min

    # Enforce min durations by run-length filtering
    min_len_slow = int(np.ceil(thr.slow_min_duration_ms / dt_ms))
    min_len_fast = int(np.ceil(thr.fast_min_duration_ms / dt_ms))

    def keep_min_len(mask, min_len):
        mask = mask.copy().to_numpy(dtype=bool)
        runs = _label_runs(pd.Series(mask))
        for s,e in runs:
            if (e - s + 1) < min_len:
                mask[s:e+1] = False
        return pd.Series(mask, index=dfk.index)

    slow_mask = keep_min_len(slow_mask, min_len_slow)
    fast_mask = keep_min_len(fast_mask, min_len_fast)

    # Initial segmentation by any-threshold pass (label preference: fast > slow > none)
    seg_type = np.array(["none"]*n, dtype=object)
    seg_type[slow_mask.to_numpy()] = "slow"
    seg_type[fast_mask.to_numpy()] = "rapid"  # overrides slow where both hold

    # Now form segments ensuring end conditions (speed ~0 or accel sign changes twice)
    segments = []
    i = 0
    while i < n:
        if seg_type[i] == "none":
            i += 1
            continue
        ttype = seg_type[i]
        start = i
        acc_flips = 0
        last_sign = np.sign(dfk['accel'].iloc[i]) or np.nan

        i += 1
        while i < n and seg_type[i] == ttype:
            # end conditions
            if dfk['speed'].iloc[i] <= thr.epsilon_speed:
                break
            # acceleration sign flip logic
            cur = np.sign(dfk['accel'].iloc[i]) or np.nan
            if not np.isnan(last_sign) and not np.isnan(cur) and np.sign(cur) != np.sign(last_sign):
                acc_flips += 1
                if acc_flips >= thr.accel_sign_flip_end:
                    break
            if not np.isnan(cur):
                last_sign = cur
            i += 1
        end = i
        if end - start >= 1:
            v_peak = float(dfk['speed'].iloc[start:end].max())
            t_start = float(dfk['t'].iloc[start])
            t_end = float(dfk['t'].iloc[end-1])
            segments.append({
                "start_idx": int(start),
                "end_idx": int(end-1),
                "t_start": t_start,
                "t_end": t_end,
                "duration_ms": t_end - t_start,
                "type": ttype,
                "v_peak_px_per_ms": v_peak,
            })
        i += 1

    # Merge heuristic on adjacent segments:
    # if velocity at midpoint >= ratio * linear extrapolation of the two peak velocities.
    # We'll approximate 'linear extrapolation between peaks' as linear interp at mid-time between the two
    # peak times using (t_peak1,v_peak1) and (t_peak2,v_peak2).
    merged = []
    k = 0
    while k < len(segments):
        if k == len(segments) - 1:
            merged.append(segments[k]); break
        a = segments[k]; b = segments[k+1]
        # Check gap
        if (b['t_start'] - a['t_end']) <= thr.merge_max_gap_ms:
            # find peaks within each segment
            segA = dfk.iloc[a['start_idx']:a['end_idx']+1]
            segB = dfk.iloc[b['start_idx']:b['end_idx']+1]
            iA = segA['speed'].idxmax(); iB = segB['speed'].idxmax()
            tA, vA = dfk.loc[iA, 't'], dfk.loc[iA, 'speed']
            tB, vB = dfk.loc[iB, 't'], dfk.loc[iB, 'speed']
            # midpoint in time between peaks
            tmid = (tA + tB) / 2.0
            # linear extrapolation (actually interpolation) at tmid
            if tB != tA:
                v_lin_mid = vA + (vB - vA) * ((tmid - tA) / (tB - tA))
            else:
                v_lin_mid = max(vA, vB)
            # measured speed near tmid
            vmid = float(dfk.iloc[(dfk['t']-tmid).abs().argmin()]['speed'])
            if vmid >= thr.merge_midpoint_ratio * v_lin_mid:
                # merge: extend a to b
                a['end_idx'] = b['end_idx']
                a['t_end'] = b['t_end']
                a['duration_ms'] = a['t_end'] - a['t_start']
                a['v_peak_px_per_ms'] = float(dfk['speed'].iloc[a['start_idx']:a['end_idx']+1].max())
                a['type'] = a['type'] if a['type']==b['type'] else f"{a['type']}+{b['type']}"
                k += 2
                merged.append(a)
                continue
        merged.append(a); k += 1

    return merged

def analyze_trial_positions(df_trial: pd.DataFrame,
                            resample_cfg: ResampleCfg = ResampleCfg(),
                            thresholds: Thresholds = Thresholds()) -> Dict[str, pd.DataFrame]:
    """
    df_trial: columns ['t','x','y'] (ms, px)
    Returns dict with:
      - 'uniform': resampled positions with speed/accel
      - 'segments': DataFrame of detected submovements
    """
    uni = resample_uniform(df_trial[['t','x','y']].sort_values('t'), dt_ms=resample_cfg.dt_ms)
    kin = compute_kinematics(uni, dt_ms=resample_cfg.dt_ms, smooth_window=resample_cfg.smooth_window)
    segs = detect_submovements(kin, thresholds, dt_ms=resample_cfg.dt_ms)
    segs_df = pd.DataFrame(segs)
    return {"uniform": kin, "segments": segs_df}