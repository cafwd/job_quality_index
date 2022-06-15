# CAFWD Job Quality Index

The full documentation can be found [here](https://docs.google.com/document/d/1YGyLF0LoafMH-IuZ94a7Bw1o3q0IpqfXUlEY1c62RrU/edit).

## Data Sources

### EDD

The Employment Development Department releases its Current Employment Statistics each month, which can be found [here](https://data.edd.ca.gov/Industry-Information-/Current-Employment-Statistics-CES-/r4zm-kdcg).

To properly create new years of EDD dataframes, make sure that the Current Employment Statistics are stored as `data/edd/Current_EDD_Statistics.csv`.


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

To maintain a consistent methodology across years, only the 2019 data from United Way is used, then this data is adjusted for previous or future years based on inflation rates from [here](https://www.minneapolisfed.org/about-us/monetary-policy/inflation-calculator/consumer-price-index-1913-). Inflation rates from 2010-2022 can be found in this repository, under:

`data/cost_of_living/inflation-rates.csv`

### Crosswalks

Some miscellaneous crosswalks have been developed in-house to connect select industries in the EDD dataset to the industries in the IPUMS dataset. These crosswalks live in this repository, under:

`data/edd/edd_to_ipums_crosswalk.csv`

`data/ipums/ipums_to_edd_crosswalk.csv`

The usage of these crosswalks is documented and incorporated in the JQI Functions Library.

## JQI Functions Library

A library of functions to assist in generating high wage outputs has been created and lives in `jqi_functions.py`. These functions include, but are not limited to:

- `normalize_titles`, `cleaned_ipums`
    - Cleans the IPUMS dataframes, merges with respective crosswalks, and normalizes any industry title text included.
    - Set the `demo` parameter in `cleaned_ipums` to True to include racial demographic information in the IPUMS dataset.
    - **NOTE:** `cleaned_ipums` uses minimum wage data that needs to be updated on an annual basis. Within the function, there is a dictionary that stores the California minimum wage from 2010 onward, and this data can be found [here](https://www.dir.ca.gov/iwc/minimumwagehistory.htm).
- `add_to_state_df`, `add_to_region_df`, `add_geo_high_wages`
    - Engineers the necessary features for computing the high wage percentages for a particular industry at the state and regional levels, then adds these features to the returned dataframe.
- `clean_edd`, `filter_edd`
    - Cleans the EDD dataframes, merges with respective crosswalks, normalizes any industry title text included, and reduces the number of industries included to be a representative subset of industries for each region and the state of California.
- `edd_to_hw`
    - Takes all of the cleaned, filtered, and engineered dataframes and computes the high wage job count for an industry in a specified region and on a specified date.

## Process to Create High Wage Outputs

1. Ensure that EDD and IPUMS data are in the correct data folders (i.e., `data/edd` and `data/ipums`, respectively). 
2. Ensure JQI Functions Library is up to date by:
- Making sure all minimum wage values in `cleaned_ipums` are up to date.
- Confirming that no new NAICS Code to Industry Title crosswalks have been released. This crosswalk has changed twice since 2010, so it's possible that they could change again.
3. Run `clean-edd-data.ipynb` to generate a cleaned output of a particular year's EDD data. This is only necessary if working with new EDD data that has not been cleaned before.
- To run this notebook, begin by changing the year to the year that is needed.
4. Run `generate-cost-of-living.ipynb` to generate a particular year's cost of living data. This is only necessary if this year's cost of living data has not been generated before.
- To run this notebook, begin by changing the year to the year that is needed.
5. Run `jqi-create-high-wage-outputs.ipynb` to generate high wage outputs for a given year.
- To run this notebook, begin by changing the desired year for outputs.
6. To create corresponding outputs with a racial demographics breakdown, run `jqi-race-breakdown-hw-outputs.ipynb` with the necessary year entered. To have racial demographics data included in the IPUMS dataset, change the `demo` parameter in `cleaned_ipums` to True.
7. Code for creating visualizations lives in `high-wage-visualizations.ipynb`.




























