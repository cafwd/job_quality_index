import numpy as np
import pandas as pd
import string
import os
import matplotlib.pyplot as plt

def normalize_titles(col):
    """
    Normalize text to lowercase, remove whitespace, and remove punctuation.
    Needed when working with industry titles in IPUMS or EDD data.
    """
    col = col.astype(str)
    col = col.str.strip()
    col = col.str.lower()
    col = col.str.replace('&', 'and')
    col = col.apply(lambda x:''.join([i for i in x if i not in string.punctuation]))
    return col

def cleaned_ipums(year: str):
    """
    Function to clean IPUMS data for the specified year.
    Currently has hardcoded file paths for naics_parsed_crosswalk and 
    ind_indnaics_crosswalk_2000_onward_without_code_descriptions csv files.
    Assumption of full time employees is anyone with INCWAGE >= minimum wage * 30 hours * 50 weeks
    """
    """
    Minimum wage data found here: https://www.dir.ca.gov/iwc/minimumwagehistory.htm
    """
    cwd = os.getcwd()
    
    if int(year) < 2010:
        print('Invalid year')
        return None
    min_wages = {2010:8, 2011:8, 2012:8, 2013:8, 
                 2014:9, 2015:9, 2016:10, 2017:10, 
                 2018:10.5, 2019:11, 2020:12, 
                 2021:13, 2022:14}
    min_wage = min_wages[int(year)] * 30 * 50
    ipums = pd.read_csv(f'{cwd}/data/ipums/IPUMS_{year}.csv')
    ca_ipums = ipums.loc[ipums['STATEFIP'] == 6].copy()
    ca_ipums = ca_ipums[['YEAR', 'COUNTYFIP', 'INDNAICS','PERWT','INCWAGE']]
    ca_ipums = ca_ipums.loc[ca_ipums['INCWAGE'] >= min_wage].reset_index().iloc[:,1:] # filter by full time employees
    ipums_titles = pd.read_csv(f'{cwd}/data/ipums/ind_indnaics_crosswalk_2000_onward_without_code_descriptions.csv')
    ipums_titles = ipums_titles.iloc[2:]
    ipums_titles = ipums_titles.iloc[:,9:]
    ipums_titles['2018 Onward ACS/PRCS INDNAICS CODE'] = normalize_titles(ipums_titles['2018 Onward ACS/PRCS INDNAICS CODE'])
    ipums_titles['2013-2017 ACS/PRCS INDNAICS CODE'] = normalize_titles(ipums_titles['2013-2017 ACS/PRCS INDNAICS CODE'])
    ca_ipums['INDNAICS'] = normalize_titles(ca_ipums['INDNAICS'])
    if int(year) >= 2018:
        ipums_titles = ipums_titles[['2018 Onward ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2018 Onward ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2018 Onward ACS/PRCS INDNAICS CODE": "NAICS Code"})
    elif 2013 <= int(year) <= 2017:
        ipums_titles = ipums_titles[['2013-2017 ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2013-2017 ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2013-2017 ACS/PRCS INDNAICS CODE": "NAICS Code"})
    else:
        ipums_titles = ipums_titles[['2008-2012 ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2008-2012 ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2008-2012 ACS/PRCS INDNAICS CODE": "NAICS Code"})
    merged_ipums['Industry Title'] = normalize_titles(merged_ipums['Industry Title'])
    ipums_to_edd = pd.read_csv(f'{cwd}/data/ipums/ipums_to_edd_crosswalk.csv')
    merged_ipums = pd.merge(merged_ipums, ipums_to_edd, on='NAICS Code')
    return merged_ipums

def show_null(df):
    """
    Function to print number and percentage of null values per column.
    """
    print(f'''TOTAL ROWS: {len(df)}''')
    for column in df.columns.values:
        total = len(df)
        nulls = df[column].isna().sum()
        percentage = (nulls / total) * 100
        print(f'''{column}: {nulls} null values, {percentage:.2f}%''')
        
def add_to_state_df(df):
    """
    Add high wage threshold and percentage features at the state level.
    """
    df['Above CA Threshold'] = df['INCWAGE'] > df['State COL']
    df['wt_ind_counts'] = df['PERWT'].groupby(df['Crosswalk Value']).transform('sum')
    df["Above CA Threshold"] = df["Above CA Threshold"].astype(int)
    df["wt_CA_above_thresh"] = df["Above CA Threshold"] * df['PERWT']
    df['wt_CA_high_wage_count'] = df['wt_CA_above_thresh'].groupby(
        df['Crosswalk Value']).transform('sum')
    df['wt_CA_high_wage_perc'] = (df['wt_CA_high_wage_count'] / df['wt_ind_counts']) * 100
    df['unwt_ind_counts'] = df['Crosswalk Value'].groupby(df['Crosswalk Value']).transform('count')
    return df

def add_to_region_df(df):
    """
    Add high wage threshold and percentage features at the region level.
    """
    df['above_region_thresh'] = df['INCWAGE'] > df['Regional COL']
    df["above_region_thresh"] = df["above_region_thresh"].astype(int)
    df["wt_reg_above_thresh"] = df["above_region_thresh"] * df['PERWT']
    df_agg = df.groupby(['Crosswalk Value','CERF Regions']).agg(wt_reg_ind_counts = ('PERWT','sum'),
                                                     wt_reg_high_wage_count = ('wt_reg_above_thresh','sum'),
                                                     unwt_reg_ind_counts = ('Crosswalk Value','count')).reset_index() 
    df = pd.merge(df, df_agg, on=['Crosswalk Value', 'CERF Regions'])
    df['wt_reg_high_wage_perc'] = (df['wt_reg_high_wage_count'] / df['wt_reg_ind_counts']) * 100
    df = df.rename(columns={'wt_reg_high_wage_count_x':'wt_reg_high_wage_count','wt_reg_ind_counts_x':'wt_reg_ind_counts',
                           'unwt_reg_ind_counts_x':'unwt_reg_ind_counts'})
    return df

# def add_to_community_df(df):
#     """
#     Add high wage threshold and percentage features at the rural/urban level.
#     """
#     df['above_comm_thresh'] = df['INCWAGE'] > df['Rural/Urban COL']
#     df["above_comm_thresh"] = df["above_comm_thresh"].astype(int)
#     df["wt_comm_above_thresh"] = df["above_comm_thresh"] * df['PERWT'] 
#     df_agg = df.groupby(['Crosswalk Value','Rural/Urban']).agg(wt_comm_ind_counts = ('PERWT','sum'),
#                                                      wt_comm_high_wage_count = ('wt_comm_above_thresh','sum'),
#                                                      unwt_comm_ind_counts = ('Crosswalk Value','count')).reset_index()
#     df = pd.merge(df, df_agg, on=['Crosswalk Value', 'Rural/Urban'])
#     df['wt_comm_high_wage_perc'] = (df['wt_comm_high_wage_count'] / df['wt_comm_ind_counts']) * 100
#     df = df.rename(columns={"Rural/Urban_x": "Rural/Urban", 'wt_comm_high_wage_count_x':'wt_comm_high_wage_count','wt_comm_ind_counts_x':'wt_comm_ind_counts',
#                            'unwt_comm_ind_counts_x':'unwt_comm_ind_counts'})
#     return df

def add_geo_high_wages(df):
    """
    Add all high wage threshold and percentage features at every geographical level 
    (county, region, regional urban/rural, urban/rural, state).
    References past five functions.
    """
    df_new = df.copy() # initialize new dataframe
    df_new = add_to_state_df(df_new) # creating state level counts
#     df_new = add_to_community_df(df_new) # creating rural/urban level counts
    df_new = add_to_region_df(df_new) # creating regional level counts
    return df_new

def edd_to_hw(edd_df, ipums_df_hw, region: str, crosswalk_val: int, date: str, sample_size: int):
    """
    Returns the number of high wage jobs for a given date, region, and EDD industry (based on a predetermined selection).
    
    """
    # filter edd by date, region, and industry via crosswalk value
    edd_df = edd_df.loc[edd_df['Date'] == date].copy()
    edd_df = edd_df.loc[edd_df['Crosswalk Value'] == crosswalk_val].copy()
    edd_df = edd_df.loc[edd_df['CERF Regions'] == region]
    
    # merge naics with edd on crosswalk value
    edd_df = pd.merge(edd_df, ipums_df_hw, on=['Crosswalk Value', 'CERF Regions', 'County', 'Rural/Urban'])
    if len(edd_df) == 0:
        return np.nan, np.nan, np.nan, np.nan
    employment_count = edd_df.groupby('County').mean()['Current Employment'].sum()
        
    # sample size logic
    if edd_df['unwt_reg_ind_counts'].values[0] >= sample_size:
        hw_perc = edd_df['wt_reg_high_wage_perc'].values[0]
#     elif edd_df['unwt_comm_ind_counts'].values[0] >= sample_size:
#         hw_perc = edd_df['wt_comm_high_wage_perc'].values[0]
    elif edd_df['unwt_ind_counts'].values[0] >= sample_size:
        hw_perc = edd_df['wt_CA_high_wage_perc'].values[0]
    else:
        hw_perc = -1
    hw_count = (employment_count * hw_perc) / 100
    industry = edd_df['Industry Title_x'].values[0]
    return hw_count, hw_perc, employment_count, industry

        
def ts_plot(df, title):
    """
    Function to create simple time series plots.
    """
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(df.index, df['High Wage Count'], color='green')
    ax.set_xlabel('Date')
    ax.set_ylabel('High Wage Count')
    ax.set_title(f'{title}', fontsize=14, pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_linewidth(0.5)
    
# construction subcodes: 20236000, 20237000, 20238000 - replaced with general construction code 20000000 for LA and SD
region_series_codes = {'Bay Area':[10000000, 11000000, 15000000, 20000000, 30000000, 
                                   41000000, 42000000, 43000000, 50000000, 
                                   60540000, 60550000, 60560000, 65000000, 
                                   70000000, 80000000, 90910000, 90920000, 90930000],
                       'Central Coast':[10000000, 11000000, 15000000, 20000000, 31000000, 32000000,
                                        41000000, 42000000, 43000000, 55000000, 
                                        60000000, 65000000, 
                                        70000000, 80000000, 90910000, 90920000, 90930000],
                       'Central San Joaquin':[10000000, 11000000, 15000000, 20000000, 
                                         31000000, 32000000, 41000000, 42000000, 43000000, 50000000, 55000000, 
                                         60000000, 65000000, 70000000, 80000000, 90910000, 90920000, 90930000],
                       'Eastern Sierra':[8999999, 10000000, 11000000, 15000000, 20000000, 
                                         31000000, 32000000, 41000000, 42000000, 43000000, 
                                         50000000, 55000000, 60000000, 65000000, 70000000, 
                                         80000000, 90910000, 90920000, 90930000],
                       'Inland Empire':[10000000, 11000000, 20000000, 31000000, 32000000, 
                                        41000000, 42000000, 43000000, 55000000, 
                                        60540000, 60550000, 60560000, 65610000, 65620000, 
                                        70710000, 70720000, 80000000, 90910000, 90920000, 90930000],
                       'Kern':[10000000, 11000000, 15000000, 20000000, 31000000, 32000000, 
                               41000000, 42000000, 43000000, 50000000, 55520000, 55530000, 
                               60540000, 60550000, 60560000, 65610000, 65620000, 70710000, 70720000, 
                               80000000, 90910000, 90920000, 90930000],
                       'Los Angeles':[10000000, 11000000, 15000000, 2000000, 
                                      31000000, 32000000, 41000000, 42000000, 43220000, 43400089, 
                                      50000000, 55000000, 60540000, 60550000, 60560000, 65610000, 65620000, 
                                      70710000, 70720000, 80811000, 80812000, 80813000, 90910000, 90920000, 90930000],
                       'North State':[8999999, 10000000, 11000000, 15000000, 20000000, 
                                      30000000, 41000000, 42000000, 43000000, 50000000, 55000000, 
                                      60000000, 65000000, 70000000, 80000000, 90910000, 90920000, 90930000],
                       'Northern San Joaquin':[10000000, 11000000, 15000000, 20000000, 30000000, 
                                               41000000, 42000000, 43000000, 50000000, 55000000, 
                                               60000000, 65000000, 70000000, 80000000, 90910000, 90920000, 90930000],
                       'Orange':[10000000, 11000000, 20000000, 31000000, 32000000, 
                                 41000000, 42000000, 43220000, 43400089, 50000000, 55520000, 55530000, 
                                 60540000, 60550000, 60560000, 65610000, 65620000, 70710000, 70720000, 
                                 80000000, 90910000, 90920000, 90930000],
                       'Redwood Coast':[10000000, 11000000, 20000000, 31000000, 32000000, 
                                        40000000, 50000000, 55000000, 60000000, 65000000, 
                                        70000000, 80000000, 90910000, 90920000, 90930000],
                       'Sacramento':[10000000, 11000000, 15000000, 20000000, 30000000, 
                                     40000000, 50000000, 55000000, 60000000, 65000000, 
                                     70000000, 80000000, 90910000, 90920000, 90930000],
                       'San Diego-Imperial':[10000000, 11000000, 20000000, 31000000, 32000000, 
                                             41000000, 42000000, 43220000, 43400089, 43493000, 
                                             50000000, 55000000, 60540000, 60550000, 60560000, 65000000, 
                                             70000000, 80000000, 90910000, 90920000, 90930000]
}
    
def filter_edd(edd, region_series_codes):
    """
    Filter EDD data to have only the industries that properly represent the population of each region.
    """
    # separate dataframes
    ba = edd.loc[edd['CERF Regions'] == 'Bay Area']
    cc = edd.loc[edd['CERF Regions'] == 'Central Coast']
    csj = edd.loc[edd['CERF Regions'] == 'Central San Joaquin']
    es = edd.loc[edd['CERF Regions'] == 'Eastern Sierra']
    ie = edd.loc[edd['CERF Regions'] == 'Inland Empire']
    kern = edd.loc[edd['CERF Regions'] == 'Kern']
    la = edd.loc[edd['CERF Regions'] == 'Los Angeles']
    ns = edd.loc[edd['CERF Regions'] == 'North State']
    nsj = edd.loc[edd['CERF Regions'] == 'Northern San Joaquin']
    oc = edd.loc[edd['CERF Regions'] == 'Orange']
    rc = edd.loc[edd['CERF Regions'] == 'Redwood Coast']
    sac = edd.loc[edd['CERF Regions'] == 'Sacramento']
    sd = edd.loc[edd['CERF Regions'] == 'San Diego-Imperial']
    
    # filter out series codes
    ba = ba.loc[ba['Series Code'].isin(region_series_codes['Bay Area'])]
    cc = cc.loc[cc['Series Code'].isin(region_series_codes['Central Coast'])]
    csj = csj.loc[csj['Series Code'].isin(region_series_codes['Central San Joaquin'])]
    es = es.loc[es['Series Code'].isin(region_series_codes['Eastern Sierra'])]
    ie = ie.loc[ie['Series Code'].isin(region_series_codes['Inland Empire'])]
    kern = kern.loc[kern['Series Code'].isin(region_series_codes['Kern'])]
    la = la.loc[la['Series Code'].isin(region_series_codes['Los Angeles'])]
    ns = ns.loc[ns['Series Code'].isin(region_series_codes['North State'])]
    nsj = nsj.loc[nsj['Series Code'].isin(region_series_codes['Northern San Joaquin'])]
    oc = oc.loc[oc['Series Code'].isin(region_series_codes['Orange'])]
    rc = rc.loc[rc['Series Code'].isin(region_series_codes['Redwood Coast'])]
    sac = sac.loc[sac['Series Code'].isin(region_series_codes['Sacramento'])]
    sd = sd.loc[sd['Series Code'].isin(region_series_codes['San Diego-Imperial'])]
    
    dfs = [ba, cc, csj, es, ie, kern, la, ns, nsj, oc, rc, sac, sd]
    final_edd = pd.concat(dfs)
    
    return final_edd
    
def clean_edd(edd, edd_titles_crosswalk, edd_to_ipums_crosswalk, county_info):
    """
    Function to clean EDD data.
    edd = pd.read_csv('data/edd/current_edd_1121.csv')
    county_info = pd.read_csv('data/county_to_regions_key.csv')
    edd_crosswalk = pd.read_csv('data/edd/Industry_Title_Crosswalk.csv')
    edd_to_ipums_crosswalk = pd.read_csv('data/edd/edd_to_ipums_crosswalk.csv')
    """
    edd['Area Name'] = edd['Area Name'].str.replace(' County', '')
    edd = edd.loc[edd['Area Type'] == 'County']
    edd = edd.loc[edd['Year'] >= 2014]
    edd = pd.merge(edd, edd_titles_crosswalk, on='Series Code')
    edd = edd.drop(columns=['Industry Title', 'EDD Industry Title'])
    edd = edd.rename(columns={'LMID Industry Title':'Industry Title'})
    edd['Industry Title'] = normalize_titles(edd['Industry Title'])
    edd = pd.merge(edd, county_info, left_on='Area Name', right_on='County')
    edd = edd.loc[edd['Seasonally Adjusted'] == 'N']
    edd = pd.merge(edd, edd_to_ipums_crosswalk, on='Series Code')
    edd = edd[['Area Type', 'Area Name', 'Year', 'Month', 'Date', 'Series Code',
       'Seasonally Adjusted', 'Current Employment', 'Industry Title',
       'COUNTYFIP', 'County', 'Rural/Urban', 'CERF Regions', 'Crosswalk Value']]
    return edd

def cleaned_ipums_demo(year: str):
    """
    Function to clean IPUMS data specifically for a race/demographics breakdown for the specified year.
    Currently has hardcoded file paths for naics_parsed_crosswalk and 
    ind_indnaics_crosswalk_2000_onward_without_code_descriptions csv files.
    Assumption of full time employees is anyone with INCWAGE >= minimum wage * 30 hours * 50 weeks
    """
    """
    Minimum wage data found here: https://www.dir.ca.gov/iwc/minimumwagehistory.htm
    """
    cwd = os.getcwd()
    
    if int(year) < 2014:
        print('Invalid year')
        return None
    min_wages = {2010:8, 2011:8, 2012:8, 2013:8, 
                 2014:9, 2015:9, 2016:10, 2017:10, 
                 2018:10.5, 2019:11, 2020:12, 
                 2021:13, 2022:14}
    min_wage = min_wages[int(year)] * 30 * 50
    ipums = pd.read_csv(f'{cwd}/data/ipums/IPUMS_{year}.csv')
    ca_ipums = ipums.loc[ipums['STATEFIP'] == 6].copy()
    ca_ipums = ca_ipums[['YEAR', 'COUNTYFIP', 'INDNAICS','PERWT','RACE','HISPAN','INCWAGE']]
    ca_ipums = ca_ipums.loc[ca_ipums['INCWAGE'] >= min_wage].reset_index().iloc[:,1:] # filter by full time employees
    ipums_titles = pd.read_csv(f'{cwd}/data/ipums/ind_indnaics_crosswalk_2000_onward_without_code_descriptions.csv')
    ipums_titles = ipums_titles.iloc[2:]
    ipums_titles = ipums_titles.iloc[:,9:]
    ipums_titles['2018 Onward ACS/PRCS INDNAICS CODE'] = normalize_titles(ipums_titles['2018 Onward ACS/PRCS INDNAICS CODE'])
    ipums_titles['2013-2017 ACS/PRCS INDNAICS CODE'] = normalize_titles(ipums_titles['2013-2017 ACS/PRCS INDNAICS CODE'])
    ca_ipums['INDNAICS'] = normalize_titles(ca_ipums['INDNAICS'])
    if int(year) >= 2018:
        ipums_titles = ipums_titles[['2018 Onward ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2018 Onward ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2018 Onward ACS/PRCS INDNAICS CODE": "NAICS Code"})
    elif 2013 <= int(year) <= 2017:
        ipums_titles = ipums_titles[['2013-2017 ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2013-2017 ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2013-2017 ACS/PRCS INDNAICS CODE": "NAICS Code"})
    else:
        ipums_titles = ipums_titles[['2008-2012 ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2008-2012 ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2008-2012 ACS/PRCS INDNAICS CODE": "NAICS Code"})
    merged_ipums['Industry Title'] = normalize_titles(merged_ipums['Industry Title'])
    ipums_to_edd = pd.read_csv(f'{cwd}/data/ipums/ipums_to_edd_crosswalk.csv')
    merged_ipums = pd.merge(merged_ipums, ipums_to_edd, on='NAICS Code')
    return merged_ipums