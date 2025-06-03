# F1PreseasonTesting
Parsing F1 pre-season testing timing sheets with OCR, as this data is not available collectively. 

From the 2019 Season, pre- and mid-season testing classification has been available online through single article pages on either the official [F1 website](https://www.formula1.com/en/latest/article/f1-pre-season-testing-vettel-heads-sainz-at-the-end-of-day-1.2JJU5sSZJ2MC4w0HzkYVhK), or other [enthusiast-maintained sites](https://f1.fandom.com/wiki/2019_Barcelona_Test_1). Prior to these years, however, it appears that [TSL-Timing](https://www.tsl-timing.com/event/191489) was responsible for timing data of testing sessions. 

Unfortunately the data is only available as .gif images of the timing sheets, and are no longer directly naviagable through their website. However, the timing sheets remain online, or at least accessible through the WayBack machine. 

This project aims to collate all available F1 pre-season testing data in one place, in a format compatible with [F1DB](https://github.com/f1db/f1db/tree/main), for analyses, visualisations etc. While recent seasons were largely parsed by hand, the bulk of this project entails optical character recognition (OCR) of the timing sheet images.

**NB Current results (Outputs/parsed_results.csv) are incorrect due to OCR innacuracy but will be updated** 

## To Do
- Complete all available timing sheet OCR (currently only 2010-2018 seasons completed)
- Fuzzy match Drivers, Entrant teams, and circuit names in order to be compatible with [F1DB](https://github.com/f1db/f1db/tree/main).
- Add outline/description of OCR process.
