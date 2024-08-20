import pandas as pd
import numpy as np
import warnings
import requests
import sys
import argparse
import time
from sklearn.ensemble import GradientBoostingClassifier
import joblib
import site
from tqdm import tqdm

import GenerateActivities as gat
import ExtractEvent as eev
# import ComputeFeatures as cfe
import important_features as imf

from datetime import datetime
from dateutil.relativedelta import relativedelta

TIMEOUT_WAITING_TIME = 30
CONNECTION_ERROR_WAITING_TIME = 10
QUERY_LIMIT_RESET_OVERHEAD_TIME = 120
ALL_FEATURES = ['events', 'NA','NT','NOR','ORR',
                'DCA_mean','DCA_median','DCA_std','DCA_gini',
                'NAR_mean','NAR_median','NAR_gini','NAR_IQR',
                'NTR_mean','NTR_median','NTR_std','NTR_gini',
                'NCAR_mean','NCAR_std','NCAR_IQR',
                'DCAR_mean','DCAR_median','DCAR_std','DCAR_IQR',
                'DAAR_mean','DAAR_median','DAAR_std','DAAR_gini','DAAR_IQR',
                'DCAT_mean','DCAT_median','DCAT_std','DCAT_gini','DCAT_IQR',
                'NAT_mean','NAT_median','NAT_std','NAT_gini','NAT_IQR']

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

    model_file = 'bimbas.joblib'
    for dir in site.getsitepackages():
        if dir.endswith('site-packages'):
            target_dir = dir
        else:
            target_dir = site.getsitepackages()[0]
    bot_identification_model = joblib.load(f'{target_dir}/{model_file}')
    # bot_identification_model = joblib.load(model_file)
    
    return(bot_identification_model)

def compute_confidence(probability_value):
    '''
    args: probability_value (float) - the bot probability value given by the model

    returns: contributor_type (str) - type of contributor determined based on probability ('Bot' or 'Human') 
             confidence (float) - confidence score of the determined type (value between 0.0 and 1.0)

    description: Based on the determined type probability that a contributor is a bot, determine the type of contributor based on threshold and compute the confidence score on type.
    '''

    if(probability_value <= 0.5):
        contributor_type = 'Human'
    else:
        contributor_type = 'Bot'
    confidence = (abs(probability_value - 0.5)*2).round(3)

    return(contributor_type,confidence)

def frame_direct_result(determined_type, confidence, result_cols, contributor):
    '''
    args: determined_type (str) - type determined by GitHub Users API or Unknown or Invalid
          confidence (str/int) - confidence on determined type, int value for type provided by GitHub Users API, str for others
          result_cols (list) - columns that needs to be present in the result
          contributor (str) - contributor name that is being processed at the moment
    
    returns: result (DataFrame) - DataFrame containing the type of contributor, confidence in determining that type and the corresponding feature values

    description: Frame the result with required columns and corresponding feature values for the contributors whose type is directly determined 
                 through GitHub Users API, or did not perform enough events or does not exist on GitHub. This function creates the result for
                 which BIMBAS will not be executed.
    '''
    
    if(determined_type == "Unknown"):
        result = pd.DataFrame([[determined_type,confidence]+[0]+['-']*(len(ALL_FEATURES)-1)], 
                              columns=result_cols,
                              index=[contributor])
    else:
        result = pd.DataFrame([[determined_type,confidence]+['-']*(len(ALL_FEATURES))], 
                              columns=result_cols,
                              index=[contributor])
    
    return(result)

def format_result(result, verbose):
    '''
    args: result (DataFrame) - DataFrame of result obtained through MakePrediction
          verbose (bool) - If True, displays the features, #events and #activities that were used to determine the type
    
    returns: result (DataFrame) - formatted result as per verbose

    description: The result that will be printed directly to the terminal or saved in csv or json will universally be 
                 formatted here. Depending on the value of verbose, the final result will contain just the prediction 
                 and confidence of each contributor or will have all the features that led to the prediction.
    '''

    if verbose:
        result = result[['type','confidence']+ALL_FEATURES]
    else:
        result = result[['type','confidence']]
    
    return(result)

def check_ratelimit(ratelimit, nextResetTime, max_queries):
    '''
    args: rate limit (int) - remaining rate limit for the provided API key
          nextResetTime (int) - time at which the API rate limit will be reset
          max_queries (int) - maximum number of queries per contributor
        
    returns: None

    description: Get the time at which the API rate limit will be reset, calculate its difference from 
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
    
    returns: contributor_type (str) - type of the contributor (e.g., "Bot", "User", "Organization")
             query_failed (bool) - a boolean value to indicate if the query failed or success
    '''

    QUERY_ROOT = "https://api.github.com"
    query_failed = False
    contributor_type = None

    try:
        query = f'{QUERY_ROOT}/users/{contributor}'
        if key:
            headers = {'Authorization': 'token ' + key}
            response = requests.get(query, headers=headers)
        else:
            response = requests.get(query)

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

    description: Query the GitHub Events API with 100 events per page, unpack the json format to get the required fields and store it in list format
    '''

    QUERY_ROOT = "https://api.github.com"
    query_failed = False
    list_event = []

    try:
        query = f'{QUERY_ROOT}/users/{contributor}/events?per_page=100&page={page}'
        if key:
            headers = {'Authorization': 'token ' + key}
            response = requests.get(query, headers=headers)
        else:
            response = requests.get(query)

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

def MakePrediction(contributor, apikey, min_events, min_confidence, max_queries, verbose):
    '''
    args: contributor (str) - name of the contributor for whom the type needs to be determined
          apikey (str) - the API key
          min_events (int) - minimum number of events that a contributor should have performed to determine their type
          min_confidence (float) - minimum confidence on contributor type to stop further querying
          max_queries (int) - maximum number of queries to be made to GitHub Events API
          verbose (bool) - If True, displays the features, #events and #activities that were used to determine the type of contributor
    
    returns: activity_features (array) - an array of 7 features and the probability that the contributor is a bot

    description: 1) Query the GitHub Events API
                 2) Identify the activities performed by the contributor through queried events
                 3) Compute activity features
                 4) Invoke the trained model
                 5) Predict the probability that the contributor is a bot 
                 6) Compute confidence from this probability
    '''
    
    page=1
    df_events_obt = pd.DataFrame()
    activities = pd.DataFrame()
    result_cols = ['type','confidence']+ALL_FEATURES
    confidence = 0.0

    contributor_type, query_failed = QueryUser(contributor, apikey, max_queries)
    if(contributor_type != 'User' and query_failed==False):
        # We only need to distinguish bots from humans if the contributor_type is 'User'.
        # In all other cases we just report the type retrieved from the API with 1.0 confidence.
        result = frame_direct_result(contributor_type, 1.0, result_cols, contributor)
        result = format_result(result, verbose)
    elif(contributor_type == 'User'):
        while(page <= max_queries and (confidence != '-' and confidence <= min_confidence)):
            events, query_failed = QueryEvents(contributor, apikey, page, max_queries)
            if(len(events)>0):
                df_events_obt = pd.concat([df_events_obt, pd.DataFrame.from_dict(events, orient = 'columns')])
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
                    page=max_queries+1 # loop breaking condition
            elif(query_failed):
                result = frame_direct_result('Invalid', '-', result_cols, contributor)
                result = format_result(result, verbose)
                
                return(result)
            elif(page==1):
                result = frame_direct_result('Unknown', '-', result_cols, contributor)
                result = format_result(result, verbose)

                return(result)
            else:
                result = frame_direct_result('Unknown', '-', result_cols, contributor)
                result = format_result(result, verbose)
                page=max_queries+1 # loop breaking condition
                # break
        
            if(df_events_obt.shape[0]>0):
                activities = gat.activity_identification(df_events_obt)
            
            if(len(activities)>0):
                # with warnings.catch_warnings():
                #     warnings.simplefilter("ignore", category=RuntimeWarning)
                activity_features = (
                    imf.extract_features(activities)
                    .set_index([[contributor]])
                )
                if(df_events_obt.shape[0]>=min_events):
                    model = get_model()
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=UserWarning)
                        probability = model.predict_proba(activity_features)
                    contributor_type, confidence = compute_confidence(probability[0][1])
                
                else:
                    contributor_type = 'Unknown'
                    confidence = '-'
                    # break

                result = activity_features.assign(type = contributor_type,
                                                confidence = confidence,
                                                events = df_events_obt.shape[0],
                                                activities = activities.shape[0]
                                                )
            else:
                result = frame_direct_result('Unknown', result_cols, contributor)
            result = format_result(result, verbose)
    
    elif(query_failed):
        result = frame_direct_result('Invalid', '-', result_cols, contributor)
        result = format_result(result, verbose)
        
    return(result)

def get_results(contributors_name_file, contributor_name, apikey, min_events, min_confidence, max_queries, output_type, save_path, verbose, incremental):
    '''
    args: contributors_name_file (str) - path to the text file containing contributors names for which the type needs to be determined
          contributor_name (str) - login name of GitHub contributor for which the type needs to be predicted
          apikey (str) - the API key
          min_events (int) - minimum number of events that a contributor should have performed to determine their type.
          min_confidence (float) - minimum confidence on type of contributor to stop further querying
          max_queries (int) - maximum number of queries to be made to GitHub Events API
          verbose (bool) - if True, displays the features that were used to determine the type of contributor
          result (DataFrame) - DataFrame of results
          save_path (str) - the path along with file name and extension to save the results
          output_type (str) - to convert the results to csv or json 
          incremental (bool) - Update the output file/print on terminal once the type is determined for new contributors. If False, results will be accessible only after the type is determined for all the contributors
    
    returns: None

    description: Gets the results and either prints it on the terminal or write into a json/csv file depending on the provided inputs
    '''

    contributors = []
    if len(contributor_name) > 0:
        contributors.extend(contributor_name)
    if contributors_name_file is not None:
        contributors.extend(pd.read_csv(contributors_name_file, sep=' ', header=None, index_col=0).index.to_list())
    all_results = pd.DataFrame()
    for contributor in tqdm(contributors):
        contributor_type_result = MakePrediction(contributor, apikey, min_events, min_confidence, max_queries, verbose)
        all_results = pd.concat([all_results, contributor_type_result])
        if incremental:
            save_results(all_results, output_type, save_path)
    
    if ~incremental:
        save_results(all_results, output_type, save_path)

def save_results(all_results, output_type, save_path):
    '''
    args: all_results (DataFrame)- all the results (contributor name, type, confidence and so on) and additional information (features used to determine the type)
          save_path (str) - the path along with file name and extension to save the results
          output_type (str) - to convert the results to csv or json
    
    returns: None

    description: Save the results in the given path
    '''

    if output_type == 'text':
        print(all_results
              .reset_index(names=['contributor'])
              .to_string(index=False)
              )
    elif(output_type == 'csv'):
        (all_results
        .reset_index(names=['contributor'])
        .to_csv(save_path)
        )
    elif(output_type == 'json'):
        (all_results
         .reset_index(names=['contributor'])
         .to_json(save_path, orient='records', indent=4)
        )
    

def arg_parser():
    parser = argparse.ArgumentParser(description='RABBIT is an Activity Based Bot Identification Tool that identifies bots based on their recent activities in GitHub')
    parser.add_argument('contributor', action='store', type=str, default=None, nargs='*', 
                        help='For predicting type of single contributor, the login name of the contributor should be provided to the tool.')
    parser.add_argument('--input-file', type=str, default=None, required=False,
                        help='For predicting type of multiple contributors, a .txt file with the login names (one name per line) of the contributors should be provided to the tool.')
    # parser.add_argument(
    #     '--start-time', type=str, required=False,
    #     default=None, help='Start time (format: yyyy-mm-dd HH:MM:SS) to be considered for analysing the contributor's activity. \
    #                         The default start-time is 91 days before the current time.')
    parser.add_argument(
        '--verbose', action="store_true", required=False, default=False,
        help='Also report the values of the number of events, number of identified activities and features that were used to determine the type of contributor. The default value is False.')
    parser.add_argument(
        '--min-events', metavar='MIN_EVENTS', type=int, required=False, default=5,
        help='Minimum number of events that are required to determine the type of contributor. The default minimum number of events is 5.')
    parser.add_argument(
        '--min-confidence', metavar='MIN_CONFIDENCE', type=float, required=False, default=1.0,
        help='Minimum confidence threshold on determined contributor type to stop further querying. The default minimum confidence is 1.0.')
    parser.add_argument(
        '--max-queries', metavar='MAXQUERIES', type=int, required=False, default=3, choices=[1,2,3],
        help='Maximum number of queries to be made to the GitHub Events API for each contributor. The default number of queries is 3, allowed values are 1, 2 or 3.')
    parser.add_argument(
        '--key', metavar='APIKEY', required=False, type=str, default='',
        help='GitHub API key to extract events from GitHub Events API. API key is required if the number of API queries exceed 15 per hour.')
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

    description: parse the args parameters in to tool parameters and pass it to the MakePredictions function
    '''

    args = arg_parser()

    # if args.start_time is not None:
    #     time_after = datetime.strftime(dateutil.parser.parse(args.start_time), '%Y-%m-%d %H:%M:%S')
    # else:
    #     time_after = datetime.strftime(datetime.now()+relativedelta(days=-91), '%Y-%m-%d %H:%M:%S')

    if args.key == '' or len(args.key) < 40:
        warnings.warn('A valid GitHub personal access token is required if more than 15 queries are required to be made per hour. \
Please read more about it in the repository readme file.')
        apikey = None
    else:
        apikey = args.key
    
    if args.input_file is None and len(args.contributor) == 0:
        sys.exit('The login name of a contributor or a .txt file containing login names for contributors should be \
provided to the tool. Please read more about it in the repository readme file.')
    
    if args.min_events < 1 or args.min_events > 300:
        sys.exit('Minimum number of events to determine the contributor type should be between 1 and 300 including both.')
    else:
        min_events = args.min_events
    
    if args.min_confidence <0.0 or args.min_confidence > 1.0:
        sys.exit('Minimum confidence on determined contributor type to stop further querying should be between 0.0 and 1.0 including both.')
    else:
        min_confidence = args.min_confidence

    if args.csv != '':
        output_type = 'csv'
        save_path = args.csv
    elif args.json != '':
        output_type = 'json'
        save_path = args.json
    else:
        output_type = 'text'
        save_path = ''

    get_results(args.input_file,
                args.contributor,
                apikey, 
                min_events, 
                min_confidence,
                args.max_queries, 
                # time_after, 
                output_type,
                save_path,  
                args.verbose,
                args.incremental)

if __name__ == '__main__':
    cli()
