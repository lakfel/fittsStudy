from google.cloud import firestore
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime
from pathlib import Path

PROJECT_ID = "fittslaw-6568d"
KEY_PATH = str(Path(__file__).parent.parent / "config" / "key.json")
OUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

creds = service_account.Credentials.from_service_account_file(KEY_PATH)
client = firestore.Client(project=PROJECT_ID, credentials=creds)

def fetch_collection(client, name):
    docs = client.collection(name).stream()
    rows = []
    for d in docs:
        doc = d.to_dict()
        doc["__doc_id"] = d.id
        rows.append(doc)
    return pd.DataFrame(rows)

def main():
    df_participants = fetch_collection(client, "participants")
    df_trials = fetch_collection(client, "fitts_trials")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_participants.to_parquet(OUT_DIR / f"participants_{ts}.parquet", index=False)
    df_trials.to_parquet(OUT_DIR / f"trials_{ts}.parquet", index=False)

    # Si guardaste posiciones dentro de trials como arrays largos, puedes
    # reventarlas luego en 01_flatten_trials.py para una tabla positions

    print("OK:", len(df_participants), "participants;", len(df_trials), "trials")

if __name__ == "__main__":
    main()
