"""
Fitts Law Analysis
==================
This script calculates Fitts law metrics for each trial:
- Effective Index of Difficulty (IDe)
- Effective Width (We) and Amplitude (Ae)
- Movement Time (MT) for different moments
- Throughput (TP)

Analysis is performed for three different time points:
1. Reaching time (first time cursor reaches target area)
2. Indication down time (when user presses button/bar)
3. Indication up time (when user releases button/bar)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from scipy.stats import f_oneway
import matplotlib.pyplot as plt
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import utils_paths as up


def calculate_endpoint_projected_position(row):
    """
    Calculate projected endpoint position (dx) for a trial along the movement vector.
    This dx represents the deviation from the intended target center.
    
    Returns dx for each time point (reaching, indication_down, indication_up).
    Positive dx means overshooting, negative means undershooting.
    """
    results = {}
    
    # Movement vector from previous target to current target
    movement_vector = np.array([
        row['Target_position_x'] - row['Previous_target_position_x'], 
        row['Target_position_y'] - row['Previous_target_position_y']
    ])
    movement_norm = np.linalg.norm(movement_vector)
    
    if movement_norm == 0:
        return pd.Series({
            'dx_indication_down': np.nan,
            'dx_indication_up': np.nan,
            'dx_reaching': np.nan
        })

    # For indication down
    if pd.notna(row['Indication_down_x']) and pd.notna(row['Indication_down_y']):
        # Vector from previous target to endpoint
        endpoint_vector = np.array([
            row['Indication_down_x'] - row['Target_position_x'], 
            row['Indication_down_y'] - row['Target_position_y']
        ])
        # Project onto movement vector and subtract nominal amplitude A
        dx_down = np.dot(movement_vector, endpoint_vector) / movement_norm
        results['dx_indication_down'] = dx_down
    else:
        results['dx_indication_down'] = np.nan

    # For indication up
    if pd.notna(row['Indication_up_x']) and pd.notna(row['Indication_up_y']):
        endpoint_vector = np.array([
            row['Indication_up_x'] - row['Target_position_x'], 
            row['Indication_up_y'] - row['Target_position_y']
        ])
        dx_up = np.dot(movement_vector, endpoint_vector) / movement_norm 
        results['dx_indication_up'] = dx_up
    else:
        results['dx_indication_up'] = np.nan

    # For reaching time endpoint
    if pd.notna(row['Reaching_pos_x']) and pd.notna(row['Reaching_pos_y']):
        endpoint_vector = np.array([
            row['Reaching_pos_x'] - row['Target_position_x'], 
            row['Reaching_pos_y'] - row['Target_position_y']
        ])
        dx_reaching = np.dot(movement_vector, endpoint_vector) / movement_norm 
        results['dx_reaching'] = dx_reaching
    else:
        results['dx_reaching'] = np.nan

    return pd.Series(results)


def filter_outliers_by_indication_up_time(df, n_std=3, verbose=True):
    """
    Filter out trials with indication_up time exceeding mean + n standard deviations.
    
    Parameters:
    -----------
    df : DataFrame
        Trials data
    n_std : float
        Number of standard deviations above mean to use as threshold (default: 3)
    verbose : bool
        If True, print filtering statistics
        
    Returns:
    --------
    DataFrame
        Filtered dataframe without outlier trials
    """
    # Calculate statistics for indication_up_t
    mean_time = df['Indication_up_t'].mean()
    std_time = df['Indication_up_t'].std()
    threshold = mean_time + n_std * std_time
    
    # Count trials before filtering
    n_before = len(df)
    
    # Filter outliers
    df_filtered = df[df['Indication_up_t'] <= threshold].copy()
    
    # Count trials after filtering
    n_after = len(df_filtered)
    n_removed = n_before - n_after
    pct_removed = (n_removed / n_before * 100) if n_before > 0 else 0
    
    if verbose:
        print("\n" + "="*80)
        print("OUTLIER FILTERING (Indication Up Time)")
        print("="*80)
        print(f"Mean indication_up time: {mean_time:.2f} ms")
        print(f"Std deviation: {std_time:.2f} ms")
        print(f"Threshold (mean + {n_std}*std): {threshold:.2f} ms")
        print(f"Trials before filtering: {n_before}")
        print(f"Trials removed: {n_removed} ({pct_removed:.2f}%)")
        print(f"Trials after filtering: {n_after}")
        
        if n_removed > 0:
            removed_trials = df[df['Indication_up_t'] > threshold]
            print(f"\nOutlier time range: {removed_trials['Indication_up_t'].min():.2f} - {removed_trials['Indication_up_t'].max():.2f} ms")
    
    return df_filtered


def calculate_fitts_law_metrics(save_results=True, verbose=True):
    """
    Calculate Fitts law metrics aggregated by condition.
    
    According to ISO 9241-9, metrics are calculated per condition (not per trial):
    - We = 4.133 * SD(dx) where dx are endpoint deviations
    - Ae = A + mean(dx) where A is nominal amplitude
    - MT = mean(MT) across all trials in condition
    - IDe = log2(1 + Ae/We)
    - TP = IDe / MT
    
    Parameters:
    -----------
    save_results : bool
        If True, save results to CSV files
    verbose : bool
        If True, print detailed analysis summary
        
    Returns:
    --------
    DataFrame
        Condition-level summary with Fitts law metrics
    """
    
    # Load trials data
    df_trials = pd.read_csv(up.TRIALS_FILE_CSV)
    
    if verbose:
        print("="*80)
        print("PARTICIPANT FILTERING")
        print("="*80)
    
    # Filter successful trials only for Fitts law analysis
    df_success = df_trials[df_trials['success'] == True].copy()
    
    if verbose:
        print(f"\nTotal trials: {len(df_trials)}")
        print(f"Successful trials: {len(df_success)}")
        print(f"Success rate: {len(df_success)/len(df_trials)*100:.2f}%")
    
    # Filter outliers based on indication_up time
    df_success = filter_outliers_by_indication_up_time(df_success, n_std=3, verbose=verbose)

    # Convert time columns from milliseconds to seconds
    df_success['MT_reaching'] = df_success['Reaching_time'] / 1000.0
    df_success['MT_indication_down'] = df_success['Indication_down_t'] / 1000.0
    df_success['MT_indication_up'] = df_success['Indication_up_t'] / 1000.0

    # Calculate dx (projected endpoint deviations) for each trial
    if verbose:
        print("\n" + "="*80)
        print("CALCULATING ENDPOINT DEVIATIONS (dx)")
        print("="*80)
    
    df_success[['dx_indication_down', 'dx_indication_up', 'dx_reaching']] = df_success.apply(
        calculate_endpoint_projected_position, axis=1
    )

    print("\nSample of calculated dx values:")
    print(df_success[['dx_indication_down', 'dx_indication_up', 'dx_reaching']].head())

    # Group by experimental conditions
    grouping_vars = [ 'W', 'A', 'buffer', 'indication', 'feedbackMode']
    
    if verbose:
        print("\n" + "="*80)
        print("AGGREGATING METRICS BY CONDITION")
        print("="*80)

    # ====================
    # AGGREGATE BY CONDITION (ISO 9241-9)
    # ====================
    
    condition_metrics = []
    
    for time_type, time_col in [('reaching', 'MT_reaching'), 
                                 ('indication_down', 'MT_indication_down'), 
                                 ('indication_up', 'MT_indication_up')]:
        
        dx_col = f'dx_{time_type}'
        
        # Group and calculate aggregated metrics
        # Use apply with a function that has access to the whole group
        def aggregate_condition(group):
            # Extract A value (same for all trials in group)
            A_val = group['A'].iloc[0]
            
            return pd.Series({
                # Count trials
                'n_trials': len(group),
                
                # Movement Time (mean across trials)
                'MT_mean': group[time_col].mean(),
                'MT_std': group[time_col].std(),
                
                # Endpoint deviations
                'dx_mean': group[dx_col].mean(),
                'dx_std': group[dx_col].std(),
                
                # Effective Width: We = 4.133 * SD(dx)
                'We': 4.133 * group[dx_col].std(),
                
                # Effective Amplitude: Ae = A + mean(dx)
                'Ae': A_val + group[dx_col].mean(),
            })
        
        grouped = df_success.groupby(grouping_vars, group_keys=False).apply(aggregate_condition).reset_index()
        
        # Calculate IDe and Throughput
        grouped['IDe'] = np.log2(1 + grouped['Ae'] / grouped['We'])
        grouped['TP'] = grouped['IDe'] / grouped['MT_mean']
        
        # Add time type identifier
        grouped['time_type'] = time_type
        
        condition_metrics.append(grouped)
    
    # Combine all time types
    df_conditions = pd.concat(condition_metrics, ignore_index=True)
    
    # Save results
    if save_results:
        output_file = Path(up.PROCESSED_DATA) / "csv" / "fitts_conditions_summary.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df_conditions.to_csv(output_file, index=False)
        if verbose:
            print(f"\nCondition-level metrics saved to: {output_file}")
    
    # ====================
    # PRINT SUMMARY
    # ====================
    
    if verbose:
        print("\n" + "="*80)
        print("FITTS LAW ANALYSIS SUMMARY (AGGREGATED BY CONDITION)")
        print("="*80)
        
        for time_type in ['reaching', 'indication_down', 'indication_up']:
            subset = df_conditions[df_conditions['time_type'] == time_type]
            
            print(f"\n{time_type.upper().replace('_', ' ')} Analysis:")
            print(f"   Number of conditions: {len(subset)}")
            print(f"   Mean MT: {subset['MT_mean'].mean():.3f} s (SD: {subset['MT_mean'].std():.3f})")
            print(f"   Mean TP: {subset['TP'].mean():.2f} bits/s (SD: {subset['TP'].std():.2f})")
            print(f"   Mean IDe: {subset['IDe'].mean():.2f} (SD: {subset['IDe'].std():.2f})")
            print(f"   Mean We: {subset['We'].mean():.2f} px (SD: {subset['We'].std():.2f})")
            print(f"   Mean Ae: {subset['Ae'].mean():.2f} px (SD: {subset['Ae'].std():.2f})")
            print(f"   Mean dx: {subset['dx_mean'].mean():.2f} px (SD: {subset['dx_std'].mean():.2f})")
        
        print("\n" + "="*80)

    return df_conditions

    


def perform_statistical_analysis(df_success, save_results=True, verbose=True):
    """
    Perform ANOVA and post-hoc tests to identify significant differences between conditions.
    
    Parameters:
    -----------
    df_success : DataFrame
        DataFrame with Fitts law metrics
    save_results : bool
        If True, save statistical results to files
    verbose : bool
        If True, print detailed statistical results
        
    Returns:
    --------
    dict
        Dictionary with ANOVA and post-hoc results for each time type
    """
    
    results = {}
    
    if verbose:
        print("\n" + "="*80)
        print("STATISTICAL ANALYSIS (ANOVA & POST-HOC TESTS)")
        print("="*80)
    
    # Prepare data - create categorical variables
    df_analysis = df_success.copy()
    df_analysis['feedbackMode'] = df_analysis['feedbackMode'].astype('category')
    df_analysis['buffer_cat'] = df_analysis['buffer'].astype('category')
    df_analysis['indication'] = df_analysis['indication'].astype('category')
    df_analysis['ID_cat'] = df_analysis['ID_nominal'].astype('category')
    
    # Define time types to analyze
    time_types = [
        ('MT_reaching', 'Reaching Time'),
        ('MT_indication_down', 'Indication Down'),
        ('MT_indication_up', 'Indication Up')
    ]
    
    for mt_col, time_name in time_types:
        if verbose:
            print(f"\n{'='*80}")
            print(f"Analysis for: {time_name}")
            print(f"{'='*80}")
        
        results[mt_col] = {}
        
        # Remove NaN values
        df_clean = df_analysis[[mt_col, 'feedbackMode', 'buffer_cat', 'indication', 'ID_cat']].dropna()
        
        # ========== MULTI-FACTORIAL ANOVA ==========
        if verbose:
            print(f"\n--- Multi-Factorial ANOVA (with higher-order interactions) ---")
        
        try:
            # Fit OLS model with main effects and interactions up to 3-way
            # We include feedbackMode*buffer_cat*indication (all interactions among these 3)
            # Plus ID_cat and its 2-way interactions with each of the other factors
            formula = (f'{mt_col} ~ C(feedbackMode) + C(buffer_cat) + C(indication) + C(ID_cat) + '
                      f'C(feedbackMode):C(buffer_cat) + C(feedbackMode):C(indication) + C(buffer_cat):C(indication) + '
                      f'C(feedbackMode):C(ID_cat) + C(buffer_cat):C(ID_cat) + C(indication):C(ID_cat) + '
                      f'C(feedbackMode):C(buffer_cat):C(indication) + '
                      f'C(feedbackMode):C(buffer_cat):C(ID_cat) + C(feedbackMode):C(indication):C(ID_cat) + C(buffer_cat):C(indication):C(ID_cat)')
            model = ols(formula, data=df_clean).fit()
            anova_table = anova_lm(model, typ=2)
            
            results[mt_col]['anova'] = anova_table
            results[mt_col]['model'] = model
            
            if verbose:
                print(anova_table.to_string())
                print(f"\nModel R²: {model.rsquared:.4f}")
                print(f"Adjusted R²: {model.rsquared_adj:.4f}")
                
                # Identify significant interactions
                sig_interactions = []
                for idx in anova_table.index:
                    if ':' in str(idx) and anova_table.loc[idx, 'PR(>F)'] < 0.05:
                        sig_interactions.append(str(idx))
                
                if sig_interactions:
                    print(f"\nSignificant interactions (p < 0.05): {', '.join(sig_interactions)}")
            
        except Exception as e:
            if verbose:
                print(f"Error in ANOVA: {e}")
            results[mt_col]['anova'] = None
            results[mt_col]['model'] = None
        
        # ========== POST-HOC TESTS: MAIN EFFECTS ==========
        
        # 1. Feedback Mode
        if verbose:
            print(f"\n--- Post-hoc: Feedback Mode (Main Effect) ---")
        try:
            tukey_feedback = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['feedbackMode'],
                alpha=0.05
            )
            results[mt_col]['posthoc_feedback'] = tukey_feedback
            if verbose:
                print(tukey_feedback)
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (feedback): {e}")
            results[mt_col]['posthoc_feedback'] = None
        
        # 2. Buffer
        if verbose:
            print(f"\n--- Post-hoc: Buffer (Main Effect) ---")
        try:
            tukey_buffer = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['buffer_cat'],
                alpha=0.05
            )
            results[mt_col]['posthoc_buffer'] = tukey_buffer
            if verbose:
                print(tukey_buffer)
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (buffer): {e}")
            results[mt_col]['posthoc_buffer'] = None
        
        # 3. Indication Mode
        if verbose:
            print(f"\n--- Post-hoc: Indication Mode (Main Effect) ---")
        try:
            tukey_indication = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['indication'],
                alpha=0.05
            )
            results[mt_col]['posthoc_indication'] = tukey_indication
            if verbose:
                print(tukey_indication)
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (indication): {e}")
            results[mt_col]['posthoc_indication'] = None
        
        # 4. ID (Task Difficulty)
        if verbose:
            print(f"\n--- Post-hoc: Index of Difficulty (Main Effect) ---")
        try:
            tukey_id = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['ID_cat'],
                alpha=0.05
            )
            results[mt_col]['posthoc_id'] = tukey_id
            if verbose:
                # Only show significant differences for ID (too many comparisons)
                tukey_df = pd.DataFrame(data=tukey_id.summary().data[1:], 
                                       columns=tukey_id.summary().data[0])
                significant = tukey_df[tukey_df['reject'] == True]
                if len(significant) > 0:
                    print(f"Significant pairwise differences (out of {len(tukey_df)} comparisons):")
                    print(significant.to_string(index=False))
                else:
                    print("No significant pairwise differences found.")
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (ID): {e}")
            results[mt_col]['posthoc_id'] = None
        
        # ========== POST-HOC TESTS: INTERACTION EFFECTS ==========
        
        # 5. Feedback × Buffer Interaction
        if verbose:
            print(f"\n--- Post-hoc: Feedback × Buffer Interaction (Simple Effects) ---")
        try:
            df_clean['feedback_buffer'] = df_clean['feedbackMode'].astype(str) + '_' + df_clean['buffer_cat'].astype(str)
            tukey_fb = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['feedback_buffer'],
                alpha=0.05
            )
            results[mt_col]['posthoc_feedback_buffer'] = tukey_fb
            if verbose:
                print(tukey_fb)
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (feedback × buffer): {e}")
            results[mt_col]['posthoc_feedback_buffer'] = None
        
        # 6. Feedback × Indication Interaction
        if verbose:
            print(f"\n--- Post-hoc: Feedback × Indication Interaction (Simple Effects) ---")
        try:
            df_clean['feedback_indication'] = df_clean['feedbackMode'].astype(str) + '_' + df_clean['indication'].astype(str)
            tukey_fi = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['feedback_indication'],
                alpha=0.05
            )
            results[mt_col]['posthoc_feedback_indication'] = tukey_fi
            if verbose:
                print(tukey_fi)
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (feedback × indication): {e}")
            results[mt_col]['posthoc_feedback_indication'] = None
        
        # 7. Buffer × Indication Interaction
        if verbose:
            print(f"\n--- Post-hoc: Buffer × Indication Interaction (Simple Effects) ---")
        try:
            df_clean['buffer_indication'] = df_clean['buffer_cat'].astype(str) + '_' + df_clean['indication'].astype(str)
            tukey_bi = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['buffer_indication'],
                alpha=0.05
            )
            results[mt_col]['posthoc_buffer_indication'] = tukey_bi
            if verbose:
                print(tukey_bi)
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (buffer × indication): {e}")
            results[mt_col]['posthoc_buffer_indication'] = None
        
        # 8. Feedback × Buffer × Indication (3-way interaction)
        if verbose:
            print(f"\n--- Post-hoc: Feedback × Buffer × Indication (3-way, Simple Effects) ---")
        try:
            df_clean['fbi'] = (df_clean['feedbackMode'].astype(str) + '_' + 
                               df_clean['buffer_cat'].astype(str) + '_' + 
                               df_clean['indication'].astype(str))
            tukey_fbi = pairwise_tukeyhsd(
                endog=df_clean[mt_col],
                groups=df_clean['fbi'],
                alpha=0.05
            )
            results[mt_col]['posthoc_feedback_buffer_indication'] = tukey_fbi
            if verbose:
                # Show only significant comparisons
                tukey_df = pd.DataFrame(data=tukey_fbi.summary().data[1:], 
                                       columns=tukey_fbi.summary().data[0])
                significant = tukey_df[tukey_df['reject'] == True]
                if len(significant) > 0:
                    print(f"Significant pairwise differences (out of {len(tukey_df)} comparisons):")
                    print(significant.to_string(index=False))
                else:
                    print("No significant pairwise differences found.")
        except Exception as e:
            if verbose:
                print(f"Error in post-hoc (3-way interaction): {e}")
            results[mt_col]['posthoc_feedback_buffer_indication'] = None
        
        # ========== DESCRIPTIVE STATISTICS BY FACTOR ==========
        if verbose:
            print(f"\n--- Descriptive Statistics ---")
            
            print("\nBy Feedback Mode:")
            desc = df_clean.groupby('feedbackMode', observed=True)[mt_col].agg(['mean', 'std', 'count'])
            print(desc)
            
            print("\nBy Buffer:")
            desc = df_clean.groupby('buffer_cat', observed=True)[mt_col].agg(['mean', 'std', 'count'])
            print(desc)
            
            print("\nBy Indication Mode:")
            desc = df_clean.groupby('indication', observed=True)[mt_col].agg(['mean', 'std', 'count'])
            print(desc)
            
            print("\nBy ID:")
            desc = df_clean.groupby('ID_cat', observed=True)[mt_col].agg(['mean', 'std', 'count'])
            print(desc)
            
            print("\nBy Feedback × Buffer:")
            desc = df_clean.groupby(['feedbackMode', 'buffer_cat'], observed=True)[mt_col].agg(['mean', 'std', 'count'])
            print(desc)
            
            print("\nBy Feedback × Indication:")
            desc = df_clean.groupby(['feedbackMode', 'indication'], observed=True)[mt_col].agg(['mean', 'std', 'count'])
            print(desc)
    
    # ========== SAVE RESULTS ==========
    if save_results:
        stats_dir = Path(up.PROCESSED_DATA) / "statistical_analysis"
        stats_dir.mkdir(parents=True, exist_ok=True)
        
        for mt_col, time_name in time_types:
            if results[mt_col].get('anova') is not None:
                anova_file = stats_dir / f"anova_{mt_col}.csv"
                results[mt_col]['anova'].to_csv(anova_file)
            
            # Save post-hoc results for main effects
            for factor in ['feedback', 'buffer', 'indication', 'id']:
                key = f'posthoc_{factor}'
                if results[mt_col].get(key) is not None:
                    posthoc_file = stats_dir / f"posthoc_{mt_col}_{factor}.csv"
                    tukey_result = results[mt_col][key]
                    tukey_df = pd.DataFrame(data=tukey_result.summary().data[1:], 
                                           columns=tukey_result.summary().data[0])
                    tukey_df.to_csv(posthoc_file, index=False)
            
            # Save post-hoc results for interactions
            for interaction in ['feedback_buffer', 'feedback_indication', 'buffer_indication', 
                               'feedback_buffer_indication']:
                key = f'posthoc_{interaction}'
                if results[mt_col].get(key) is not None:
                    posthoc_file = stats_dir / f"posthoc_{mt_col}_{interaction}.csv"
                    tukey_result = results[mt_col][key]
                    tukey_df = pd.DataFrame(data=tukey_result.summary().data[1:], 
                                           columns=tukey_result.summary().data[0])
                    tukey_df.to_csv(posthoc_file, index=False)
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"Statistical results saved to: {stats_dir}")
            print(f"{'='*80}")
    
    return results


def plot_fitts_law_by_conditions(df_conditions, save_plots=True):
    """
    Create MT vs ID plots for each combination of feedback mode, buffer, and indication mode.
    Each plot contains 3 series: reaching time, indication down, and indication up.
    
    Parameters:
    -----------
    df_conditions : DataFrame
        DataFrame with condition-level Fitts law metrics (output from calculate_fitts_law_metrics)
    save_plots : bool
        If True, save plots to files
        
    Returns:
    --------
    list
        List of figure objects created
    """
    # Create output directory for plots
    plot_dir = Path(up.PROCESSED_DATA) / "fitts_plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all unique combinations (excluding time_type)
    conditions = df_conditions[['feedbackMode', 'buffer', 'indication']].drop_duplicates()
    
    figures = []
    
    print("\n" + "="*80)
    print("CREATING FITTS LAW PLOTS (MT vs ID)")
    print("="*80)
    
    for _, cond in conditions.iterrows():
        feedback = cond['feedbackMode']
        buffer = cond['buffer']
        indication = cond['indication']
        
        # Filter data for this condition combination
        mask = (
            (df_conditions['feedbackMode'] == feedback) & 
            (df_conditions['buffer'] == buffer) & 
            (df_conditions['indication'] == indication)
        )
        data = df_conditions[mask].copy()
        
        if len(data) == 0:
            continue
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Plot each time type
        time_configs = [
            ('reaching', 'Reaching Time', 'o', '#1f77b4'),
            ('indication_down', 'Indication Down', 's', '#ff7f0e'),
            ('indication_up', 'Indication Up', '^', '#2ca02c')
        ]
        
        for time_type, label, marker, color in time_configs:
            subset = data[data['time_type'] == time_type].copy()
            
            if len(subset) == 0:
                continue
            
            # Calculate nominal ID from W and A
            # ID = log2(A/W + 1)
            subset['ID_nominal'] = np.log2(subset['A'] / subset['W'] + 1)
            
            # Sort by ID for proper line plotting
            subset = subset.sort_values('ID_nominal')
            
            # Plot points
            ax.errorbar(subset['ID_nominal'], subset['MT_mean'], 
                       yerr=subset['MT_std'] / np.sqrt(subset['n_trials']), 
                       fmt=marker, markersize=8, capsize=5, capthick=2, 
                       label=label, color=color, ecolor=color, alpha=0.8)
            
            # Fit line
            if len(subset) > 1:
                slope, intercept, r_value, _, _ = stats.linregress(
                    subset['ID_nominal'], subset['MT_mean']
                )
                x_line = np.array([subset['ID_nominal'].min(), subset['ID_nominal'].max()])
                y_line = intercept + slope * x_line
                ax.plot(x_line, y_line, '--', color=color, linewidth=2, 
                       label=f'{label}: MT={intercept:.2f}+{slope:.2f}*ID (R²={r_value**2:.3f})')
        
        # Formatting
        ax.set_xlabel('Index of Difficulty (ID)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Movement Time (s)', fontsize=12, fontweight='bold')
        
        title = f"Fitts' Law: {feedback.capitalize()} Feedback | Buffer={buffer}px | {indication.capitalize()}"
        ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
        
        ax.legend(loc='best', fontsize=9, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        # Save plot
        if save_plots:
            filename = f"fitts_law_{feedback}_buffer{buffer}_{indication}.png"
            filepath = plot_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filename}")
        
        figures.append(fig)
    
    print(f"\nTotal plots created: {len(figures)}")
    print(f"Plots saved to: {plot_dir}")
    print("="*80)
    
    return figures


def plot_fitts_law_by_time_type(df_conditions, save_plots=True):
    """
    Create MT vs ID plots grouped by time type (reaching, indication down, indication up).
    Each plot shows all conditions as separate series.
    
    Parameters:
    -----------
    df_conditions : DataFrame
        DataFrame with condition-level Fitts law metrics (output from calculate_fitts_law_metrics)
    save_plots : bool
        If True, save plots to files
        
    Returns:
    --------
    list
        List of figure objects created
    """
    # Create output directory for plots
    plot_dir = Path(up.PROCESSED_DATA) / "fitts_plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all unique condition combinations
    conditions = df_conditions[['feedbackMode', 'buffer', 'indication']].drop_duplicates()
    
    # Define colors for different conditions
    colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    
    figures = []
    
    print("\n" + "="*80)
    print("CREATING FITTS LAW PLOTS BY TIME TYPE (All Conditions)")
    print("="*80)
    
    # Define the three time types to plot
    time_types = [
        ('reaching', 'Reaching Time'),
        ('indication_down', 'Indication Down'),
        ('indication_up', 'Indication Up')
    ]
    
    for time_type, title_name in time_types:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        legend_entries = []
        
        # Filter data for this time type
        time_data = df_conditions[df_conditions['time_type'] == time_type].copy()
        
        # Calculate nominal ID
        time_data['ID_nominal'] = np.log2(time_data['A'] / time_data['W'] + 1)
        
        for idx, (_, cond) in enumerate(conditions.iterrows()):
            feedback = cond['feedbackMode']
            buffer = cond['buffer']
            indication = cond['indication']
            
            # Filter data for this condition
            mask = (
                (time_data['feedbackMode'] == feedback) & 
                (time_data['buffer'] == buffer) & 
                (time_data['indication'] == indication)
            )
            data = time_data[mask].copy()
            
            if len(data) == 0:
                continue
            
            # Sort by ID
            data = data.sort_values('ID_nominal')
            
            # Create label
            label = f"{feedback.capitalize()}/Buf{buffer}/{indication.capitalize()}"
            
            # Plot with error bars
            color = colors[idx % len(colors)]
            marker = markers[idx % len(markers)]
            
            ax.errorbar(data['ID_nominal'], data['MT_mean'], 
                       yerr=data['MT_std'] / np.sqrt(data['n_trials']), 
                       fmt=marker, markersize=7, capsize=4, capthick=1.5, 
                       label=label, color=color, ecolor=color, alpha=0.7, linewidth=1.5)
            
            # Fit line
            if len(data) > 1:
                slope, intercept, r_value, _, _ = stats.linregress(
                    data['ID_nominal'], data['MT_mean']
                )
                x_line = np.linspace(data['ID_nominal'].min(), data['ID_nominal'].max(), 100)
                y_line = intercept + slope * x_line
                ax.plot(x_line, y_line, '--', color=color, linewidth=1.5, alpha=0.5)
                
                legend_entries.append(f"{label}: MT={intercept:.2f}+{slope:.2f}*ID (R²={r_value**2:.2f})")
        
        # Formatting
        ax.set_xlabel('Index of Difficulty (ID)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Movement Time (s)', fontsize=13, fontweight='bold')
        
        title = f"Fitts' Law - {title_name}: All Conditions"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Legend with regression equations
        ax.legend(legend_entries, loc='best', fontsize=8, framealpha=0.95, 
                 ncol=2 if len(legend_entries) > 4 else 1)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        # Save plot
        if save_plots:
            filename = f"fitts_law_all_conditions_{time_type}.png"
            filepath = plot_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filename}")
        
        figures.append(fig)
    
    print(f"\nTotal plots created: {len(figures)}")
    print(f"Plots saved to: {plot_dir}")
    print("="*80)
    
    return figures


if __name__ == "__main__":
    # Run Fitts law analysis - returns condition-level metrics
    df_conditions = calculate_fitts_law_metrics(save_results=True, verbose=True)
    
    # Create plots by condition (one plot per condition combination)
    figs1 = plot_fitts_law_by_conditions(df_conditions, save_plots=True)
    
    # Create plots by time type (one plot per time type with all conditions)
    figs2 = plot_fitts_law_by_time_type(df_conditions, save_plots=True)
    
    # Perform statistical analysis (ANOVA and post-hoc tests)
    # Note: This would need to be updated to work with condition-level data
    # stats_results = perform_statistical_analysis(df_conditions, save_results=True, verbose=True)
    
    # Close all figures to free memory
    plt.close('all')
