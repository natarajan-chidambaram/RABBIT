import numpy as np
import pandas as pd

def gini(array):
    '''
    args: array - an array of numbers
    
    return: g_coeff - float that gives gini coefficient
    
    method: calculate the Gini coefficient of a numpy array
    '''
    
    array = array[array!=0]
    if len(array) == 0:
        return np.float64(0.0)
    array = array.flatten()
    array = np.sort(array)
    index = np.arange(1, array.shape[0] + 1)
    n = array.shape[0]
    g_coeff = (np.sum((2 * index - n - 1) * array)) / (n * np.sum(array))
    
    return (g_coeff)

def extract_features(df):
    '''
    args: df - DataFrame; table of contributor activities

    returns: features - numpy array; an array of contributor behavioural features

    description: compute the contributor behavioural features
                 1) Mean number of activities per activity type
                 2) Number of activity types
                 3) Meadian time between activities of different activity types
                 4) Number of owners of repositories contributed to
                 5) Gini coefficient of time between consecuvtive activities
                 6) Mean number of activities per repository
    '''
    
    df['date'] = pd.to_datetime(df.date, errors='coerce').dt.tz_localize(None)
    df[['owner','repo']]=df.repository.str.split('/', expand=True)
    #1
    mean_num_activities_per_type = (
                                    df
                                    .groupby('activity')
                                    .agg(act_count=('repository','count'))
                                    ['act_count']
                                    .mean()
                                    .round(3)
                                   )
    
    #2
    num_activity_types = df.activity.nunique()
    
    #3
    median_time_bet_activity_different_type = (
                                               df
                                               .sort_values('date')
                                               .assign(group=lambda d: (d.activity != d.activity.shift(1)).cumsum())
                                               .groupby('group')
                                               .agg(activities=('repository', 'count'), first_time=('date','first'), last_time=('date','last'))
                                               .assign(next_first_time=lambda d: d.first_time.shift(-1))
                                               .assign(time_spent=lambda d: (d.last_time - d.first_time)/pd.to_timedelta('1 hour'))
                                               .assign(time_to_switch=lambda d: (d.next_first_time - d.last_time)/pd.to_timedelta('1 hour'))
                                               ['time_to_switch']
                                               .median()
                                               .round(3)
                                              )
    
    #4
    num_owner = df.owner.nunique()

    #5
    time_between_consecutive_activities = (
                 df[['date','activity','repository']]
                 .sort_values('date')
                 .assign(next_time_stamp = lambda d: d.date.shift(-1))
                 .assign(time_diff = lambda d: d.next_time_stamp - d.date)
                 .assign(time_diff = lambda d: d.time_diff/pd.to_timedelta('1 hour'))
                 ['time_diff']
                 .dropna()
                 .to_numpy()
               )
    Gini_time_between_consecutive_activities = gini(time_between_consecutive_activities).round(3)

    #6
    mean_num_act_per_repo = (
                             df
                             .groupby('repository')
                             .agg(act_count=('activity','count'))
                             ['act_count']
                             .mean()
                             .round(3)
                            )
    
    features = np.array([mean_num_activities_per_type, 
                         num_activity_types, 
                         median_time_bet_activity_different_type, 
                         num_owner, 
                         Gini_time_between_consecutive_activities, 
                         mean_num_act_per_repo])
    
    return(features)