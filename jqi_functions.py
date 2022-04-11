import numpy as np
import pandas as pd
import string
import os
import matplotlib.pyplot as plt

def normalize_titles(col):
    col = col.astype(str)
    col = col.str.strip()
    col = col.str.lower()
    col = col.str.replace('&', 'and')
    col = col.apply(lambda x:''.join([i for i in x if i not in string.punctuation]))
    return col

# edit to generalize for all files/locations
def load_initial_data(year: str, family_size: str):
    cwd = os.getcwd()
    if int(year) < 2015:
        print('Invalid year')
        return None
    ipums = pd.read_csv(f'{cwd}/data/IPUMS_{year}.csv')
    ipums = ipums[['STATEFIP', 'COUNTYFIP', 'INDNAICS','PERWT','INCWAGE']]
    ca_ipums = ipums.loc[ipums['STATEFIP'] == 6].copy()
    ca_ipums = ca_ipums.reset_index().iloc[:,1:]
    ipums_titles = pd.read_csv(f'{cwd}/data/ind_indnaics_crosswalk_2000_onward_without_code_descriptions.csv')
    ipums_titles = ipums_titles.iloc[2:]
    ipums_titles = ipums_titles.iloc[:,9:]
    if int(year) >= 2018:
        ipums_titles = ipums_titles[['2018 Onward ACS/PRCS INDNAICS CODE', 'Industry Title']]
    else:
        ipums_titles = ipums_titles[['2013-2017 ACS/PRCS INDNAICS CODE', 'Industry Title']]
    cost_of_living = pd.read_csv(f'{cwd}/data/united-way-col-{family_size}{year}.csv')
    cost_of_living = cost_of_living.iloc[0:11, :2]
    naics_parsed_crosswalk = pd.read_csv(f'{cwd}/data/naics_parsed_crosswalk.csv').drop_duplicates(subset='INDNAICS').reset_index().iloc[:,1:]
    county_info = pd.read_csv(f'{cwd}/data/county_to_regions_key - Sheet1.csv')
    return ca_ipums, ipums_titles, cost_of_living, naics_parsed_crosswalk, county_info

def cleaned_ipums(year: str):
    cwd = os.getcwd()
    if int(year) < 2015:
        print('Invalid year')
        return None
    ipums = pd.read_csv(f'{cwd}/data/IPUMS_{year}.csv')
    ipums = ipums[['YEAR','STATEFIP', 'COUNTYFIP', 'INDNAICS','PERWT','INCWAGE']]
    ca_ipums = ipums.loc[ipums['STATEFIP'] == 6].copy().reset_index().iloc[:,1:]
    ipums_titles = pd.read_csv(f'{cwd}/data/ind_indnaics_crosswalk_2000_onward_without_code_descriptions.csv')
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
    naics_parsed_crosswalk = pd.read_csv(f'{cwd}/data/naics_parsed_crosswalk.csv').drop_duplicates(subset='INDNAICS').reset_index().iloc[:,1:]
    merged_ipums = pd.merge(merged_ipums, naics_parsed_crosswalk, on='INDNAICS')
    return merged_ipums

def show_null(df):
    print(f'''TOTAL ROWS: {len(df)}''')
    for column in df.columns.values:
        total = len(df)
        nulls = df[column].isna().sum()
        percentage = (nulls / total) * 100
        print(f'''{column}: {nulls} null values, {percentage:.2f}%''')
        
def add_to_state_df(df):
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
    df_new = df.copy() # initialize new dataframe
    df_new = add_to_state_df(df_new) # creating state level counts
    df_new = add_to_community_df(df_new) # creating rural/urban level counts
    df_new = add_to_region_df(df_new) # creating regional level counts
    df_new = add_to_regioncomm_df(df_new) # creating regional rural/urban level counts
    df_new = add_to_county_df(df_new) # creating county level counts
    return df_new

# def ca_ipums_filter(df, county: str, NAICS: str, n: int):
#     df = df.loc[df['County'] == county].copy()
#     if len(df) == 0:
#         return "County not valid or found", np.nan
#     df = df.loc[df['INDNAICS'] == NAICS].copy()
#     industry = df['Industry Title'].values[0]
#     if len(df) == 0:
#         return "NAICS Code not valid or found", np.nan
#     df = df.drop_duplicates(subset='INDNAICS').reset_index().iloc[:,1:]
#     if df['unwt_county_ind_counts'].values[0] >= n:
#         return f"County: {county}, Geographical level used: County, Industry: {industry}, High wage percentage: {df['wt_county_hw_perc'].values[0]}", df['wt_county_hw_perc'].values[0]
#     elif df['unwt_regcomm_ind_counts'].values[0] >= n:
#         return f"County: {county}, Geographical level used: Regional Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_regcomm_hw_perc'].values[0]}", df['wt_regcomm_hw_perc'].values[0]
#     elif df['unwt_reg_ind_counts'].values[0] >= n:
#         return f"County: {county}, Geographical level used: Regional, Industry: {industry}, High wage percentage: {df['wt_reg_high_wage_perc'].values[0]}", df['wt_reg_high_wage_perc'].values[0]
#     elif df['unwt_comm_ind_counts'].values[0] >= n:
#         return f"County: {county}, Geographical level used: Rural/Urban, Industry: {industry}, High wage percentage: {df['wt_comm_high_wage_perc'].values[0]}", df['wt_comm_high_wage_perc'].values[0]
#     elif df['unwt_ind_counts'].values[0] >= n:
#         return f"County: {county}, Geographical level used: State, Industry: {industry}, High wage percentage: {df['wt_CA_high_wage_perc'].values[0]}", df['wt_CA_high_wage_perc'].values[0]
#     else:
#         return "Not enough records available to satisfy sample size request", np.nan
    
def edd_to_hw(edd_df, ipums_df_hw, naics_df, county_df, county: str, parsed_code: str, date: str, sample_size: int):
    # filter edd by date, edd county, and industry via parsed code
    edd_df = edd_df.loc[edd_df['Date'] == date].copy()
    if len(edd_df) == 0:
        return "Date not valid or found", np.nan, np.nan, np.nan
    edd_df = edd_df.loc[(edd_df['Sub_4_Code'] == parsed_code) | 
                        (edd_df['Sub_3_Code'] == parsed_code) | 
                        (edd_df['Sub_2_Code'] == parsed_code) | 
                        (edd_df['Sub_1_Code'] == parsed_code) | 
                        (edd_df['Main_Code'] == parsed_code)].copy()
    edd_df = edd_df.loc[edd_df['Area Name'] == county] # this is possible because all counties are in EDD data
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
    return output, hw_count, industry, employment_count # this is currently naics industry - should be edd industry?

def ca_ipums_filter(df, county_df, county: str, NAICS: str, n: int):
    df = df.loc[df['County'] == county].copy()
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
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(df.index, df['High Wage Count'], color='green')
    ax.set_xlabel('Date')
    ax.set_ylabel('High Wage Count')
    ax.set_title(f'{title}', fontsize=14, pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_linewidth(0.5)