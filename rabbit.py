import pandas as pd
import numpy as np
import warnings
import requests
import sys
import argparse
import time
import dateutil
import xgboost as xgb
import site
from tqdm import tqdm

import GenerateActivities as gat
import ExtractEvent as eev
import ComputeFeatures as cfe

from datetime import datetime
from dateutil.relativedelta import relativedelta

TIMEOUT_WAITING_TIME = 30
CONNECTION_ERROR_WAITING_TIME = 10
QUERY_LIMIT_RESET_OVERHEAD_TIME = 120

def time_to_pause(nextResetTime):
    '''    
    args:
        nextResetTime (str/int): Next reset time for the corresponding API key in the form of timestamp
    
    returns:
        timeDiff (float): The time that is remaining for the next reset to happen. This is the time (in seconds) that the script needs to wait/sleep
        ResetTime (datetime.datetime): The time at which the next reset happens
    
    description: Calculates the time for resetting query rate limit + QUERY_LIMIT_RESET_OVERHEAD_TIME that 
                 is required to pause querying in case of limit exceed situation
    '''

    ResetTime = datetime.fromtimestamp(int(nextResetTime)).strftime('%Y-%m-%d %H:%M:%S')
    ResetTime = datetime.strptime(ResetTime, '%Y-%m-%d %H:%M:%S')
    timeDiff = (ResetTime - datetime.now()).total_seconds() + QUERY_LIMIT_RESET_OVERHEAD_TIME
    return timeDiff, ResetTime

def get_model():
    '''
    args: None

    returns: bot_identification_model (json); Json file with trained model parameters
    
    description: Load the bot identification model
    '''

    bot_identification_model = xgb.XGBClassifier()
    for dir in site.getsitepackages():
        if dir.endswith('site-packages'):
            target_dir = dir
        else:
            target_dir = site.getsitepackages()[0]
    bot_identification_model.load_model(f'{target_dir}/rabbit_model.json')
    # filename = 'rabbit_model.json'
    # bot_identification_model = xgb.XGBClassifier()
    # bot_identification_model.load_model(filename)
    
    return(bot_identification_model)

def compute_confidence(probability_value):
    '''
    args: probability_value (float) - the bot probability value given by the model

    returns: prediction (str) - prediction of contribtuor type based on probability ('bot' or 'human') 
             confidence (float) - confidence score of the prediction

    description: based on the prediction probability that a contributor is a bot, make the prediction based on threshold
                 and compute the confidence score on the prediction
    '''

    if(probability_value <= 0.5):
        prediction = 'human'
    else:
        prediction = 'bot'
    confidence = (abs(probability_value - 0.5)*2).round(3)

    return(prediction,confidence)

def format_result(result, verbose):
    '''
    args: result (DataFrame) - DataFrame of result obtained through MakePrediction
          verbose (bool) - If True, displays the features, #events and #activities that were used to make the prediction
    
    returns: result (DataFrame) - formatted result as per verbose

    description: The result that will be printed or saved will universally be formatted here as per the input value of verbose.
    '''

    if verbose:
        result = result[['events','activities',
                        'NAT_mean','NT',
                        'DCAT_median','NOR',
                        'DCA_gini','NAR_mean',
                        'prediction','confidence']]
    else:
        result = result[['prediction','confidence']]
    
    return(result)

def check_ratelimit(ratelimit, nextResetTime, max_queries):
    '''
    args: ratelimit (int) - remaining ratelimit for the provided API key
          nextResetTime (int) - time at which the API ratelimit will be reset
          max_queries (int) - maximum number of queries per account
        
    returns: None

    description: Get the time at which the API rate limit will be reset, calcualte its difference from 
                 current time + some time overhead and sleep for that much time.
    '''
    if ratelimit < max_queries:
        pause, ResetTime = time_to_pause(nextResetTime)
        print("Remaining API query limit is {0}. Querying paused until next reset time: {1}".format(ratelimit, ResetTime))
        time.sleep(pause)

def timeout_exception():
    '''
    args: None

    returns: None

    description: Wait for TIMEOUT_WAITING_TIME for trying to query again
    '''
    print('Request timeout exceeded, retrying after 60 seconds')
    time.sleep(TIMEOUT_WAITING_TIME)
    print('Retrying...')

def connection_error_exception():
    '''
    args: None

    returns: None

    description: Wait for CONNECTION_ERROR_WAITING_TIME for trying to query again
    '''
    print("Connection error, retrying after 10 seconds")
    time.sleep(CONNECTION_ERROR_WAITING_TIME)
    print('Retrying...')

def QueryUser(contributor, key, max_queries):
    '''
    args: contributor (str) - contributor name
          key (str) - the API key
    
    returns: contributor_type (str) - type of the contribitor ("Bot" or "User")
             query_failed (bool) - a boolean value to indicate if the query failed or success
    '''

    QUERY_ROOT = "https://api.github.com"
    query_failed = False
    contributor_type = 'unknown'

    try:
        query = f'{QUERY_ROOT}/users/{contributor}'
        headers = {'Authorization': 'token ' + key}
        response = requests.get(query, headers=headers)

        if response.ok:
            json_response = response.json()
            if not json_response:
                return(contributor_type, query_failed)
            else:
                contributor_type = json_response['type']
            
            check_ratelimit(int(response.headers['X-RateLimit-Remaining']), int(response.headers['X-RateLimit-Reset']), max_queries)
        
        else:
            query_failed = True
            return(contributor_type, query_failed)
    except requests.exceptions.Timeout as e:
        timeout_exception()
    except requests.ConnectionError as e:
        connection_error_exception()
    
    return(contributor_type, query_failed)


def QueryEvents(contributor, key, page, max_queries):
    '''
    args: contributor (str) - contributor name
          key (str) - the API key
          page (str) - the events page number to be queried
    
    returns: list_events (list) - a list of events that were performed by contributor
             query_failed (bool) - a boolean value to indicate if the query failed or success

    description: Query the GitHub Events API with 100 events per page, unpack the json format to get the requried fields and store it in list format
    '''

    QUERY_ROOT = "https://api.github.com"
    query_failed = False
    list_event = []

    try:
        query = f'{QUERY_ROOT}/users/{contributor}/events?per_page=100&page={page}'
        headers = {'Authorization': 'token ' + key}
        response = requests.get(query, headers=headers)

        if response.ok:
            json_response = response.json()
            if not json_response and page == 1:
                return(list_event, query_failed)
            else:
                events = eev.unpackJson(json_response)
                list_event.extend(events)
            
            check_ratelimit(int(response.headers['X-RateLimit-Remaining']), int(response.headers['X-RateLimit-Reset']), max_queries)

        else:
            query_failed = True
            return(list_event, query_failed)
    except requests.exceptions.Timeout as e:
        timeout_exception()
    except requests.ConnectionError as e:
        connection_error_exception()
    
    return(list_event, query_failed)

def MakePrediction(contributor, apikey, min_events, max_queries, verbose):
    '''
    args: contributor (str) - name of the contributor for whom the prediciton needs to be made
          apikey (str) - the API key
          min_events (int) - minimum number of events that a contributor should have performed to consider them for prediciton
          max_queries (int) - maximum number of queries to be made to GitHub Events API
          verbose (bool) - If True, displays the features, #events and #activities that were used to make the prediction
    
    returns: activity_features (array) - an array of 7 features and the probability that the contributor is a bot

    description: 1) Query the GitHub Events API
                 2) Identify the activities performed by the contributor through queried events
                 3) Compute activity features
                 4) Invoke the trained model
                 5) Predict the proability that the contributor is a bot 
    '''
    
    page=1
    not_app = True
    df_events_obt = pd.DataFrame()
    activities = pd.DataFrame()
    all_features = ['events','activities',
                    'NAT_mean','NT',
                    'DCAT_median','NOR',
                    'DCA_gini','NAR_mean']
    result_cols = all_features + ['prediction','confidence']

    if('[bot]' in contributor):
        contributor_type, query_failed = QueryUser(contributor, apikey, max_queries)
        if(contributor_type == 'Bot'):
            result = pd.DataFrame([[np.nan]*len(all_features) +['app',1.0]], 
                                        columns=result_cols,
                                        index=[contributor])
            result = format_result(result, verbose)
            not_app = False
        
        elif(query_failed):
            result = pd.DataFrame([[np.nan]*len(all_features) +['invalid',np.nan]], 
                                columns=result_cols,
                                index=[contributor])
            result = format_result(result, verbose)
            not_app = False

    if(not_app):
        while(page <= max_queries):
            events, query_failed = QueryEvents(contributor, apikey, page, max_queries)
            if(len(events)>0):
                df_events_obt = pd.concat([df_events_obt, pd.DataFrame.from_dict(events, orient = 'columns').assign(page=page)])
                df_events_obt['created_at'] = pd.to_datetime(df_events_obt.created_at, errors='coerce', format='%Y-%m-%dT%H:%M:%SZ').dt.tz_localize(None)
                # time_after = pd.to_datetime(time_after, errors='coerce', format='%Y-%m-%d %H:%M:%S').tz_localize(None)
                
                # if(df_events_obt['created_at'].min() > time_after):
                #     time_limit_reached=True
                # else:
                #     time_limit_reached=False
                # df_events_obt = df_events_obt[df_events_obt['created_at']>=time_after].sort_values('created_at')
                df_events_obt = df_events_obt.sort_values('created_at')
                # if(len(events) == 100 and time_limit_reached):
                if(len(events) == 100):
                        page = page + 1
                else:
                    break
            elif(query_failed):
                result = pd.DataFrame([[np.nan]*len(all_features) +['invalid',np.nan]], 
                                    columns=result_cols,
                                    index=[contributor])
                result = format_result(result, verbose)
                
                return(result)
            else:
                result = pd.DataFrame([[0,0]+[np.nan]*(len(all_features)-2)+['unknown',np.nan]], 
                                    columns=result_cols,
                                    index=[contributor])
                result = format_result(result, verbose)

                return(result)
        if(df_events_obt.shape[0]>0):
            activities = gat.activity_identification(df_events_obt)
        
        if(len(activities)>0):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                activity_features = cfe.extract_features(activities)
            activity_features = pd.DataFrame([activity_features], 
                                                index=[contributor], 
                                                columns=['NAT_mean',
                                                        'NT',
                                                        'DCAT_median',
                                                        'NOR',
                                                        'DCA_gini',
                                                        'NAR_mean']
                                            )
            if(df_events_obt.shape[0]>=min_events):
                model = get_model()
                probability = model.predict_proba(activity_features)
                prediction, confidence = compute_confidence(probability[0][1])
            
            else:
                prediction = 'unknown'
                confidence = np.nan

            result = activity_features.assign(events = df_events_obt.shape[0],
                                            activities = activities.shape[0],
                                            prediction = prediction, 
                                            confidence = confidence
                                            )
            result = format_result(result, verbose)

            return(result)
        else:
            result = pd.DataFrame([[0,0]+[np.nan]*(len(all_features)-2)+['unknown',np.nan]], 
                                columns=result_cols,
                                index=[contributor])
            result = format_result(result, verbose)
        
    return(result)

def get_results(contributors_name_file, contributor_name, apikey, min_events, max_queries, output_type, save_path, verbose, incremental):
    '''
    args: contributors_name_file (str) - path to the csv file containing contributors names for which the predicitons need to be made
          contributor_name (str) - login name of GitHub account for which the type needs to be predicted
          apikey (str) - the API key
          min_events (int) - minimum number of events that a contributor should have performed to consider them for prediciton
          max_queries (int) - maximum number of queries to be made to GitHub Events API
          verbose (bool) - if True, displays the features that were used to make the prediction
          result (DataFrame) - DataFrame of prediction results
          save_path (str) - the path along with file name and extension to save the prediction results
          output_type (str) - to convert the results to csv or json 
          incremental (bool) - Update the output file/print on terminal once new predictions are made. If False, 
                          results will be accessible only after the predicitons are made for all the contributors
    
    returns: None

    description: Gets the prediciton results and either prints it on the terminal or write into a json/csv file 
                 depending on the provided inputs
    '''

    contributors = []
    if len(contributor_name) > 0:
        contributors.extend(contributor_name)
    if contributors_name_file is not None:
        contributors.extend(pd.read_csv(contributors_name_file, sep=' ', header=None, index_col=0).index.to_list())
    all_results = pd.DataFrame()
    for contributor in tqdm(contributors):
        prediction_result = MakePrediction(contributor, apikey, min_events, max_queries, verbose)
        all_results = pd.concat([all_results, prediction_result])
        if incremental:
            save_results(all_results, output_type, save_path)
    
    if ~incremental:
        save_results(all_results, output_type, save_path)

def save_results(all_results, output_type, save_path):
    '''
    args: all_results (DataFrame)- all the predictions and additional informations
          save_path (str) - the path along with file name and extension to save the prediction results
          output_type (str) - to convert the results to csv or json
    
    returns: None

    description: Save the results in the given path
    '''

    if output_type == 'text':
        print(all_results.reset_index(names=['account']).to_string(index=False))
    elif(output_type == 'csv'):
        all_results.reset_index(names=['account']).to_csv(save_path)
    elif(output_type == 'json'):
        all_results.reset_index(names=['account']).to_json(save_path, orient='records', indent=4)
    

def arg_parser():
    parser = argparse.ArgumentParser(description='RABBIT is an Activity Based Bot Identification Tool that identifies bots based on their recent activities in GitHub')
    parser.add_argument('account', action='store', type=str, default=None, nargs='*', 
                        help='For predicting type of single account, the login name of the account should be provided to the tool.')
    parser.add_argument('--file', type=str, default=None, required=False,
                        help='For predicting type of multiple accounts, a .txt file with the login names (one name per line) of the accounts should be provided to the tool.')
    # parser.add_argument(
    #     '--start-time', type=str, required=False,
    #     default=None, help='Start time (format: yyyy-mm-dd HH:MM:SS) to be considered for anlysing the account\'s activity. \
    #                         The default start-time is 91 days before the current time.')
    parser.add_argument(
        '--verbose', action="store_true", required=False, default=False,
        help='Also report the values of the number of events, number of identified activities and features that were used to make the prediction. The default value is False.')
    parser.add_argument(
        '--min-events', metavar='MIN_EVENTS', type=int, required=False, default=5,
        help='Minimum number of events that are required to make a prediction. The default minimum number of events is 5.')
    parser.add_argument(
        '--max-queries', metavar='MAXQUERIES', type=int, required=False, default=3, choices=[1,2,3],
        help='Maximum number of queries to be made to the GitHub Events API for each account. The default number of queries is 3, allowed values are 1, 2 or 3.')
    parser.add_argument(
        '--key', metavar='APIKEY', required=True, type=str, default='',
        help='GitHub API key to extract events from GitHub Events API')
    parser.add_argument(
        '--csv', metavar='FILE_NAME.csv', required=False, type=str, default='',
        help='Saves the result in comma-separated values (csv) format.')
    parser.add_argument(
        '--json', metavar='FILE_NAME.json', required=False, type=str, default='',
        help='Saves the result in json format.')
    parser.add_argument(
        '--incremental', action="store_true", required=False, default=False, 
        help='Method of reporting the results - incremental/all at once. The default value is False.')

    return parser.parse_args()


def cli():
    '''
    args: None

    returns: None

    description: parse the args paramters in to tool parameters and pass it to the MakePredictions function
    '''

    args = arg_parser()

    # if args.start_time is not None:
    #     time_after = datetime.strftime(dateutil.parser.parse(args.start_time), '%Y-%m-%d %H:%M:%S')
    # else:
    #     time_after = datetime.strftime(datetime.now()+relativedelta(days=-91), '%Y-%m-%d %H:%M:%S')

    if args.key == '' or len(args.key) < 40:
        sys.exit('A valid GitHub personal access token is required to start the process. \
Please read more about it in the repository readme file.')
    else:
        apikey = args.key
    
    if args.file is None and len(args.account) == 0:
        sys.exit('The login name of an acount or a .txt file containing login names for accounts should be \
provided to the tool. Please read more about it in the respository readme file.')
    
    if args.min_events < 1 or args.min_events > 300:
        sys.exit('Minimum number of events to make a prediction should be between 1 and 300 including both')
    else:
        min_events = args.min_events

    if args.csv != '':
        output_type = 'csv'
        save_path = args.csv
    elif args.json != '':
        output_type = 'json'
        save_path = args.json
    else:
        output_type = 'text'
        save_path = ''

    get_results(args.file,
                args.account,
                apikey, 
                min_events, 
                args.max_queries, 
                # time_after, 
                output_type,
                save_path,  
                args.verbose,
                args.incremental)

if __name__ == '__main__':
    cli()