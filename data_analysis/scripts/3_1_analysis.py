import pandas as pd
import numpy as np
from utils_paths import TRIALS_FILE, SEGMENTS_FILE, ANALYSIS_FILE_1
from collections import defaultdict
from tqdm import tqdm

# Cargar archivos
df_trials = pd.read_parquet(TRIALS_FILE)
df_segments = pd.read_parquet(SEGMENTS_FILE)

print(df_trials.columns)
print(df_segments.columns)

# Asegurar que los campos de tiempo estén como float
for col in ['Indication_down_t', 'Indication_up_t', 'Reaching_time']:
    df_trials[col] = df_trials[col].apply(lambda x: np.array(x, dtype=float) if isinstance(x, list) else x)

# Inicializar lista de resultados
results = []

for idx, trial in tqdm(df_trials.iterrows(), total=len(df_trials)):
    trial_id = trial['trialDocId']
    participant_id = trial['participantId']

    reaching_times = trial['Reaching_times']
    out_times = trial['Out_times']
    


    if not isinstance(trial['Reaching_times'], np.ndarray) or len(trial['Reaching_times']) == 0:
        continue  # ignorar si no hay reaching

    times = {
        'reaching': trial['Reaching_time'],
        'clickDown':  trial['Indication_down_t'],
        'clickUp': trial['Indication_up_t']
    }


    # Obtener los segmentos de ese trial
    segs = df_segments[(df_segments['trialDocId'] == trial_id) ]

    #print(f"Trial {trial_id} - Reaching times: {reaching_times}, Out times: {out_times}, Segments: {len(segs)}")

    def get_movement_type(t):
        seg = segs[(segs['t_start'] <= t) & (segs['t_end'] >= t)]
        if len(seg) == 0:
            return 'pause'
        return seg.iloc[0]['type']

    movement_types = {
        'reaching': get_movement_type(times['reaching']),
        'clickDown': get_movement_type(times['clickDown']),
        'clickUp': get_movement_type(times['clickUp'])
    }


    for time_type  in ['reaching', 'clickDown', 'clickUp']:
        movement_type_sum = 'rapid' if 'rapid' in movement_types[time_type] else movement_types[time_type]
        sucess_type = 'fail'
        if len(out_times) < len(reaching_times):
            sucess_type = 'success +1 reach'
            if len(reaching_times) == 1:
                sucess_type = 'success no outs'
        results.append({
            'participantId': participant_id,
            'event': time_type,
            'trialindex': trial_id,
            #'ID': trial['ID'],
            'A': trial['A'],
            'W': trial['W'],
            'feedbackMode': trial['feedbackMode'],
            'buffer': trial['buffer'],
            'reaching_count': len(reaching_times),
            'outs_count': len(out_times),
            'indication': trial['indication'],
            'movement_type_reach': movement_types[time_type],
            'movement_type_sum': movement_type_sum,
            'sucess_type': sucess_type
        })

# Convertir a DataFrame
df_results = pd.DataFrame(results)

print(df_results.head(10))

# Mostrar conteo agrupado por columnas clave
grouped = df_results.groupby([
    'event',
    'movement_type_reach',
    'movement_type_sum',
    #'ID',
    'A',
    'W',
    'feedbackMode',
    'buffer',
    'reaching_count',
    'outs_count',
    'indication',
    'sucess_type'
]).size().reset_index(name='count')

# Guardar resultados
grouped.to_csv(ANALYSIS_FILE_1, index=False)
#print(grouped.head(40))
