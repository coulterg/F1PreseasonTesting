# F1 Preseason Testing Parser

This project extracts, standardizes, and compiles Formula 1 pre-season testing data from 2008–2025 using a combination of OCR, fuzzy matching, and manual validation. The final dataset is compatible with the [F1DB](https://github.com/f1db/f1db/tree/main) schema and can be used for performance analysis, visualization, or statistical modeling.

---

## Motivation

While F1 race data is well-structured and publicly available, **pre-season and mid-season testing classifications are scattered, inconsistent, or completely unstructured** — especially prior to 2019.

- **2008–2018**: Testing times were published by [TSL Timing](https://www.tsl-timing.com/event/191489) as `.gif` images of timing sheets — often only accessible/navigable via the [Wayback Machine](https://web.archive.org/)
- **2019–2025**: Data is available online in text format, via either the official [F1 website](https://www.formula1.com/en/latest/article/f1-pre-season-testing-vettel-heads-sainz-at-the-end-of-day-1.2JJU5sSZJ2MC4w0HzkYVhK) or other [enthusiast-maintained sites](https://f1.fandom.com/wiki/2019_Barcelona_Test_1) but not in machine-readable form or consistent schema

---

## Project Goals

-  Extract raw timing data from `.gif` timesheets using OCR (PaddleOCR)
-  Clean and standardize the data (e.g. convert lap times, resolve circuits, names, teams)
-  Fuzzy match drivers, entrants, and circuits to canonical entries in F1DB
-  Extend F1DB to include:
  - Test-only drivers
  - Season entrants not currently listed
  - Structured testing results from 2008 onward

---

## Current Status

- OCR + processing completed for: **2008–2025**
- All results are now:
  - Aligned with F1DB driver/team IDs
  - Include `lap_time`, `lap_time_millis`, `circuit_id`, and `test_type`
  - Normalized and ready for export or use in analysis
- Output is available in:  
  `output/testing_results.csv`

---

## Dataset Structure

The standardized dataset contains the following fields:

| Column                  | Description |
|-------------------------|-------------|
| `year`, `test`, `day`   | Session grouping |
| `date`, `test_type`     | Calendar info |
| `circuit_id`            | Matched to F1DB circuit |
| `position_*`            | Classification result |
| `driver_id`             | F1DB-compatible slug |
| `entrant_id`, `constructor_id`, `engine_manufacturer_id` | F1DB compatible |
| `lap_time`, `lap_time_millis` | Raw + numeric lap time |
| `laps`, `lap_number_fastest` | Laps driven, and fastest lap number |

---

## Contributions Back to F1DB

This project also generates **update proposals for the F1DB project**, including:

- `driver_updates.csv` — missing test-only drivers
- `season_entrant_driver_updates.csv` — test-only entrants by year
- `testing_results.csv` — full classification results in F1DB schema

See the [`f1db_updates/`](./f1db_updates/) folder for prepared CSVs.

---

## OCR Pipeline (to be documented)

The OCR pipeline uses:

- **PaddleOCR** for optical character recognition
- Image preprocessing (upscaling, sharpening)
- Table region cropping and line segmentation
- Post-processing and confidence scoring
- Manual fallback handling and fuzzy matching using `rapidfuzz`

(Coming soon: full walkthrough in `ocr_pipeline.md`)

---

## To Do

- [x] Fuzzy match all drivers, teams, circuits to F1DB
- [x] Clean + validate all test result records (2008–2025)
- [ ] Add description of OCR process and data cleaning
- [ ] Submit PR or open issue with updates for F1DB

---

## Contact / Contributions

If you’re interested in:
- Using this dataset
- Helping validate entries
- Contributing testing results from missing years

...feel free to open an issue or PR, or reach out directly!

