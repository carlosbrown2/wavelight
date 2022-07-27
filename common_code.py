import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import datetime


def get_tables(data):
    '''
    Find the tables in the data and return them in a list.

    Parameters: data - requests.Response object containing data tables
    Returns: list of dataframes containing the data from the tables
    '''
    table_class="wikitable sortable jquery-tablesorter"
    soup = BeautifulSoup(data.text, 'html.parser')
    wikitable=soup.findAll('table',{'class':"wikitable"})

    table_df_list = []
    for table in wikitable:
        table_df_list.append(pd.read_html(str(table))[0])

    return table_df_list


def create_world_records_df(df_list):
    '''
    Set up the dataframe containing the world records.

    Paramaters: df_list - list of dataframes containing the data from the tables.
    Returns: records_df - dataframe containing men's and women's indoor and outdoor track records.
    '''
    # select desired tables
    df_men = df_list[0] # World record Mens
    df_women = df_list[1] # World record Womens
    df_men_indoor = df_list[3] # Indoor World Record Mens
    df_women_indoor = df_list[4] # Indoor World Record Womens

    # Remove multiindex
    df_men.columns = df_men.columns.droplevel(0)

    # Format Dates
    df_men.Date = pd.to_datetime(df_men.Date)
    df_men_indoor.Date = pd.to_datetime(df_men_indoor.Date)
    df_women.Date = pd.to_datetime(df_women.Date)
    df_women_indoor.Date = pd.to_datetime(df_women_indoor.Date)

    # Add gender category
    df_women['gender'] = 'W'
    df_men['gender'] = 'M'

    # Select running events we want to keep
    df_men = df_men.iloc[~df_men.index.isin([x for x in range(20,42)]),:]
    df_men_indoor = df_men_indoor.iloc[df_men_indoor.index.isin([x for x in range(0,12)]), :]
    df_women = df_women.iloc[~df_women.index.isin([x for x in range(27,50)]),:]
    df_women_indoor = df_women_indoor.iloc[df_women_indoor.index.isin([x for x in range(0,10)]),:]

    # Combine wikipedia records
    df = pd.concat([df_men, df_women, df_men_indoor, df_women_indoor])
    df = df.reset_index(drop=True)
    df['year'] = df.Date.dt.year

    # Correct Meeting names in line with wavelight nomenclature
    df.iloc[9,9] = 'Diamond League'
    df.iloc[11,9] = 'NN World Record Day'
    df.iloc[34,9] = 'NN World Record Day'

    return df


def world_record_url_to_df():
    '''
    Take the men's and women's outdoor and indoor track and field world records from
    "https://en.wikipedia.org/wiki/List_of_world_records_in_athletics" and put them
    in a dataframe.

    Returns: a dataframe and the status code from getting the url.
    '''
    url = 'https://en.wikipedia.org/wiki/List_of_world_records_in_athletics'
    wiki_data = requests.get(url)
    df_list = get_tables(wiki_data)
    records_df = create_world_records_df(df_list)

    return(records_df, wiki_data.status_code)


def create_wavelight_records_df(data):
    '''
    Take the wavelight data and put it into a dataframe with the same format as
    the world records dataframe.
    
    Parameters: data - the results of the requests.get call on the wavelight url.
    Returns: df_wave - dataframe containing wavelight data.
    '''
    soup = BeautifulSoup(data.text, 'html.parser')
    wave_table = soup.find('table')
    df_wave = pd.read_html(str(wave_table))[0]
    df_wave['year'] = df_wave['Meeting'].apply(lambda x: x.split(' (')[1].replace(')',''))
    df_wave['Meeting'] = df_wave['Meeting'].apply(lambda x: x.split(' (')[0])
    
    # Column name changes
    mapper = {'The Track at Boston': 'The Track at Boston',
              'International Meeting de Lievin': 'Meeting Hauts-de-France Pas-de-Calais',
              'Ethiopian Trials': 'Ethiopian Olympic Trials',
              'FBK Games': 'FBK Games',
              'NN World Record Day': 'NN World Record Day',
              'Memorial van Damme': 'Diamond League',
              'Herculis Monaco': 'Herculis',
              'Monaco Diamond League': 'Diamond League',
              'Impossible Games': 'Impossible Games'}
    df_wave.Meeting = df_wave.Meeting.map(mapper)
    df_wave['wavelight'] = 'y'
    # Individual adjustments
    df_wave.iloc[1,0] = 'Jakob Ingebrigtsen'

    return(df_wave)


def wavelight_url_to_df():
    '''
    Place the track world records for men and women, indoor and outdoor listed at
    "https://wavelight.live/past-events/" in a dataframe
    
    Returns: a dataframe and the status code from gettin the url.
    '''

    wave_url = 'https://wavelight.live/past-events/'
    wave_data = requests.get(wave_url)
    
    wave_records_df = create_wavelight_records_df(wave_data)

    return (wave_records_df, wave_data.status_code)


def combine_dfs(df_wave, df_records):
    '''
    Combine the wavelight dataframe with the world records dataframe
    
    Parameters: df_wave - dataframe containing wavelight info
                df_records - dataframe containing world record info
    Returns: comb_df - dataframe containing the combined info
    '''
    
    df_wave.year = df_wave.year.astype('int64')
    df_comb = df_records.merge(df_wave,
                               how='left',
                               left_on=['Athlete(s)', 'Meeting', 'year'],
                               right_on=['Athlete', 'Meeting', 'year'])
    df_comb.wavelight = df_comb.wavelight.fillna('n')
    # Add Sifan Hassan record from 2021 that is missing from wikipedia
    df_comb = pd.concat([df_comb, pd.DataFrame({'Event': '10,000 m',
                                                 'Athlete(s)':'Sifan Hassan',
                                                 'Meeting': 'FBK Games',
                                                 'year':2021,
                                                 'Date':datetime.date(year=2021, month=6, day=6),
                                                 'wavelight':'y', 'gender': 'W', 'Perf.': '29:06.82'},
                                                 index=[0])],
                                                 ignore_index=True)
    return df_comb


def check_status(status, location):
    '''
    Prints and error message if the status is not 200
    
    Parameters: status - int value or variable containing status code
                location - string description of where status code came from
    '''

    if status == 200:
        print(f'{str.capitalize(location)} sucessfully opened and read.')
    else:
        print(f'Unable to open or read {location}.  Error code: {status}')