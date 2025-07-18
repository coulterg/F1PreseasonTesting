
import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz

from typing import Optional

from parse.constants import CIRCUIT_ALIASES

COLUMNS_TO_IMPORT = ['POS', 'NAME', 'ENTRY', 'TIME', 'LAPS', 'ON', 'DATE',
       'CIRCUIT', 'YEAR', 'SESSION', 'DAY']

COLUMN_MAPPING = {
    'YEAR': 'year', 
    'SESSION': 'test', 
    'DAY': 'day',
    'DATE': 'date',
    'CIRCUIT': 'circuit_id',
    'POS': 'position_display_order', 
    'NAME': 'driver_name_raw',
    'ENTRY': 'entrant_raw', 
    'TIME': 'lap_time', 
    'LAPS': 'laps', 
    'ON': 'lap_number_fastest'
}

def load_and_standardize_raw_data(filepath: str) -> pd.DataFrame:
    '''Loads raw, unprocessed timing sheet data excel at filepath and renames available columns to match Schema'''

    df = pd.read_excel(filepath, usecols=COLUMNS_TO_IMPORT)
    df.rename(columns = COLUMN_MAPPING, inplace=True)

    df['lap_number_fastest'] = pd.to_numeric(df['lap_number_fastest'], errors='coerce').astype('Int64')

    return df

def add_test_type(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Add's a 'test_type' column to dataframe, based on the month of the test 'date'
    Returns a copy of df with the new column
    '''
    test_month = df.date.dt.month

    df['test_type'] = np.select(
        [
            test_month.isin([1,2,3]),
            test_month.isin([5,6,7]),
            test_month.isin([10,11,12])
        ],
        [
            'pre',
            'mid',
            'post'
        ],
        default='unknown'
    )

    return df

def add_position_fields(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds 'position_number' and 'position_text' fields.
    - position_number is the same as position_display_order if lap_time is not null, else null
    - position_text is a string of position_display_order
    '''
    df['position_number'] = np.where(
        df.lap_time.notna(),
        df.position_display_order,
        pd.NA
    )

    df['position_text'] = df.position_display_order.astype(str)

    return df

def parse_lap_time_to_millis(time_str: str) -> Optional[int]:
    '''
    Converts lap_time string, e.g. '1:19.035' into milliseconds
    Returns None if no laptime
    '''
    if pd.isna(time_str):
        return pd.NA # Need to us pd.NA here - nullable integer, else entire column upcast as float
    try:
        minutes, seconds = time_str.split(':')
        total_millis = int(float(minutes) * 60_000 + float(seconds) * 1_000)
        return total_millis
    except(ValueError, AttributeError):
        return pd.NA
    
def add_lap_time_millis(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds lap_time_millis column, parsing string lap_time
    '''

    df['lap_time_millis'] = df.lap_time.apply(parse_lap_time_to_millis)
    return df


def match_circuit_id(
        name: str, 
        circuit_df: pd.DataFrame, 
        aliases: dict, 
        threshold: int = 85,
        unmatched: Optional[set] = None,
        cache: Optional[dict] = None
) ->Optional[str]:
    '''
    Match raw circuit name to F1DB circuit_id
    '''
    if pd.isna(name):
        return pd.NA
    
    raw = name.strip().lower()

    if raw in aliases:
        return aliases[raw]
    
    if cache is not None and raw in cache:
        return cache[raw]
    
    # Fuzzy match on circuit id
    candidates = circuit_df.id.str.lower().tolist()
    best_match, score, idx = process.extractOne(raw, candidates, scorer=fuzz.ratio)

    if score >= threshold:
        result = circuit_df.iloc[idx]['id']
        if cache is not None:
            cache[raw] = result
        return result
    
    # Fuzzy match on circuit name
    candidates = circuit_df.name.str.lower().tolist()
    best_match, score, idx = process.extractOne(raw, candidates, scorer=fuzz.ratio)

    if score >= threshold:
        result = circuit_df.iloc[idx]['id']
        if cache is not None:
            cache[raw] = result
        return result
    
    # Fuzzy match on circuit full name
    candidates = circuit_df.full_name.str.lower().tolist()
    best_match, score, idx = process.extractOne(raw, candidates, scorer=fuzz.ratio)

    if score >= threshold:
        result = circuit_df.iloc[idx]['id']
        if cache is not None:
            cache[raw] = result
        return result

    if unmatched is not None: # is there a defined unmatched set, even an empty one
        unmatched.add(name)

    return raw

def update_circuit_ids(df: pd.DataFrame, circuit_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Matches raw circuit_id strings to F1DB ids and updates circuit_id column
    '''
    unmatched_set = set()

    df['circuit_id'] = (
        df.groupby(['year', 'test'])['circuit_id']
        .transform(lambda group: match_circuit_id(group.iloc[0], circuit_df, aliases = CIRCUIT_ALIASES, unmatched=unmatched_set))
    )

    return df, unmatched_set

def match_driver_name(
    raw_name: str,
    match_candidates: dict,
    unmatched: Optional[set] = None,
    cache: Optional[dict] = None,
    fallback_candidates: Optional[dict] = None
) -> str:
    """
    Match a raw driver name to the best candidate in a year, using multiple fields.
    Returns the best-matched driver_id.
    """
    if pd.isna(raw_name) or not isinstance(raw_name, str):
        if unmatched is not None:
            unmatched.add(raw_name)
        return raw_name

    raw = raw_name.strip().lower()

    if cache is not None and raw in cache:
        return cache[raw]

    match_results = []

    for field in ['driver_id', 'full_name', 'last_name', 'abbrev_name', 'joined_name']:
        choices = match_candidates.get(field, [])
        if choices is None or len(choices) == 0:
            continue

        best_str, score, idx = process.extractOne(raw, choices, scorer=fuzz.token_sort_ratio)
        matched_id = match_candidates['driver_id'][idx]
        match_results.append((field, score, matched_id))

    if not match_results:
        if unmatched is not None:
            unmatched.add(raw_name)
        return raw_name

    best_field, best_score, best_driver_id = max(match_results, key=lambda x: x[1])
    # best_field, best_score, best_driver_id = max(match_results, key=lambda x: x[1])
    lowest_score = min(score for _, score, _ in match_results)

    # Fallback to global pool if scores are weak
    if lowest_score < 40 and fallback_candidates is not None:
        print(f"⚠️ Low match score ({lowest_score}) for '{raw_name}' — retrying with fallback candidates")

        fallback_name = match_driver_name(
            raw_name,
            fallback_candidates,
            unmatched=unmatched,
            cache=cache,
            fallback_candidates=None  # Prevent recursion
        )
        print(fallback_name)
        return fallback_name

    if cache is not None:
        cache[raw] = best_driver_id

    if best_score < 70 and unmatched:
        unmatched.add(raw_name)

    return best_driver_id

def prepare_driver_match_candidates(year_df: pd.DataFrame) -> dict:
    """
    Prepares normalized candidate lists for fuzzy matching.
    """
    candidates = year_df[['driver_id', 'full_name', 'last_name', 'joined_name', 'abbrev_name']].dropna().reset_index(drop=True)
    return {
        'driver_id': candidates['driver_id'].astype(str).tolist(),
        'full_name': candidates['full_name'].str.lower().tolist(),
        'last_name': candidates['last_name'].str.lower().tolist(),
        'abbrev_name': candidates['abbrev_name'].str.lower().tolist(),
        'joined_name': candidates['joined_name'].str.lower().tolist(),
        'id_map': candidates['driver_id'].tolist()  # Keep for reference if needed
    }

def update_driver_ids(
    df: pd.DataFrame,
    joined_driver_df: pd.DataFrame,
    global_driver_df: pd.DataFrame, # fallback dataframe
    cache: Optional[dict] = None
) -> tuple[pd.DataFrame, set]:
    """
    Updates the driver_id field in df by fuzzy matching driver_name_raw to season driver data per year.
    """
    unmatched = set()
    match_rows = []

    for year, group in df.groupby('year'):
        year_df = joined_driver_df[joined_driver_df['year'] == year]
        match_candidates = prepare_driver_match_candidates(year_df)

        # print(year, group, match_candidates)

        for raw_name in group['driver_name_raw'].unique():
            matched_id = match_driver_name(
                raw_name,
                match_candidates,
                unmatched=unmatched,
                cache=cache,
                fallback_candidates=global_driver_df
            )
            match_rows.append({
                'year': year,
                'driver_name_raw': raw_name,
                'matched_driver_id': matched_id
            })

    match_df = pd.DataFrame(match_rows)
    df = df.merge(match_df, on=['year', 'driver_name_raw'], how='left')
    df['driver_id'] = df['matched_driver_id']
    df.drop(columns=['matched_driver_id'], inplace=True)

    return df, unmatched
            
def prepare_entrant_match_candidates(year_df: pd.DataFrame) -> dict:
    '''
    prepare list of entry candidates for fuzzy matching
    '''
    candidates = year_df[['entrant_id', 'constructor_id', 'engine_manufacturer_id']].dropna().reset_index(drop=True)
    # print(candidates)

    return {
        'entrant_id': candidates['entrant_id'].astype(str).tolist(),
        'constructor_id': candidates['constructor_id'].astype(str).tolist(),
        'engine_manufacturer_id': candidates['engine_manufacturer_id'].astype(str).tolist(),
        'search_pool': candidates['entrant_id'].str.replace('-', ' ').str.lower().tolist()  # Use entrant_id as main match target
    }

def match_entrant(
    raw_entrant: str,
    candidates: dict,
    unmatched: Optional[set] = None,
    cache: Optional[dict] = None
) -> dict:
    """
    Match raw entrant name to the best entrant_id from the candidate pool.
    Returns a dict with entrant_id, constructor_id, and engine_manufacturer_id.
    """
    if pd.isna(raw_entrant) or not isinstance(raw_entrant, str):
        if unmatched:
            unmatched.add(raw_entrant)
        return {'entrant_id': None, 'constructor_id': None, 'engine_manufacturer_id': None}

    raw = raw_entrant.strip().lower()

    if cache and raw in cache:
        return cache[raw]

    # Match against entrant_id list
    entrant_choices = candidates['search_pool']
    best_entrant_str, entrant_score, entrant_idx = process.extractOne(raw, entrant_choices, scorer=fuzz.token_sort_ratio)
    # print(f'Raw string: {raw}, \nBest match: {best_entrant_str}, {entrant_score}')

    constructor_choices = [c.replace('-', ' ') for c in candidates['constructor_id']]
    best_constructor_str, constructor_score, constructor_idx = process.extractOne(raw, constructor_choices, scorer=fuzz.token_sort_ratio)
    # print(f'Raw string: {raw}, \nBest match: {best_constructor_str}, {constructor_score}')

    # Use better score
    if constructor_score > entrant_score:
        best_str = best_constructor_str
        idx = constructor_idx
        score = constructor_score
    else:
        best_str = best_entrant_str
        idx = entrant_idx
        score = entrant_score

    if score < 50:
        print('No Match')
        if unmatched:
            unmatched.add(raw_entrant)
        return {'entrant_id': None, 'constructor_id': None, 'engine_manufacturer_id': None}
    
    # print(best_str)

    matched = {
        'entrant_id': candidates['entrant_id'][idx],
        'constructor_id': candidates['constructor_id'][idx],
        'engine_manufacturer_id': candidates['engine_manufacturer_id'][idx]
    }

    if cache is not None:
        cache[raw] = matched

    # print('Match: ', matched)

    return matched

def update_entrant_fields(
    df: pd.DataFrame,
    entrant_df: pd.DataFrame,
    cache: Optional[dict] = None
) -> tuple[pd.DataFrame, set]:
    unmatched = set()
    match_rows = []

    for year, group in df.groupby('year'):
        year_candidates = entrant_df[entrant_df['year'] == year]
        match_candidates = prepare_entrant_match_candidates(year_candidates)

        for raw in group['entrant_raw'].unique():
            match_result = match_entrant(
                raw,
                match_candidates,
                unmatched=unmatched,
                cache=cache
            )
            match_rows.append({
                'year': year,
                'entrant_raw': raw,
                **match_result
            })

    match_df = pd.DataFrame(match_rows)

    df = df.merge(match_df, on=['year', 'entrant_raw'], how='left')

    return df, unmatched

