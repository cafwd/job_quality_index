# CAFWD Job Quality Index

The full documentation can be found [here](https://docs.google.com/document/d/1YGyLF0LoafMH-IuZ94a7Bw1o3q0IpqfXUlEY1c62RrU/edit).

## Data Sources

### EDD

The Employment Development Department releases its Current Employment Statistics each month, which can be found [here](https://data.edd.ca.gov/Industry-Information-/Current-Employment-Statistics-CES-/r4zm-kdcg).


### IPUMS

IPUMS is our source for census and American Community Survey (ACS) data. Each year's data must be downloaded, which can be done [here](https://usa.ipums.org/usa/).

The following fields should be selected when creating a dataset:

- COUNTYFIP
- HISPAN
- INCWAGE
- INDNAICS
- PERWT
- RACE
- STATEFIP
- YEAR

**Data File Location**

Due to the size of the IPUMS datasets, they cannot be stored in the repository and must be in the correct file location when generating high wage outputs. Begin by cloning and pulling the repository, so all other file locations are in place. Then, add any year of IPUMS data to the data folder with the following location and naming convention:

Location: `data/ipums`

Naming Convention: `IPUMS_{YEAR}.csv`

Example: `data/ipums/IPUMS_2020`

### County to Region Information

This is a translational spreadsheet to show how California has been divided by county into the Community Economic Resiliency Fund (CERF) regions. This spreadsheet can be found in this repository, under:

`data/county_to_regions_key.csv`.

### Cost of Living

The Real Cost Measure from United Ways of California serves as the threshold for what is considered a "high wage" in the Job Quality Index. Specifically, we are using the cost of living to support 1 adult, 1 preschooler, and 1 school-aged child in a given county. The Real Cost Measure dashboard can be found [here](https://public.tableau.com/app/profile/hgascon/viz/TheRealCostMeasureinCalifornia2021/RealCostDashboard).

To create cost of living thresholds to reflect the CERF regions, weighted averages of county cost of living values based on county populations are used to represent the cost of living in a particular region. The spreadsheet where these calculations live can be found in this repository, under:

`data/cost_of_living/cost-of-living-calculations.xlsx`.

### Crosswalks

Some miscellaneous crosswalks have been developed in-house to connect select industries in the EDD dataset to the industries in the IPUMS dataset. These crosswalks live in this repository, under:

`data/edd/edd_to_ipums_crosswalk.csv`

`data/ipums/ipums_to_edd_crosswalk.csv`

The usage of these crosswalks is documented and incorporated in the JQI Functions Library.

## JQI Functions Library

A library of functions to assist in generating high wage outputs has been created and lives in `jqi_functions.py`. These functions include, but are not limited to:

- `normalize_titles`, `cleaned_ipums`, `cleaned_ipums_demo`
    - Cleans the IPUMS dataframes, merges with respective crosswalks, and normalizes any industry title text included.
    - `cleaned_ipums_demo` is meant to be used in place of `cleaned_ipums` when generating high wage outputs with a racial demographic breakdown included.
- `add_to_state_df`, `add_to_region_df`, `add_geo_high_wages`
    - Engineers the necessary features for computing the high wage percentages for a particular industry at the state and regional levels, then adds these features to the returned dataframe.
- `clean_edd`, `filter_edd`
    - Cleans the EDD dataframes, merges with respective crosswalks, normalizes any industry title text included, and reduces the number of industries included to be a representative subset of industries for each region and the state of California.
- `edd_to_hw`
    - Takes all of the cleaned, filtered, and engineered dataframes and computes the high wage job count for an industry in a specified region and on a specified date.

## Process to Create High Wage Outputs

1. Ensure that EDD and IPUMS data are in the correct data folders (i.e., `data/edd` and `data/ipums`, respectively). 
2. Run `clean-edd-data.ipynb` to generate a cleaned output of a particular year's EDD data. This is only necessary if working with new EDD data that has not been cleaned before.
- To run this notebook, begin by changing the year to the year that is needed.
3. Run `jqi-create-high-wage-outputs.ipynb` to generate high wage outputs for a given year.
- To run this notebook, begin by changing the desired year and the corresponding cost of living year. Cost of living does not get updated as frequently as EDD and IPUMS data, so the cost of living year may be behind the year that outputs are being generated for.
4. To create corresponding outputs with a racial demographics breakdown, run `jqi-race-breakdown-hw-outputs.ipynb` with the necessary year and corresponding cost of living year entered.
5. Code for creating visualizations lives in `high-wage-visualizations.ipynb`.




























