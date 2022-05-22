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
    cwd = os.getcwd()
    
    if int(year) < 2014:
        print('Invalid year')
        return None
    min_wages = {2014:9, 2015:9, 2016:10, 2017:10, 2018:10.5, 2019:11, 2020:12}
    min_wage = min_wages[int(year)] * 30 * 50
    ipums = pd.read_csv(f'{cwd}/data/ipums/IPUMS_{year}.csv')
    ipums = ipums[['YEAR','STATEFIP', 'COUNTYFIP', 'INDNAICS','PERWT','INCWAGE', 'OCCSOC']]
    ca_ipums = ipums.loc[ipums['STATEFIP'] == 6].copy()
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
    else:
        ipums_titles = ipums_titles[['2013-2017 ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2013-2017 ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2013-2017 ACS/PRCS INDNAICS CODE": "NAICS Code"})
#     naics_parsed_crosswalk = pd.read_csv(f'{cwd}/data/ipums/naics_parsed_crosswalk.csv').drop_duplicates(subset='INDNAICS').reset_index().iloc[:,1:]
#     merged_ipums = pd.merge(merged_ipums, naics_parsed_crosswalk, on='INDNAICS')
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
    df['Above CA Threshold'] = df['INCWAGE'] > 74448
    df['wt_ind_counts'] = df['PERWT'].groupby(df['INDNAICS']).transform('sum')
    df["Above CA Threshold"] = df["Above CA Threshold"].astype(int)
    df["wt_CA_above_thresh"] = df["Above CA Threshold"] * df['PERWT']
    df['wt_CA_high_wage_count'] = df['wt_CA_above_thresh'].groupby(
        df['INDNAICS']).transform('sum')
    df['wt_CA_high_wage_perc'] = (df['wt_CA_high_wage_count'] / df['wt_ind_counts']) * 100
    df['unwt_ind_counts'] = df['INDNAICS'].groupby(df['INDNAICS']).transform('count')
    return df

def add_to_county_df(df):
    """
    Add high wage threshold and percentage features at the county level.
    """
    df['above_county_thresh'] = df['INCWAGE'] > df['County COL']
    df["above_county_thresh"] = df["above_county_thresh"].astype(int)
    df["wt_county_above_thresh"] = df["above_county_thresh"] * df['PERWT']
    df_agg = df.groupby(['INDNAICS','County']).agg(wt_county_ind_counts = ('PERWT','sum'),
                                                     wt_county_hw_count = ('wt_county_above_thresh','sum'),
                                                     unwt_county_ind_counts = ('INDNAICS','count')).reset_index()    
    
    df = pd.merge(df, df_agg, on=['INDNAICS', 'County'])
    df['wt_county_hw_perc'] = (df['wt_county_hw_count'] / df['wt_county_ind_counts']) * 100
    df = df.rename(columns={"County_x": "County", 'wt_county_hw_count_x':'wt_county_hw_count','wt_county_ind_counts_x':'wt_county_ind_counts',
                           'unwt_county_ind_counts_x':'unwt_county_ind_counts'})
    return df

def add_to_region_df(df):
    """
    Add high wage threshold and percentage features at the region level.
    """
    df['above_region_thresh'] = df['INCWAGE'] > df['Regional COL']
    df["above_region_thresh"] = df["above_region_thresh"].astype(int)
    df["wt_reg_above_thresh"] = df["above_region_thresh"] * df['PERWT']
    df_agg = df.groupby(['INDNAICS','CDI Regions']).agg(wt_reg_ind_counts = ('PERWT','sum'),
                                                     wt_reg_high_wage_count = ('wt_reg_above_thresh','sum'),
                                                     unwt_reg_ind_counts = ('INDNAICS','count')).reset_index()    
    
    df = pd.merge(df, df_agg, on=['INDNAICS', 'CDI Regions'])
    df['wt_reg_high_wage_perc'] = (df['wt_reg_high_wage_count'] / df['wt_reg_ind_counts']) * 100
    df = df.rename(columns={"CDI Regions_x": "CDI Regions", 'wt_reg_high_wage_count_x':'wt_reg_high_wage_count','wt_reg_ind_counts_x':'wt_reg_ind_counts',
                           'unwt_reg_ind_counts_x':'unwt_reg_ind_counts'})
    return df

def add_to_regioncomm_df(df):
    """
    Add high wage threshold and percentage features at the regional urban/rural level.
    """
    df['above_regcomm_thresh'] = df['INCWAGE'] > df['Regional Rural/Urban COL']
    df["above_regcomm_thresh"] = df["above_regcomm_thresh"].astype(int)
    df["wt_regcomm_above_thresh"] = df["above_regcomm_thresh"] * df['PERWT']
    df_agg = df.groupby(['INDNAICS','Regional Rural/Urban']).agg(wt_regcomm_ind_counts = ('PERWT','sum'),
                                                     wt_regcomm_hw_count = ('wt_regcomm_above_thresh','sum'),
                                                     unwt_regcomm_ind_counts = ('INDNAICS','count')).reset_index()    
    
    df = pd.merge(df, df_agg, on=['INDNAICS', 'Regional Rural/Urban'])
    df['wt_regcomm_hw_perc'] = (df['wt_regcomm_hw_count'] / df['wt_regcomm_ind_counts']) * 100
    df = df.rename(columns={"Regional Rural/Urban_x": "Regional Rural/Urban", 'wt_regcomm_hw_count_x':'wt_regcomm_hw_count','wt_regcomm_ind_counts_x':'wt_regcomm_ind_counts',
                           'unwt_regcomm_ind_counts_x':'unwt_regcomm_ind_counts'})
    return df

def add_to_community_df(df):
    """
    Add high wage threshold and percentage features at the rural/urban level.
    """
    df['above_comm_thresh'] = df['INCWAGE'] > df['Rural/Urban COL']
    df["above_comm_thresh"] = df["above_comm_thresh"].astype(int)
    df["wt_comm_above_thresh"] = df["above_comm_thresh"] * df['PERWT']
    df_agg = df.groupby(['INDNAICS','Rural/Urban']).agg(wt_comm_ind_counts = ('PERWT','sum'),
                                                     wt_comm_high_wage_count = ('wt_comm_above_thresh','sum'),
                                                     unwt_comm_ind_counts = ('INDNAICS','count')).reset_index()    
    
    df = pd.merge(df, df_agg, on=['INDNAICS', 'Rural/Urban'])
    df['wt_comm_high_wage_perc'] = (df['wt_comm_high_wage_count'] / df['wt_comm_ind_counts']) * 100
    df = df.rename(columns={"Rural/Urban_x": "Rural/Urban", 'wt_comm_high_wage_count_x':'wt_comm_high_wage_count','wt_comm_ind_counts_x':'wt_comm_ind_counts',
                           'unwt_comm_ind_counts_x':'unwt_comm_ind_counts'})
    return df

def add_geo_high_wages(df):
    """
    Add all high wage threshold and percentage features at every geographical level 
    (county, region, regional urban/rural, urban/rural, state).
    References past five functions.
    """
    df_new = df.copy() # initialize new dataframe
    df_new = add_to_state_df(df_new) # creating state level counts
    df_new = add_to_community_df(df_new) # creating rural/urban level counts
    df_new = add_to_region_df(df_new) # creating regional level counts
    df_new = add_to_regioncomm_df(df_new) # creating regional rural/urban level counts
    df_new = add_to_county_df(df_new) # creating county level counts
    return df_new

    
def edd_to_hw(edd_df, ipums_df_hw, naics_df, county_df, county: str, parsed_code: str, date: str, sample_size: int):
    """
    Returns the number of high wage jobs for a given date, county, and industry.
    Merges on the parsed code system at the most granular level possible.
    
    """
    # filter edd by date, edd county, and industry via parsed code
    edd_df = edd_df.loc[edd_df['Date'] == date].copy()
    if len(edd_df) == 0:
        return "Date not valid or found", np.nan, np.nan, np.nan
    edd_df = edd_df.loc[(edd_df['Sub_4_Code'] == parsed_code) | 
                        (edd_df['Sub_3_Code'] == parsed_code) | 
                        (edd_df['Sub_2_Code'] == parsed_code) | 
                        (edd_df['Sub_1_Code'] == parsed_code) | 
                        (edd_df['Main_Code'] == parsed_code)].copy()
    edd_df = edd_df.loc[edd_df['Area Name'] == county] 
    edd_df = edd_df.drop_duplicates(subset='Main_EDD').reset_index().iloc[:,1:]
    
    # merge naics with edd
    edd_df_ = pd.merge(edd_df, naics_df, on='Sub_4_Code')
    if len(edd_df_) == 0:
        edd_df_ = pd.merge(edd_df, naics_df, on='Sub_3_Code')
        if len(edd_df_) == 0:
            edd_df_ = pd.merge(edd_df, naics_df, on='Sub_2_Code')
            if len(edd_df_) == 0:
                edd_df_ = pd.merge(edd_df, naics_df, on='Sub_1_Code')
                if len(edd_df_) == 0:
                    edd_df_ = pd.merge(edd_df, naics_df, on='Main_Code')
                    if len(edd_df_) == 0:
                        return "No parsed code of input industry found within input county", np.nan, np.nan, np.nan
    edd_df = edd_df_.rename(columns = {'Industry Title_x':'EDD Industry',
                                 'Industry Title_y': 'IPUMS Industry'})
    edd_df = edd_df[['EDD Industry', 'Area Name', 'IPUMS Industry', 'INDNAICS', 'Current Employment']]
    employment_count = int(edd_df['Current Employment'].values[0])
    naics_code = edd_df['INDNAICS'].values[0]
    output, hw_perc, industry = ca_ipums_filter(ipums_df_hw, county_df, county, naics_code, sample_size)
    hw_count = (employment_count * hw_perc) / 100
    output += f", High wage count: {hw_count}"
    return output, hw_count, industry, employment_count

def ca_ipums_filter(df, county_df, region: str, NAICS: str, n: int):
    """
    Returns the high wage percentage to be used in the edd_to_hw function.
    Substitutes specified county with higher geographical levels if there isn't a large enough sample size.
    """
    df = df.loc[df['County'] == county].copy() # change to exclude counties
    level = 'county'
    if len(df) == 0:
        county_df = county_df.loc[county_df['County'] == county].copy() # narrow down county df
        reg_rural_urban = county_df['Regional Rural/Urban'].values[0]
        region = county_df['CDI Regions'].values[0]
        rural_urban = county_df['Rural/Urban'].values[0]
        df = df.loc[df['Regional Rural/Urban'] == reg_rural_urban].copy()
        level = 'reg_rural_urban'
        if len(df) == 0:
            df = df.loc[df['CDI Regions'] == region].copy()
            level = 'region'
            if len(df) == 0:
                df = df.loc[df['Rural/Urban'] == rural_urban].copy()
                level = 'rural_urban'
                if len(df) == 0:
                    level = 'state'
    
    df = df.loc[df['INDNAICS'] == NAICS].copy()
    try:
        industry = df['Industry Title'].values[0]
    except:
        return "Industry not valid or found", np.nan, np.nan
    if len(df) == 0:
        return "NAICS Code not valid or found", np.nan, np.nan
    df = df.drop_duplicates(subset='INDNAICS').reset_index().iloc[:,1:]
    
    # incorporate tracked levels for conditions
    if level == 'county':
        if df['unwt_county_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: County, Industry: {industry}, High wage percentage: {df['wt_county_hw_perc'].values[0]}", df['wt_county_hw_perc'].values[0], industry
        elif df['unwt_regcomm_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Regional Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_regcomm_hw_perc'].values[0]}", df['wt_regcomm_hw_perc'].values[0], industry
        elif df['unwt_reg_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Regional, Industry: {industry}, High wage percentage: {df['wt_reg_high_wage_perc'].values[0]}", df['wt_reg_high_wage_perc'].values[0], industry
        elif df['unwt_comm_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_comm_high_wage_perc'].values[0]}", df['wt_comm_high_wage_perc'].values[0], industry
        elif df['unwt_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: State, Industry: {industry}, High wage percentage: {df['wt_CA_high_wage_perc'].values[0]}", df['wt_CA_high_wage_perc'].values[0], industry
        else:
            return "Not enough records available to satisfy sample size request", np.nan, np.nan
        
    elif level == 'reg_rural_urban':
        if df['unwt_regcomm_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Regional Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_regcomm_hw_perc'].values[0]}", df['wt_regcomm_hw_perc'].values[0], industry
        elif df['unwt_reg_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Regional, Industry: {industry}, High wage percentage: {df['wt_reg_high_wage_perc'].values[0]}", df['wt_reg_high_wage_perc'].values[0], industry
        elif df['unwt_comm_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_comm_high_wage_perc'].values[0]}", df['wt_comm_high_wage_perc'].values[0], industry
        elif df['unwt_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: State, Industry: {industry}, High wage percentage: {df['wt_CA_high_wage_perc'].values[0]}", df['wt_CA_high_wage_perc'].values[0], industry
        else:
            return "Not enough records available to satisfy sample size request", np.nan, np.nan
        
    elif level == 'region':
        if df['unwt_reg_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Regional, Industry: {industry}, High wage percentage: {df['wt_reg_high_wage_perc'].values[0]}", df['wt_reg_high_wage_perc'].values[0], industry
        elif df['unwt_comm_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_comm_high_wage_perc'].values[0]}", df['wt_comm_high_wage_perc'].values[0], industry
        elif df['unwt_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: State, Industry: {industry}, High wage percentage: {df['wt_CA_high_wage_perc'].values[0]}", df['wt_CA_high_wage_perc'].values[0], industry
        else:
            return "Not enough records available to satisfy sample size request", np.nan, np.nan
        
    elif level == 'rural_urban':
        if df['unwt_comm_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_comm_high_wage_perc'].values[0]}", df['wt_comm_high_wage_perc'].values[0], industry
        elif df['unwt_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: State, Industry: {industry}, High wage percentage: {df['wt_CA_high_wage_perc'].values[0]}", df['wt_CA_high_wage_perc'].values[0], industry
        else:
            return "Not enough records available to satisfy sample size request", np.nan, np.nan
        
    elif level == 'state':
        if df['unwt_ind_counts'].values[0] >= n:
            return f"County: {county}, Geographical level used: State, Industry: {industry}, High wage percentage: {df['wt_CA_high_wage_perc'].values[0]}", df['wt_CA_high_wage_perc'].values[0], industry
        else:
            return "Not enough records available to satisfy sample size request", np.nan, np.nan
        
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
    
def clean_edd(edd):
    """
    Function to clean EDD data.
    """
    edd['Area Name'] = edd['Area Name'].str.replace(' County', '')
    edd = edd.loc[edd['Area Type'] == 'County']
    edd = edd.drop(columns=['Industry Title'])
    edd = edd.rename(columns={"LMID Industry Title": "Industry Title"})
    edd['Sub_1_Code'] = [str(x) for x in edd['Sub_1_Code']]
    edd['Main_Code'] = [str(x) for x in edd['Main_Code']]
    return edd

def cleaned_ipums_demo(year: str):
    """
    Function to clean IPUMS data specifically for a race/demographics breakdown for the specified year.
    Currently has hardcoded file paths for naics_parsed_crosswalk and 
    ind_indnaics_crosswalk_2000_onward_without_code_descriptions csv files.
    """
    cwd = os.getcwd()
    if int(year) < 2015: # change later
        print('Invalid year')
        return None
    ipums = pd.read_csv(f'{cwd}/data/ipums/IPUMS_{year}.csv')
    ipums = ipums[['YEAR','STATEFIP', 'COUNTYFIP', 'INDNAICS','PERWT','RACE','HISPAN','INCWAGE']]
    ca_ipums = ipums.loc[ipums['STATEFIP'] == 6].copy().reset_index().iloc[:,1:]
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
    else:
        ipums_titles = ipums_titles[['2013-2017 ACS/PRCS INDNAICS CODE', 'Industry Title']]
        merged_ipums = pd.merge(ca_ipums, ipums_titles, left_on = 'INDNAICS', right_on = '2013-2017 ACS/PRCS INDNAICS CODE')
        merged_ipums = merged_ipums.rename(columns={"2013-2017 ACS/PRCS INDNAICS CODE": "NAICS Code"})
    naics_parsed_crosswalk = pd.read_csv(f'{cwd}/data/ipums/naics_parsed_crosswalk.csv').drop_duplicates(subset='INDNAICS').reset_index().iloc[:,1:]
    merged_ipums = pd.merge(merged_ipums, naics_parsed_crosswalk, on='INDNAICS')
    return merged_ipums

def parse_edd(edd, crosswalk, parsed_crosswalk, year: int):
    """
    Need to import EDD data (File: data/edd/Current_EDD_1121.csv, Parameter: edd), 
    EDD to LMID crosswalk (File: data/edd/Industry_Title_Crosswalk.csv, Parameter: crosswalk), 
    and EDD to Parsed Code crosswalk (File: data/edd/edd_parsed_crosswalk.csv, Parameter: parsed_crosswalk).
    The parameters of the function, besides year, should be dataframes.
    """
    edd['Industry Title'] = normalize_titles(edd['Industry Title'])
    crosswalk['EDD Industry Title'] = normalize_titles(crosswalk['EDD Industry Title'])
    crosswalk['LMID Industry Title'] = normalize_titles(crosswalk['LMID Industry Title'])
    edd = edd.loc[edd['Area Type'] != 'Metropolitan Area'] # exclude metropolitan areas
    final_edd = edd.loc[edd['Year'] == year].copy() # specify year
    final_edd = pd.merge(final_edd, crosswalk, on='Series Code')
    final_edd = pd.merge(final_edd, parsed_crosswalk, on='Industry Title')
    final_edd = final_edd[['Industry Title', 'LMID Industry Title', 'Parsed_Code', 'Area Type', 'Area Name', 'Date', 'Seasonally Adjusted', 'Current Employment', 'Main_EDD', 'Main_Code', 'Sub_1', 'Sub_1_Code', 'Sub_2', 'Sub_2_Code', 'Sub_3', 'Sub_3_Code', 'Sub_4', 'Sub_4_Code']]  
    return final_edd