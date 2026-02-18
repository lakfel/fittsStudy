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


def calculate_effective_width(group_data, position_col_x, position_col_y):
    """
    Calculate effective width (We) for a group of trials with same conditions.
    We = 4.133 * SDx where SDx is the standard deviation of endpoint positions.
    
    Using the bivariate approach: We = 4.133 * sqrt(SD_x^2 + SD_y^2)
    """
    if len(group_data) < 2:
        return np.nan
    
    std_x = group_data[position_col_x].std()
    std_y = group_data[position_col_y].std()
    
    # Bivariate effective width
    we = 4.133 * np.sqrt(std_x**2 + std_y**2)
    
    return we


def calculate_effective_amplitude(row, start_x=640, start_y=360):
    """
    Calculate effective amplitude (Ae) for a trial.
    Ae is the actual distance from start position to endpoint.
    
    Assuming start position is center of screen (640, 360)
    """
    # Calculate for each endpoint
    results = {}
    
    # For indication down
    if pd.notna(row['Indication_down_x']) and pd.notna(row['Indication_down_y']):
        ae_down = np.sqrt(
            (row['Indication_down_x'] - row['Start_position_x'])**2 + 
            (row['Indication_down_y'] - row['Start_position_y'])**2
        )
        results['Ae_indication_down'] = ae_down
    else:
        results['Ae_indication_down'] = np.nan
    
    # For indication up
    if pd.notna(row['Indication_up_x']) and pd.notna(row['Indication_up_y']):
        ae_up = np.sqrt(
            (row['Indication_up_x'] - row['Start_position_x'])**2 + 
            (row['Indication_up_y'] - row['Start_position_y'])**2
        )
        results['Ae_indication_up'] = ae_up
    else:
        results['Ae_indication_up'] = np.nan
    
    # For reaching time endpoint
    if pd.notna(row['Reaching_pos_x']) and pd.notna(row['Reaching_pos_y']):
        ae_reaching = np.sqrt(
            (row['Reaching_pos_x'] - row['Start_position_x'])**2 + 
            (row['Reaching_pos_y'] - row['Start_position_y'])**2
        )
        results['Ae_reaching'] = ae_reaching
    else:
        results['Ae_reaching'] = np.nan

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
    Calculate Fitts law metrics for all trials.
    
    Parameters:
    -----------
    save_results : bool
        If True, save results to CSV files
    verbose : bool
        If True, print detailed analysis summary
        
    Returns:
    --------
    tuple
        (df_success, condition_summary) DataFrames with Fitts law metrics
    """
    
    # Load trials data
    df_trials = pd.read_csv(up.TRIALS_FILE_CSV)
    
    # Get list of excluded participants based on error rate threshold
    if verbose:
        print("="*80)
        print("PARTICIPANT FILTERING")
        print("="*80)
    excluded_participants = up.get_excluded_participants_by_error_rate()
    
    # Filter out excluded participants
    df_trials = df_trials[~df_trials['participantId'].isin(excluded_participants)]
    
    # Filter successful trials only for Fitts law analysis
    df_success = df_trials[df_trials['success'] == True].copy()
    
    if verbose:
        print(f"\nTotal trials (after filtering participants): {len(df_trials)}")
        print(f"Successful trials: {len(df_success)}")
        print(f"Success rate: {len(df_success)/len(df_trials)*100:.2f}%")
    
    # Filter outliers based on indication_up time
    df_success = filter_outliers_by_indication_up_time(df_success, n_std=3, verbose=verbose)

    # Step 1: Calculate effective amplitude for each trial
    df_success[['Ae_indication_down', 'Ae_indication_up', 'Ae_reaching']] = df_success.apply(
        calculate_effective_amplitude, axis=1
        )

    # Step 2: Calculate effective width for each condition group
    # Group by experimental conditions
    grouping_vars = ['participantId', 'W', 'A', 'buffer', 'indication', 'feedbackMode']

    # Calculate We for indication down positions
    we_down = df_success.groupby(grouping_vars).apply(
        lambda g: calculate_effective_width(g, 'Indication_down_x', 'Indication_down_y'),
        include_groups=False
    ).reset_index()
    we_down.columns = [*grouping_vars, 'We_indication_down']

    # Calculate We for indication up positions
    we_up = df_success.groupby(grouping_vars).apply(
        lambda g: calculate_effective_width(g, 'Indication_up_x', 'Indication_up_y'),
        include_groups=False
    ).reset_index()
    we_up.columns = [*grouping_vars, 'We_indication_up']

    # Calculate We for reaching time positions
    we_reaching = df_success.groupby(grouping_vars).apply(
        lambda g: calculate_effective_width(g, 'Reaching_pos_x', 'Reaching_pos_y'),
        include_groups=False
    ).reset_index()
    we_reaching.columns = [*grouping_vars, 'We_reaching']

    # Step 3: Merge We back to trials
    df_success = df_success.merge(we_down, on=grouping_vars, how='left')
    df_success = df_success.merge(we_up, on=grouping_vars, how='left')
    df_success = df_success.merge(we_reaching, on=grouping_vars, how='left')

    # Step 4: Calculate effective ID (IDe = log2(Ae/We + 1))
    df_success['IDe_indication_down'] = np.log2(
        df_success['Ae_indication_down'] / df_success['We_indication_down'] + 1
    )
    df_success['IDe_indication_up'] = np.log2(
        df_success['Ae_indication_up'] / df_success['We_indication_up'] + 1
    )
    df_success['IDe_reaching'] = np.log2(
        df_success['Ae_reaching'] / df_success['We_reaching'] + 1
    )

    # Step 5: Movement Times (MT) - convert from milliseconds to seconds
    df_success['MT_reaching'] = df_success['Reaching_time'] / 1000.0
    df_success['MT_indication_down'] = df_success['Indication_down_t'] / 1000.0
    df_success['MT_indication_up'] = df_success['Indication_up_t'] / 1000.0

    # Step 6: Calculate Throughput (TP = IDe / MT) in bits per second
    # For reaching time - using indication down endpoint (most common in Fitts studies)
    df_success['TP_reaching'] = df_success['IDe_reaching'] / df_success['MT_reaching']

    # For indication down time
    df_success['TP_indication_down'] = df_success['IDe_indication_down'] / df_success['MT_indication_down']

    # For indication up time
    df_success['TP_indication_up'] = df_success['IDe_indication_up'] / df_success['MT_indication_up']

    # Step 7: Add nominal ID for comparison (ID = log2(A/W + 1))
    df_success['ID_nominal'] = np.log2(df_success['A'] / df_success['W'] + 1)

    # Step 8: Summary statistics
    if verbose:
        print("\n" + "="*80)
        print("FITTS LAW ANALYSIS SUMMARY")
        print("="*80)

        print("\n1. REACHING TIME Analysis:")
        print(f"   Mean MT: {df_success['MT_reaching'].mean():.3f} s (SD: {df_success['MT_reaching'].std():.3f})")
        print(f"   Mean TP: {df_success['TP_reaching'].mean():.2f} bits/s (SD: {df_success['TP_reaching'].std():.2f})")
        print(f"   Mean IDe: {df_success['IDe_reaching'].mean():.2f} (SD: {df_success['IDe_reaching'].std():.2f})")

        print("\n2. INDICATION DOWN Analysis:")
        print(f"   Mean MT: {df_success['MT_indication_down'].mean():.3f} s (SD: {df_success['MT_indication_down'].std():.3f})")
        print(f"   Mean TP: {df_success['TP_indication_down'].mean():.2f} bits/s (SD: {df_success['TP_indication_down'].std():.2f})")
        print(f"   Mean IDe: {df_success['IDe_indication_down'].mean():.2f} (SD: {df_success['IDe_indication_down'].std():.2f})")

        print("\n3. INDICATION UP Analysis:")
        print(f"   Mean MT: {df_success['MT_indication_up'].mean():.3f} s (SD: {df_success['MT_indication_up'].std():.3f})")
        print(f"   Mean TP: {df_success['TP_indication_up'].mean():.2f} bits/s (SD: {df_success['TP_indication_up'].std():.2f})")
        print(f"   Mean IDe: {df_success['IDe_indication_up'].mean():.2f} (SD: {df_success['IDe_indication_up'].std():.2f})")

        print("\n4. COMPARISON:")
        print(f"   Nominal ID (mean): {df_success['ID_nominal'].mean():.2f}")
        print(f"   Effective ID (mean): {df_success['IDe_reaching'].mean():.2f}")
        print(f"   We_reaching (mean): {df_success['We_reaching'].mean():.2f} px")
        print(f"   Ae_reaching (mean): {df_success['Ae_reaching'].mean():.2f} px")

    # Step 9: Aggregate by condition
    condition_summary = df_success.groupby(['W', 'A', 'buffer', 'indication', 'feedbackMode']).agg({
        'MT_reaching': ['mean', 'std', 'count'],
        'MT_indication_down': ['mean', 'std'],
        'MT_indication_up': ['mean', 'std'],
        'TP_reaching': ['mean', 'std'],
        'TP_indication_down': ['mean', 'std'],
        'TP_indication_up': ['mean', 'std'],
        'IDe_indication_down': ['mean', 'std'],
        'IDe_indication_up': ['mean', 'std'],
        'ID_nominal': 'first',
        'We_indication_down': 'first',
        'We_indication_up': 'first',
        'Ae_indication_down': 'mean',
        'Ae_indication_up': 'mean'
    }).reset_index()

    # Flatten column names
    condition_summary.columns = ['_'.join(col).strip('_') for col in condition_summary.columns.values]

    if verbose:
        print("\n5. CONDITIONS ANALYZED:")
        print(f"   Total conditions: {len(condition_summary)}")
        print(f"   W values: {sorted(df_success['W'].unique())}")
        print(f"   A values: {sorted(df_success['A'].unique())}")
        print(f"   Buffer values: {sorted(df_success['buffer'].unique())}")
        print(f"   Indication modes: {sorted(df_success['indication'].unique())}")
        print(f"   Feedback modes: {sorted(df_success['feedbackMode'].unique())}")

    # Step 10: Save results
    if save_results:
        output_fitts_trials = Path(up.PROCESSED_CSV_DATA) / "fitts_trials_analysis.csv"
        output_fitts_conditions = Path(up.PROCESSED_CSV_DATA) / "fitts_conditions_summary.csv"

        # Select relevant columns for output
        output_cols = [
            'trialDocId', 'participantId', 'W', 'A', 'buffer', 'indication', 'feedbackMode',
            'Target_position_x', 'Target_position_y',
            'Indication_down_x', 'Indication_down_y', 'Indication_up_x', 'Indication_up_y',
            'ID_nominal', 
            'IDe_indication_down', 'IDe_indication_up',
            'Ae_indication_down', 'Ae_indication_up',
            'We_indication_down', 'We_indication_up',
            'MT_reaching', 'MT_indication_down', 'MT_indication_up',
            'TP_reaching', 'TP_indication_down', 'TP_indication_up',
            'Distance_to_target_indication_down', 'Distance_to_target_indication_up',
            'success'
        ]

        df_success[output_cols].to_csv(output_fitts_trials, index=False)
        condition_summary.to_csv(output_fitts_conditions, index=False)

        if verbose:
            print(f"\n{'='*80}")
            print(f"Results saved to:")
            print(f"  - {output_fitts_trials}")
            print(f"  - {output_fitts_conditions}")
            print(f"{'='*80}")

    # Step 11: Quick regression check (Fitts' Law: MT = a + b*ID)
    if verbose:
        print("\n" + "="*80)
        print("FITTS LAW REGRESSION (MT ~ ID)")
        print("="*80)

        # For reaching time
        valid_reaching = df_success[['IDe_indication_down', 'MT_reaching']].dropna()
        if len(valid_reaching) > 0:
            slope_r, intercept_r, r_value_r, p_value_r, std_err_r = stats.linregress(
                valid_reaching['IDe_indication_down'], 
                valid_reaching['MT_reaching']
            )
            print(f"\n1. REACHING TIME: MT = {intercept_r:.3f} + {slope_r:.3f} * IDe")
            print(f"   R² = {r_value_r**2:.3f}, p = {p_value_r:.2e}")

        # For indication down
        valid_down = df_success[['IDe_indication_down', 'MT_indication_down']].dropna()
        if len(valid_down) > 0:
            slope_d, intercept_d, r_value_d, p_value_d, std_err_d = stats.linregress(
                valid_down['IDe_indication_down'], 
                valid_down['MT_indication_down']
            )
            print(f"\n2. INDICATION DOWN: MT = {intercept_d:.3f} + {slope_d:.3f} * IDe")
            print(f"   R² = {r_value_d**2:.3f}, p = {p_value_d:.2e}")

        # For indication up
        valid_up = df_success[['IDe_indication_up', 'MT_indication_up']].dropna()
        if len(valid_up) > 0:
            slope_u, intercept_u, r_value_u, p_value_u, std_err_u = stats.linregress(
                valid_up['IDe_indication_up'], 
                valid_up['MT_indication_up']
            )
            print(f"\n3. INDICATION UP: MT = {intercept_u:.3f} + {slope_u:.3f} * IDe")
            print(f"   R² = {r_value_u**2:.3f}, p = {p_value_u:.2e}")

        print("\n" + "="*80)
        print("Analysis complete!")
        print("="*80)
    
    return df_success, condition_summary


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


def plot_fitts_law_by_conditions(df_success, save_plots=True):
    """
    Create MT vs ID plots for each combination of feedback mode, buffer, and indication mode.
    Each plot contains 3 series: reaching time, indication down, and indication up.
    
    Parameters:
    -----------
    df_success : DataFrame
        DataFrame with Fitts law metrics (output from calculate_fitts_law_metrics)
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
    
    # Get all unique combinations
    conditions = df_success[['feedbackMode', 'buffer', 'indication']].drop_duplicates()
    
    figures = []
    
    print("\n" + "="*80)
    print("CREATING FITTS LAW PLOTS (MT vs ID)")
    print("="*80)
    
    for _, cond in conditions.iterrows():
        feedback = cond['feedbackMode']
        buffer = cond['buffer']
        indication = cond['indication']
        
        # Filter data for this condition
        mask = (
            (df_success['feedbackMode'] == feedback) & 
            (df_success['buffer'] == buffer) & 
            (df_success['indication'] == indication)
        )
        data = df_success[mask].copy()
        
        if len(data) == 0:
            continue
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Plot 1: Reaching Time
        # Group by ID_nominal and calculate mean MT
        reaching_avg = data.groupby('ID_nominal')['MT_reaching'].agg(['mean', 'std', 'count']).reset_index()
        reaching_avg['se'] = reaching_avg['std'] / np.sqrt(reaching_avg['count'])  # standard error
        
        if len(reaching_avg) > 0:
            ax.errorbar(reaching_avg['ID_nominal'], reaching_avg['mean'], 
                       yerr=reaching_avg['se'], fmt='o', markersize=8, 
                       capsize=5, capthick=2, label='Reaching Time', 
                       color='#1f77b4', ecolor='#1f77b4', alpha=0.8)
            
            # Fit line using averaged data
            slope_r, intercept_r, r_value_r, _, _ = stats.linregress(
                reaching_avg['ID_nominal'], 
                reaching_avg['mean']
            )
            x_line = np.array([reaching_avg['ID_nominal'].min(), 
                              reaching_avg['ID_nominal'].max()])
            y_line = intercept_r + slope_r * x_line
            ax.plot(x_line, y_line, '--', color='#1f77b4', linewidth=2, 
                   label=f'Reaching: MT={intercept_r:.2f}+{slope_r:.2f}*ID (R²={r_value_r**2:.3f})')
        
        # Plot 2: Indication Down
        # Group by ID_nominal and calculate mean MT
        down_avg = data.groupby('ID_nominal')['MT_indication_down'].agg(['mean', 'std', 'count']).reset_index()
        down_avg['se'] = down_avg['std'] / np.sqrt(down_avg['count'])
        
        if len(down_avg) > 0:
            ax.errorbar(down_avg['ID_nominal'], down_avg['mean'], 
                       yerr=down_avg['se'], fmt='s', markersize=8, 
                       capsize=5, capthick=2, label='Indication Down', 
                       color='#ff7f0e', ecolor='#ff7f0e', alpha=0.8)
            
            # Fit line using averaged data
            slope_d, intercept_d, r_value_d, _, _ = stats.linregress(
                down_avg['ID_nominal'], 
                down_avg['mean']
            )
            x_line = np.array([down_avg['ID_nominal'].min(), 
                              down_avg['ID_nominal'].max()])
            y_line = intercept_d + slope_d * x_line
            ax.plot(x_line, y_line, '--', color='#ff7f0e', linewidth=2, 
                   label=f'Indication Down: MT={intercept_d:.2f}+{slope_d:.2f}*ID (R²={r_value_d**2:.3f})')
        
        # Plot 3: Indication Up
        # Group by ID_nominal and calculate mean MT
        up_avg = data.groupby('ID_nominal')['MT_indication_up'].agg(['mean', 'std', 'count']).reset_index()
        up_avg['se'] = up_avg['std'] / np.sqrt(up_avg['count'])
        
        if len(up_avg) > 0:
            ax.errorbar(up_avg['ID_nominal'], up_avg['mean'], 
                       yerr=up_avg['se'], fmt='^', markersize=8, 
                       capsize=5, capthick=2, label='Indication Up', 
                       color='#2ca02c', ecolor='#2ca02c', alpha=0.8)
            
            # Fit line using averaged data
            slope_u, intercept_u, r_value_u, _, _ = stats.linregress(
                up_avg['ID_nominal'], 
                up_avg['mean']
            )
            x_line = np.array([up_avg['ID_nominal'].min(), 
                              up_avg['ID_nominal'].max()])
            y_line = intercept_u + slope_u * x_line
            ax.plot(x_line, y_line, '--', color='#2ca02c', linewidth=2, 
                   label=f'Indication Up: MT={intercept_u:.2f}+{slope_u:.2f}*ID (R²={r_value_u**2:.3f})')
        
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


def plot_fitts_law_by_time_type(df_success, save_plots=True):
    """
    Create MT vs ID plots grouped by time type (reaching, indication down, indication up).
    Each plot shows all conditions as separate series.
    
    Parameters:
    -----------
    df_success : DataFrame
        DataFrame with Fitts law metrics (output from calculate_fitts_law_metrics)
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
    
    # Get all unique combinations
    conditions = df_success[['feedbackMode', 'buffer', 'indication']].drop_duplicates()
    
    # Define colors for different conditions
    colors = plt.cm.tab10(np.linspace(0, 1, len(conditions)))
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    
    figures = []
    
    print("\n" + "="*80)
    print("CREATING FITTS LAW PLOTS BY TIME TYPE (All Conditions)")
    print("="*80)
    
    # Define the three time types to plot
    time_types = [
        ('MT_reaching', 'Reaching Time', 'reaching'),
        ('MT_indication_down', 'Indication Down', 'indication_down'),
        ('MT_indication_up', 'Indication Up', 'indication_up')
    ]
    
    for mt_col, title_name, filename_suffix in time_types:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        legend_entries = []
        
        for idx, (_, cond) in enumerate(conditions.iterrows()):
            feedback = cond['feedbackMode']
            buffer = cond['buffer']
            indication = cond['indication']
            
            # Filter data for this condition
            mask = (
                (df_success['feedbackMode'] == feedback) & 
                (df_success['buffer'] == buffer) & 
                (df_success['indication'] == indication)
            )
            data = df_success[mask].copy()
            
            if len(data) == 0:
                continue
            
            # Group by ID_nominal and calculate mean MT
            avg_data = data.groupby('ID_nominal')[mt_col].agg(['mean', 'std', 'count']).reset_index()
            avg_data['se'] = avg_data['std'] / np.sqrt(avg_data['count'])
            
            if len(avg_data) > 0:
                # Create label
                label = f"{feedback.capitalize()}/Buf{buffer}/{indication.capitalize()}"
                
                # Plot with error bars
                color = colors[idx % len(colors)]
                marker = markers[idx % len(markers)]
                
                ax.errorbar(avg_data['ID_nominal'], avg_data['mean'], 
                           yerr=avg_data['se'], fmt=marker, markersize=7, 
                           capsize=4, capthick=1.5, label=label, 
                           color=color, ecolor=color, alpha=0.7, linewidth=1.5)
                
                # Fit line
                slope, intercept, r_value, _, _ = stats.linregress(
                    avg_data['ID_nominal'], 
                    avg_data['mean']
                )
                x_line = np.linspace(avg_data['ID_nominal'].min(), 
                                    avg_data['ID_nominal'].max(), 100)
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
            filename = f"fitts_law_all_conditions_{filename_suffix}.png"
            filepath = plot_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"Saved: {filename}")
        
        figures.append(fig)
    
    print(f"\nTotal plots created: {len(figures)}")
    print(f"Plots saved to: {plot_dir}")
    print("="*80)
    
    return figures


if __name__ == "__main__":
    # Run Fitts law analysis when script is executed directly
    df_fitts, df_conditions = calculate_fitts_law_metrics(save_results=True, verbose=True)
    
    # Perform statistical analysis (ANOVA and post-hoc tests)
    stats_results = perform_statistical_analysis(df_fitts, save_results=True, verbose=True)
    
    # Create plots by condition (one plot per condition combination)
    figs1 = plot_fitts_law_by_conditions(df_fitts, save_plots=True)
    
    # Create plots by time type (one plot per time type with all conditions)
    figs2 = plot_fitts_law_by_time_type(df_fitts, save_plots=True)
    
    # Close all figures to free memory
    plt.close('all')
