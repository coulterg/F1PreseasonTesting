import re
import os
import pandas as pd

from thefuzz import fuzz, process
from collections import defaultdict

# ~~~~ Defined Constants ~~~~~ #
from parse.constants import months, nationalities

# ~~~~ Instantiated OCR models ~~~~~ #
from parse.ocr_utils import ocr_standard, ocr_table, load_image, preprocess_image

# ~~~~ Metadata extraction ~~~~ #

def parse_filename(fname):
    '''Extract strings for year, session, and day, encoded in the file name in that order'''
    base = os.path.splitext(os.path.basename(fname))[0]
    parts = re.split(r"[_-]", base)
    year, session, day = parts[0], parts[1] if len(parts)>1 else '', parts[2] if len(parts)>2 else ''
    return year, session, day

def extract_text(img_crop, ocr_engine):
    '''Extract OCR text from image using defined ocr_engine instance'''

    result = ocr_engine.ocr(img_crop)
    return [entry[1][0] for entry in result[0]]

def extract_date(date_lines):
    '''Return Date string e.g. '12 March 2014' from OCR text input
    Uses fuzzy matching here to fix OCR error months'''

    if not date_lines:
        return None
    
    tokens = date_lines[0].strip().split()

    if len(tokens) >= 4 and tokens[-3].isdigit(): # date line usually long, with date at end

        if tokens[-2] not in months: # Slight OCR error - fuzzy match to fix
            month = process.extract(tokens[-2], months, limit=1)[0][0]
            return tokens[-3]+' '+month+' '+tokens[-1]
        
        else:
            return " ".join(tokens[-3:])
        
    return None

def extract_circuit(title_lines):
    '''Extract Circuit string from title img ocr result text.
    Circuit typically all caps and the only token that doesn't contain a digit
    Also large text, OCR typically good here'''

    if not title_lines:
        return None
    
    parts = [p.strip() for p in title_lines[0].split('-')]

    for part in parts:

        if not re.search(r'\d', part): # Only the circuit should be digit free
            return part[0].upper()+part[1:].lower()
        
    return None

# ~~~~ Table OCR Processing ~~~~ #

def ocr_results_to_rows(ocr_result, y_tolerance=10):
    """
    Group OCR output into rows by Y position.
    Returns a list of lists of strings (one list per row).
    """
    # box_list, text_list, _ = ocr_result[0]
    box_list = [entry[0] for entry in ocr_result[0]]
    text_list = [entry[1] for entry in ocr_result[0]]

    assert len(box_list) == len(text_list), "Mismatch between boxes and texts"

    rows = defaultdict(list)

    for box, (text, conf) in zip(box_list, text_list):
        if not text.strip():
            continue  # skip empty or whitespace-only entries

        y_center = sum(pt[1] for pt in box) / 4.0

        # Assign to existing row if within Y tolerance
        for key in rows:
            if abs(key - y_center) < y_tolerance:
                rows[key].append((box, text))
                break
        else:
            rows[y_center] = [(box, text)]  # new row group

    # Sort rows (top to bottom), then sort entries within each row (left to right)
    sorted_rows = []
    for key in sorted(rows):
        row = sorted(rows[key], key=lambda x: x[0][0][0])  # sort by x-position
        sorted_rows.append([text for _, text in row])

    return sorted_rows

def parse_ocr_to_dataframe(ocr_result):
    """
    Convert OCR output into a structured pandas DataFrame,
    handling optional CL and PL columns and skipping post-table notes.
    """
    rows = ocr_results_to_rows(ocr_result)
    if not rows or len(rows) < 2:
        return pd.DataFrame()

    header_row = ' '.join(rows[0]).split()
    
    # Some sheets have these, others not
    
    has_cl = 'CL' in header_row
    has_pl = 'PL' in header_row or 'PIC' in header_row

    parsed_rows = []
    bad_rows = []

    for row in rows[1:]:
        # Skip rows that are not data - usually infringements
        joined = ' '.join(row)
        if joined.strip().startswith('CAR') or not any(char.isdigit() for char in joined):
            continue

        tokens = joined.split()
        if len(tokens) < 6:
            continue  # probably junk
            
        # Skip rows with "PIRELLI", "Previous Car", "Penalty", etc.
        if any(keyword in joined.upper() for keyword in ['PIRELLI', 'PREVIOUS', 'PENALTY']):
            continue

        try:
            start = 0
            pos = tokens[start]
            start += 1

            if len(tokens[start]) <= 2 and tokens[start].isdigit():
                no = tokens[start]
                start += 1
            else: # The POS and NO may have been put together - this will extract if so
                no_match = re.search(r'\d{1,2}$', pos)
                no = no_match.group() if no_match else ''
                pos = pos[:-len(no)] if no else pos

            if has_cl and (tokens[start] == 'F1' or tokens[start] == ''):
                start += 1
            if has_pl and tokens[start].isdigit():
                start += 1

            name_tokens = []
                        
            # Crawl through name until we find a known nationality code (even if OCR-mangled)
            while start < len(tokens):
                token = re.sub(r'[^A-Za-z]', '', tokens[start])  # remove dots/punctuation
                token_upper = token.upper()
                if token_upper in nationalities:
                    nat = token_upper
                    break
                name_tokens.append(tokens[start])
                start += 1
            else:
                # fallback in case nothing matched
                nat = ''
                
            name = ' '.join(name_tokens)
            name = re.sub(r'[^\w\s]', '', name)
            name = name.title()
                
            start += 1

            entry_tokens = []
            while start < len(tokens) and not re.match(r'\d+:\d{2}\.\d{3}', tokens[start]):
                entry_tokens.append(tokens[start])
                start += 1
            entry = ' '.join(entry_tokens)
            entry = re.sub(r'[^\w\s]', '', entry)
            entry = entry.title()

            lap_time = tokens[start]
            start += 1

            # ON and LAPS are usually the next two integers after TIME
            on, laps = None, None
            ints_after_time = [tok for tok in tokens[start:] if tok.isdigit()]

            if len(ints_after_time) >= 2:
                on, laps = ints_after_time[0], ints_after_time[1]
            elif len(ints_after_time) == 1:
                laps = ints_after_time[0]

            parsed_rows.append({
                'POS': pos,
                'NO': no,
                'NAME': name,
                'NAT': nat,
                'ENTRY': entry,
                'TIME': lap_time,
                'LAPS': laps,
                'ON': on
            })

        except Exception as e:
            print(f"Row skipped due to error: {e}\n{row}")
            bad_rows.append({
                    'error': str(e),
                    'raw_row': ' '.join(row)
                })
            continue

    return pd.DataFrame(parsed_rows), bad_rows

# ~~~~ Returning Final DataFrame ~~~~ #

def process_image_to_dataframe(image_path, ocr_engine = ocr_standard, table_ocr_engine=ocr_table):
    """
    Given an image path and cropped regions, performs OCR + parsing + metadata attachment.
    Returns a DataFrame of parsed table rows with metadata columns included.
    """

    # Load full image and crops
    img = load_image(image_path)
    cropped = preprocess_image(img)
    table_image = cropped['table_img']
    date_image = cropped['date_img']
    title_image = cropped['title_img']

    # Perform OCR
    table_ocr = table_ocr_engine.ocr(table_image)
    date_lines = extract_text(date_image, ocr_engine)
    title_lines = extract_text(title_image, ocr_engine)

    # Extract metadata
    date_str = extract_date(date_lines)
    circuit_str = extract_circuit(title_lines)
    year, session, day = parse_filename(image_path)

    df, bad_rows = parse_ocr_to_dataframe(table_ocr)

    filename = os.path.basename(image_path)

    # Attach filename to each bad row
    for row in bad_rows:
        row['FILENAME'] = filename

    # Attach metadata to parsed rows
    metadata = {
        'DATE': date_str,
        'CIRCUIT': circuit_str,
        'YEAR': year,
        'SESSION': session,
        'DAY': day,
        'FILENAME': filename
    }

    for key, value in metadata.items():
        df[key] = value

    return df, bad_rows