import pandas as pd
import numpy as np

from processing import load_and_standardize_raw_data, add_test_type, add_position_fields, add_lap_time_millis,\
update_circuit_ids, update_driver_ids, update_entrant_fields

RAW_FILEPATH = 'output/parsed_results_cleaned_with_modern.xlsx'

DRIVERS = pd.read_csv("data/f1db/driver.csv")
SEASON_ENTRANTS = pd.read_csv("data/f1db/season_entrant_driver.csv")
SEASON_CONSTRUCTORS = pd.read_csv("data/f1db/season_entrant_constructor.csv")
CIRCUITS = pd.read_csv("data/f1db/circuit.csv")

# Newly added data - missing from F1DB
DRIVERS_UPDATES = pd.read_csv('data/updates/driver_updates.csv')
SEASON_ENTRANTS_UPDATES = pd.read_csv('data/updates/season_entrant_driver_updates.csv')

# Combine updates

driver_df = pd.concat([DRIVERS, DRIVERS_UPDATES], ignore_index=True)
driver_df.drop_duplicates(subset='id', keep='first', inplace=True)

entrants_df = pd.concat([SEASON_ENTRANTS, SEASON_ENTRANTS_UPDATES], ignore_index=True)
entrants_df.drop_duplicates(subset=['year', 'entrant_id', 'driver_id'])

#---------- Clean up raw timing sheet OCR results -----------------

df = load_and_standardize_raw_data(RAW_FILEPATH)

df = add_test_type(df)

df = add_position_fields(df)

df = add_lap_time_millis(df)

df, unmatched_circuits = update_circuit_ids(df, CIRCUITS)

# Add some combinations for better fuzzy matching

joined_season_driver = entrants_df.merge(driver_df[['id', 'full_name', 'last_name', 'first_name']],
                                              left_on='driver_id',
                                              right_on='id',
                                              how='left')[['year','driver_id', 'full_name', 'last_name', 'first_name']]

joined_season_driver['abbrev_name'] = joined_season_driver.first_name.str[0] + '. ' + joined_season_driver.last_name
joined_season_driver['joined_name'] = joined_season_driver.first_name.str.cat(joined_season_driver.last_name, sep=' ')

joined_season_driver.drop(columns=['first_name'], inplace=True)

driver_df.rename(columns={'id': 'driver_id'}, inplace=True)

df, unmatched_drivers = update_driver_ids(df, joined_season_driver, driver_df,)

df, unmatched_entrants = update_entrant_fields(df, SEASON_CONSTRUCTORS)

# Output structure and fields

df_clean = df[['year', 'test', 'day', 'date', 'test_type', 'circuit_id',
               'position_display_order', 'position_number', 'position_text',
               'driver_id', 'entrant_id', 'constructor_id', 'engine_manufacturer_id',  
               'lap_time', 'lap_time_millis', 'laps', 'lap_number_fastest']]

print(df_clean.info())

df_clean.to_csv('output/testing_results.csv')