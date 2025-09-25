import pandas as pd
import utils_paths as up
import numpy as np
import json
import os

def print_unsuccessful_trials(trials_path=up.TRIALS_FILE, output_path= up.TEST_QA_FILE ):
    # Cargar el archivo
    df = pd.read_parquet(trials_path)

    # Filtrar por success == False
    df_fail = df[df['success'] == False]

    def count_if_possible(x):
        try:
            return len(x)
        except:
            return 0

    # Filtrar por longitud de outtimes >= reachingtimes
    filtered_fail = df_fail[df_fail.apply(
        lambda row: count_if_possible(row['reachingTimes']) > count_if_possible(row['outTimes']),
        axis=1
    )]

    # Seleccionar campos clave para revisión
    fields_to_show = [
        'participantId', 'trialIndex', 'success', 'buffer', 'bufferReachingTimes','bufferOutTimes', 
        'reachingTimes', 'outTimes','confirmationTime', 'feedbackMode', 'indication', 'inTarget', 'inTargetBuffer',
        'clickDownTime', 'clickUpTime' #, 'cursorPositions'
    ]

    failed_trials_info = filtered_fail[fields_to_show].to_dict(orient='records')
    failed_trials_info = convert_ndarray_to_list(failed_trials_info)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(failed_trials_info, f, indent=4)

    print(f'Printed {len(failed_trials_info)} trials')


def convert_ndarray_to_list(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [convert_ndarray_to_list(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_ndarray_to_list(v) for k, v in obj.items()}
    else:
        return obj

print_unsuccessful_trials()