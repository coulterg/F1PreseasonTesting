import os
import pandas as pd
from parse.parsing_logic import process_image_to_dataframe
from parse.ocr_utils import ocr_table, ocr_standard  


INPUT_DIR = "./data/input_gifs"
OUTPUT_CSV = "./output/parsed_results2.csv"

BATCH_SIZE = 3

if __name__ == "__main__":
    # Load existing progress
    if os.path.exists(OUTPUT_CSV):
        df_master = pd.read_csv(OUTPUT_CSV)
        processed = set(df_master['FILENAME'].unique())
    else:
        df_master = pd.DataFrame()
        processed = set()

    file_list = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.gif')]
    file_list = [f for f in file_list if f not in processed]
    print(f"Found {len(file_list)} unprocessed GIFs.\n")

    batch = []
    bad_log = []

    for i, fname in enumerate(file_list, 1):
        path = os.path.join(INPUT_DIR, fname)
        print(f"[{i}] Processing {fname}")

        try:
            df, bad_rows = process_image_to_dataframe(
                image_path=path
            )
            batch.append(df)
            bad_log.extend(bad_rows) 

        except Exception as e:
            print(f"⚠️ Failed to process {fname}: {e}")
            continue

        # Save after every BATCH_SIZE files
        if i % BATCH_SIZE == 0 or i == len(file_list):
            if batch:
                combined = pd.concat(batch, ignore_index=True)
                df_master = pd.concat([df_master, combined], ignore_index=True)
                df_master.to_csv(OUTPUT_CSV, index=False)
                print(f"✔ Saved {len(batch)} entries to {OUTPUT_CSV}")
                batch = []

            if bad_log:
                error_df = pd.DataFrame(bad_log)
                error_df.to_csv("output/ocr_failed_rows.csv", mode='a', index=False, header=not os.path.exists("output/ocr_failed_rows.csv"))
                bad_log = []  # ✅ reset for next batch
                