import pandas as pd
import numpy as np
'''
fields that will be present under each activity of the contributor and constants
'''
general = ['date','activity','contributor','repository']
event_general = ['event_id','event_type','login','repository','created_at']
UPPER_TIME_THRESHOLD = '0 days 00:00:02'
LOWER_TIME_THRESHOLD = '-1 days +23:59:58'

'''
Identifying activities from events
'''
def CreatingRepository(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations
    
    Creating repository: Filter data based on CreateEvent with ref_type as repository
    '''

    create_repository = (
        df_events
        [event_general+['ref_type']]
        .assign(activity='Creating repository')
        .rename(columns={'login':'contributor',
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )
    list_event_id_covered.extend(create_repository['event_id'].to_list())

    create_repository=create_repository.sort_values('date')

    df_all_activities = pd.concat([df_all_activities,create_repository.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def merge_misc_related(df_all, df):
    '''
    args: df_all - DataFrame of all activities
          df - DataFrame of issue related activities

    return: df_all - DataFrame with all the activities

    method: For miscellaneous activities, get the dataframe that has all the activities, 
    append the new activities with required fields and return dataframe with all activities.
    '''
    df_all = pd.concat([df_all, df.drop_duplicates()[general]])

    return(df_all)

def CreateBranch(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Creating branch: Filter data based on CreateEvent and ref_type as branch
    '''
    
    create_branch = (
        df_events
        [event_general]
        .assign(activity = 'Creating branch')
        .rename(columns={'login':'contributor', 
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .assign(type="branch")
        .drop_duplicates()
        .sort_values('date')
    )
    list_event_id_covered.extend(create_branch['event_id'].to_list())
    
    df_all_activities = merge_misc_related(df_all_activities, create_branch)

    return df_all_activities, list_event_id_covered

def PublishingRelease(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations
    
    Publishing a release:
    Some Releases have a new tag that is created at the moment of creating the release, 
    whereas the other releases make use of an existing tag. Publishing release is made up of
    1. Identifying ReleaseEvent and tag CreateEvent that occurs together
        (i) identify the tag CreateEvent that happened within 2 seconds of ReleaseEvent
        (ii) identify the ReleaseEvent that happened within 2 seconds of tag CreateEvent
    2. Identifying ReleaseEvent that does not have a corresponding tag CreateEvent
    '''

    if(df_events.columns.isin(['ref']).any()):
        df_rel_cr = (
            df_events
            .drop_duplicates()
            [event_general+['tag_name','ref','release_node_id']]
            .sort_values(['login','repository','created_at'])
        
            .assign(next_event_id=lambda d: d.event_id.shift(-1))
            .assign(next_event=lambda d: d.event_type.shift(-1))
            .assign(next_login=lambda d: d.login.shift(-1))
            .assign(next_repository=lambda d: d.repository.shift(-1))
            .assign(next_ref=lambda d: d.ref.shift(-1))
            .assign(next_event_created_at=lambda d: d.created_at.shift(-1))

            .assign(cr_event_type=lambda d: 
                    np.where(((d.event_type == "ReleaseEvent") & (d.next_event == "CreateEvent") & 
                            (d.login == d.next_login) & (d.repository == d.next_repository) &
                            (d.tag_name == d.next_ref)), 
                            d.next_event, np.nan))
            .query('event_type == "ReleaseEvent" and cr_event_type == "CreateEvent"')
        )
        if(df_rel_cr.shape[0]>0):
            df_rel_cr = (
                df_rel_cr
                .rename(columns={'next_event_created_at':'cr_created_at',
                                'next_ref':'cr_ref',
                                'next_event_id':'cr_event_id', 
                                'next_repository':'cr_repository',
                                'next_login':'cr_login'})
                .assign(time_diff=lambda d: d.created_at - d.cr_created_at)
                [event_general+['tag_name', 'release_node_id',
                'cr_event_id','cr_event_type','cr_login','cr_repository','cr_created_at','cr_ref','time_diff']]
            )

        df_cr_rel = (
            df_events
            .drop_duplicates()
            [event_general+['tag_name','ref','release_node_id']]
            .sort_values(['login','repository','created_at'])
        
            .assign(prev_event_id=lambda d: d.event_id.shift(1))
            .assign(prev_event=lambda d: d.event_type.shift(1))
            .assign(prev_login=lambda d: d.login.shift(1))
            .assign(prev_repository=lambda d: d.repository.shift(1))
            .assign(prev_ref=lambda d: d.ref.shift(1))
            .assign(prev_event_created_at=lambda d: d.created_at.shift(1))

            .assign(cr_event_type=lambda d: 
                    np.where(((d.event_type == "ReleaseEvent") & (d.prev_event == "CreateEvent") & 
                            (d.login == d.prev_login) & (d.repository == d.prev_repository) &
                            (d.tag_name == d.prev_ref)),
                            d.prev_event, np.nan))
            .query('event_type == "ReleaseEvent" and cr_event_type == "CreateEvent"')
        )
        if(df_cr_rel.shape[0]>0):
            df_cr_rel = (
                df_cr_rel
                .rename(columns={'prev_event_created_at':'cr_created_at',
                                'prev_ref':'cr_ref',
                                'prev_event_id':'cr_event_id', 
                                'prev_repository':'cr_repository',
                                'prev_login':'cr_login'})

                .assign(time_diff=lambda d: d.created_at - d.cr_created_at)
                [event_general+['release_node_id',
                'cr_event_id','cr_event_type','cr_login','cr_repository','cr_created_at','cr_ref','time_diff']]
            )
        df_release_with_create = pd.concat([df_rel_cr, df_cr_rel]).drop_duplicates('event_id')

        if(df_release_with_create.shape[0]>0):
            df_release_with_create=df_release_with_create[(df_release_with_create['time_diff'] <= UPPER_TIME_THRESHOLD) & 
                                                        (df_release_with_create['time_diff'] >= LOWER_TIME_THRESHOLD)]
        
            list_event_id_covered.extend(df_release_with_create['event_id'].to_list())
            list_event_id_covered.extend(df_release_with_create['cr_event_id'].to_list())
        
            df_release_with_create_proc = (
                df_release_with_create
                .rename(columns={'login': 'contributor', 
                                'created_at': 'date'})
                .assign(activity='Publishing a release')
                .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
                [general+['release_node_id']]
                .drop_duplicates()
                .sort_values('date')
            )
        
            df_all_activities = pd.concat([df_all_activities, df_release_with_create_proc.drop_duplicates()[general]])

    '''
    ReleaseEvent that are made without creating a new tag
    '''
    df_release_without_create = (
        df_events
        .query('event_type == "ReleaseEvent" and event_id not in @list_event_id_covered')
        [event_general+['release_node_id']]
        .sort_values(['login','repository','created_at'])
    )

    if(df_release_without_create.shape[0]>0):
        list_event_id_covered.extend(df_release_without_create['event_id'].to_list())
    
        df_release_without_create_proc = (
            df_release_without_create
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date',
                             'release_node_id': 'GH_node'})
            [['contributor','repository','date','GH_node']]
            .assign(activity='Publishing a release')
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .drop_duplicates()
            .sort_values('date')
        )
    
        df_release_without_create_proc = df_release_without_create_proc.rename(columns={'GH_node':'release_GH_node'})
        df_all_activities = pd.concat([df_all_activities, df_release_without_create_proc.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def CreatingTag(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Creating tag: Get the events based on CreateEvent and ref_type as tag that were not covered as part of release activity
    '''
    create_tag = (
        df_events
        [event_general]
        .assign(activity = 'Creating tag')
        .rename(columns={'login':'contributor',
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(create_tag['event_id'].to_list())

    df_all_activities = merge_misc_related(df_all_activities, create_tag)

    return df_all_activities, list_event_id_covered

def DeletingTag(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Deleting tag: Filter data based on DeleteEvent and ref_type as tag
    '''
    delete_tag = (
        df_events
        [event_general]
        .assign(activity = 'Deleting tag')
        .rename(columns={'login':'contributor',
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(delete_tag['event_id'].to_list())

    df_all_activities = merge_misc_related(df_all_activities, delete_tag)

    return df_all_activities, list_event_id_covered

def DeletingBranch(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Deleting branch: Filter data based on DeleteEvent and ref_type as branch
    '''
    delete_branch = (
        df_events
        [event_general]
        .assign(activity = 'Deleting branch')
        .rename(columns={'login':'contributor',
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(delete_branch['event_id'].to_list())

    df_all_activities = merge_misc_related(df_all_activities, delete_branch)

    return df_all_activities, list_event_id_covered

def MakingRepositoryPublic(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Making repository public: Filter data based on PublicEvent
    '''
    public_event = (
        df_events
        [event_general]
        .assign(activity = 'Making repository public')
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(public_event['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities, public_event.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def AddingCollaborator(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Adding collaborator to repository: Filter data based on MemberEvent
    '''
    member_event = (
        df_events
        [event_general]
        .assign(activity = 'Adding collaborator to repository')
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(member_event['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities, member_event.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def ForkingRepository(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Forking a repository: Filter data based on ForkEvent
    '''
    forking_repository = (
        df_events
        [event_general]
        .assign(activity = 'Forking repository')
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(forking_repository['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities, forking_repository.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def StarringRepository(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Starring a repository: Filter data based on WatchEvent
    '''
    starring_repository = (
        df_events
        [event_general]
        .assign(activity = 'Starring repository')
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(starring_repository['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities, starring_repository.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def EditingWikiPage(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Editing a wiki page: Filter events based on GollumEvent
    '''
    df_wiki_page = (
        df_events
        [event_general]
        .rename(columns={'login':'contributor', 
                         'created_at':'date'})
        .assign(activity = 'Editing wiki page')
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(df_wiki_page['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities,df_wiki_page.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def merge_issue_related(df_all,df):
    '''
    args: df_all - DataFrame of all activities
          df - DataFrame of issue related activities

    return: df_all - DataFrame with all the activities (including issue related activities)

    method: Get the dataframe that has all the activities, append the activity fields corresponding to 
    issue and return dataframe with all activities
    
    '''
    df_all = pd.concat([df_all,df.drop_duplicates()[general]])

    return(df_all)

def TransferingIssue(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Transferring an issue:
    Issue is tranferred if
    1. action is "opened" with some timestamp in issue_closed_at field - Issue transferred after it is closed
    2. action is "opened" without any timestamp in issue_closed_at, but number of comments > 0 - Issue is transferred while it is open
    '''
    
    df_transferring_issue = (
        df_events
        [event_general+['issue_node_id']]
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(activity = 'Transferring issue')
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(df_transferring_issue['event_id'].to_list())

    df_all_activities = merge_issue_related(df_all_activities,df_transferring_issue)

    return df_all_activities, list_event_id_covered

def OpeningIssue(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Opening issue: If an issue with action opened is not covered in transferred issue then it is new
    '''
    df_opening_issue = (
        df_events
        [event_general+['issue_node_id']]
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .assign(activity='Opening issue')
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(df_opening_issue['event_id'].to_list())

    df_all_activities = merge_issue_related(df_all_activities,df_opening_issue)

    return df_all_activities, list_event_id_covered

def ClosingIssue(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Closing issue: 
    1. Issue is closed with IssueCommentEvent if both the events occur within 2 seconds
    2. Issue is close without a comment
    '''
    df_closing_issue_or_PR_comment = (
        df_events
        .drop_duplicates()
        [event_general+['issue_number','state','issue_node_id']]
        .sort_values(['login','repository','created_at'])
    )

    df_closing_issue_and_comment_1 = df_closing_issue_or_PR_comment[df_closing_issue_or_PR_comment['issue_number'].notnull()]

    df_closing_issue_before_comment = (
        df_closing_issue_and_comment_1
        .assign(next_event_id=lambda d: d.event_id.shift(-1))
        .assign(next_event=lambda d: d.event_type.shift(-1))
        .assign(next_login=lambda d: d.login.shift(-1))
        .assign(next_repository=lambda d: d.repository.shift(-1))
        .assign(next_issue_number=lambda d: d.issue_number.shift(-1))
        .assign(next_issue_state=lambda d: d.state.shift(-1))
        .assign(next_event_created_at=lambda d: d.created_at.shift(-1))
        .assign(comm_event_type=lambda d: 
                np.where(((d.event_type == "IssuesEvent") & (d.next_event == "IssueCommentEvent") & 
                          (d.login == d.next_login) & (d.repository == d.next_repository) &
                          (d.issue_number == d.next_issue_number) & (d.state == d.next_issue_state)), 
                         d.next_event, np.nan))
        .query('event_type == "IssuesEvent" and comm_event_type == "IssueCommentEvent"')
    )
    if(df_closing_issue_before_comment.shape[0]>0):
        df_closing_issue_before_comment = (
            df_closing_issue_before_comment
            .rename(columns={'next_event_created_at':'comm_created_at','next_repository':'comm_repository', 
                             'next_login':'comm_login', 'next_event_id':'comm_event_id'})
            .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
            [event_general+['issue_node_id', 'comm_event_id','comm_event_type','comm_login','comm_repository',
              'time_diff']]
        )

    df_closing_issue_after_comment = (
        df_closing_issue_and_comment_1
        .assign(prev_event_id=lambda d: d.event_id.shift(1))
        .assign(prev_event=lambda d: d.event_type.shift(1))
        .assign(prev_login=lambda d: d.login.shift(1))
        .assign(prev_repository=lambda d: d.repository.shift(1))
        .assign(prev_issue_number=lambda d: d.issue_number.shift(1))
        .assign(prev_issue_state=lambda d: d.state.shift(1))
        .assign(prev_event_created_at=lambda d: d.created_at.shift(1))
        .assign(comm_event_type=lambda d:
                np.where(((d.event_type == "IssuesEvent") & (d.prev_event == "IssueCommentEvent") & 
                          (d.login == d.prev_login) & (d.repository == d.prev_repository) &
                          (d.issue_number == d.prev_issue_number) & (d.state == d.prev_issue_state)), 
                         d.prev_event, np.nan))
        .query('event_type == "IssuesEvent" and comm_event_type == "IssueCommentEvent"')
    )
    if(df_closing_issue_after_comment.shape[0]>0):
        df_closing_issue_after_comment = (
            df_closing_issue_after_comment
            .rename(columns={'prev_event_created_at':'comm_created_at','prev_repository':'comm_repository', 
                             'prev_login':'comm_login', 'prev_event_id':'comm_event_id'})
            .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
    
            [event_general+['issue_node_id',
              'comm_event_id','comm_event_type','comm_login','comm_repository',
              'time_diff']]
        )

    df_closing_issue_with_comment = pd.concat([df_closing_issue_before_comment, df_closing_issue_after_comment]).drop_duplicates()

    if(df_closing_issue_with_comment.shape[0]>0):

        df_closing_issue_with_comment=df_closing_issue_with_comment[(df_closing_issue_with_comment['time_diff'] <= UPPER_TIME_THRESHOLD) & 
                                                                        (df_closing_issue_with_comment['time_diff'] >= LOWER_TIME_THRESHOLD)]
    
        list_event_id_covered.extend(df_closing_issue_with_comment['event_id'].to_list())
        list_event_id_covered.extend(df_closing_issue_with_comment['comm_event_id'].to_list())
    
        df_closing_issue_with_comment_proc = (
            df_closing_issue_with_comment
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Closing issue')
            [general+['issue_node_id']]
            .drop_duplicates()
            .sort_values('date')
        )
        
        df_all_activities = merge_issue_related(df_all_activities,df_closing_issue_with_comment_proc)

    '''
    Obtain the closed issue events that did not invovle any commeting activity while closing
    '''
    df_closing_issue_without_comment= (
        df_events
        .query('event_type == "IssuesEvent" and action == "closed" and event_id not in @list_event_id_covered')
        [event_general+['issue_closed_at','issue_node_id']]
    )
    if(df_closing_issue_without_comment.shape[0]>0):

        list_event_id_covered.extend(df_closing_issue_without_comment['event_id'].to_list())
    
        df_closing_issue_without_comment_proc = (
            df_closing_issue_without_comment
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(closed_at=lambda d: d.issue_closed_at.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Closing issue')
            [general + ['issue_node_id','closed_at']]
            .drop_duplicates()
        )
    
        df_all_activities = merge_issue_related(df_all_activities,df_closing_issue_without_comment_proc)

    return df_all_activities, list_event_id_covered

def ReopeningIssue(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations
    
    Reopening an issue: 
    1. Issue is reopened with IssueCommentEvent if both the events occur within 2 seconds
    2. Issue is reopened without any comment.
    '''

    df_reopening_issue_or_PR_comment = (
        df_events
        .drop_duplicates()
        [event_general+['issue_number','issue_node_id']]
        .sort_values(['login','repository','created_at'])
    )

    df_reopening_issue_and_comment_1 = df_reopening_issue_or_PR_comment[df_reopening_issue_or_PR_comment['issue_number'].notnull()]

    df_reopening_issue_before_comment = (
        df_reopening_issue_and_comment_1
        .assign(next_event_id=lambda d: d.event_id.shift(-1))
        .assign(next_event=lambda d: d.event_type.shift(-1))
        .assign(next_login=lambda d: d.login.shift(-1))
        .assign(next_repository=lambda d: d.repository.shift(-1))
        .assign(next_issue_number=lambda d: d.issue_number.shift(-1))
        .assign(next_event_created_at=lambda d: d.created_at.shift(-1))
        .assign(comm_event_type=lambda d: 
                np.where(((d.event_type == "IssuesEvent") & (d.next_event == "IssueCommentEvent") & 
                          (d.login == d.next_login) & (d.repository == d.next_repository) &
                          (d.issue_number == d.next_issue_number)), 
                         d.next_event, np.nan))
        .query('event_type == "IssuesEvent" and comm_event_type == "IssueCommentEvent"')
    )

    if(df_reopening_issue_before_comment.shape[0]>0):
        df_reopening_issue_before_comment = (
            df_reopening_issue_before_comment
            .rename(columns={'next_event_created_at':'comm_created_at',
                             'next_repository':'comm_repository', 'next_login':'comm_login', 
                             'next_event_id':'comm_event_id' })
            .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
            [event_general+['issue_node_id',
              'comm_event_id','comm_event_type','comm_login','comm_repository','comm_created_at',
              'time_diff']]
        )

    df_reopening_issue_after_comment = (
        df_reopening_issue_and_comment_1
        .assign(prev_event_id=lambda d: d.event_id.shift(1))
        .assign(prev_event=lambda d: d.event_type.shift(1))
        .assign(prev_login=lambda d: d.login.shift(1))
        .assign(prev_repository=lambda d: d.repository.shift(1))
        .assign(prev_issue_number=lambda d: d.issue_number.shift(1))
        .assign(prev_event_created_at=lambda d: d.created_at.shift(1))
        .assign(comm_event_type=lambda d:
                np.where(((d.event_type == "IssuesEvent") & (d.prev_event == "IssueCommentEvent") & 
                          (d.login == d.prev_login) & (d.repository == d.prev_repository) &
                          (d.issue_number == d.prev_issue_number)), 
                         d.prev_event, np.nan))
        .query('event_type == "IssuesEvent" and comm_event_type == "IssueCommentEvent"')
        .rename(columns={'prev_event_created_at':'comm_created_at',
                         'prev_repository':'comm_repository', 'prev_login':'comm_login', 
                         'prev_event_id':'comm_event_id' })
    )

    if(df_reopening_issue_after_comment.shape[0]>0):
        df_reopening_issue_after_comment = (
            df_reopening_issue_after_comment
            .rename(columns={'prev_event_created_at':'comm_created_at',
                         'prev_repository':'comm_repository', 'prev_login':'comm_login', 
                         'prev_event_id':'comm_event_id' })
            .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
    
            [event_general+['issue_node_id',
              'comm_event_id','comm_event_type','comm_login','comm_repository','comm_created_at',
              'time_diff']]
        )

    df_reopening_issue_with_comment = pd.concat([df_reopening_issue_before_comment, df_reopening_issue_after_comment]).drop_duplicates()

    if(df_reopening_issue_with_comment.shape[0]>0):

        df_reopening_issue_with_comment = df_reopening_issue_with_comment[(df_reopening_issue_with_comment['time_diff'] <= UPPER_TIME_THRESHOLD) & 
                                                                        (df_reopening_issue_with_comment['time_diff'] >= LOWER_TIME_THRESHOLD)]
        list_event_id_covered.extend(df_reopening_issue_with_comment['event_id'].to_list())
        list_event_id_covered.extend(df_reopening_issue_with_comment['comm_event_id'].to_list())
    
        df_reopening_issue_with_comment_proc = (
            df_reopening_issue_with_comment
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Reopening issue')
            [general + ['issue_node_id']]
            .drop_duplicates()
            .sort_values('date')
        )
        df_all_activities = merge_issue_related(df_all_activities,df_reopening_issue_with_comment_proc)

    '''
    Obtain the reopenend issue events that did not invovle any commeting activity while closing
    '''
    df_reopening_issue_without_comment= (
        df_events
        .query('event_type == "IssuesEvent" and action == "reopened" and event_id not in @list_event_id_covered')
        [event_general+['issue_node_id']]
    )

    if(df_reopening_issue_without_comment.shape[0]>0):

        list_event_id_covered.extend(df_reopening_issue_without_comment['event_id'].to_list())
    
        df_reopening_issue_without_comment_proc = (
            df_reopening_issue_without_comment
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Reopening issue')
            [general + ['issue_node_id']]
            .drop_duplicates()
        )
    
        df_all_activities = merge_issue_related(df_all_activities,df_reopening_issue_without_comment_proc)

    return df_all_activities, list_event_id_covered

def CommentingIssue(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations
    
    Commenting in issue: Filter the events based on IssueCommentEvent, where an issue_number exists in html url
    '''
    df_issue_commenting = (
        df_events[df_events['issue_number'].notnull()]
        [event_general+['comment_node_id']]
        .sort_values(['login','repository','created_at'])
        .rename(columns={'login': 'contributor',
                         'created_at': 'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .assign(activity = "Commenting issue")
        .drop_duplicates()
        .sort_values('date')
    )
    
    list_event_id_covered.extend(df_issue_commenting['event_id'].to_list())

    df_all_activities = merge_issue_related(df_all_activities,df_issue_commenting)

    return df_all_activities, list_event_id_covered

def merge_pr_related(df_all, df):
    '''
    args: df_all - DataFrame of all activities
          df - DataFrame of pr related activities

    return: df_all - DataFrame with all the activities (including pr related activities)

    method: Get the dataframe that has all the activities, append the activities corresponding to pr and return 
    dataframe with all activities
    '''
    df_all = pd.concat([df_all,df.drop_duplicates()[general]])

    return(df_all)

def OpeningPullRequest(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations
    
    Opening pull request: If a PullRequestEvent with action as opened.
    '''
    df_opening_pullrequest = (
        df_events
        [event_general+['PR_node_id']]
        .rename(columns={'login':'contributor', 'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .assign(activity='Opening pull request')
        .assign(pr_node_id=lambda d: d.PR_node_id)
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(df_opening_pullrequest['event_id'].to_list())

    df_all_activities = merge_pr_related(df_all_activities,df_opening_pullrequest)

    return df_all_activities, list_event_id_covered

def ReopeningPullRequest(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Reopening a pull request:
    1. Pull request is reopened with IssueCommentEvent if both the events occur within 2 seconds
    2. Pull request is reopened without any comment.
    '''

    df_reopening_issue_or_PR_comment = (
        df_events
        .drop_duplicates()
        [event_general+['PR_number','PR_node_id']]
        .sort_values(['login','repository','created_at'])
    )

    df_reopening_pr_and_comment_1 = df_reopening_issue_or_PR_comment[df_reopening_issue_or_PR_comment['PR_number'].notnull()]

    df_reopening_pr_before_comment = (
        df_reopening_pr_and_comment_1
        .assign(next_event_id=lambda d: d.event_id.shift(-1))
        .assign(next_event=lambda d: d.event_type.shift(-1))
        .assign(next_login=lambda d: d.login.shift(-1))
        .assign(next_repository=lambda d: d.repository.shift(-1))
        .assign(next_pr_number=lambda d: d.PR_number.shift(-1))
        .assign(next_event_created_at=lambda d: d.created_at.shift(-1))
        .assign(comm_event_type=lambda d: 
                np.where(((d.event_type == "PullRequestEvent") & (d.next_event == "IssueCommentEvent") & 
                          (d.login == d.next_login) & (d.repository == d.next_repository) &
                          (d.PR_number == d.next_pr_number)), 
                         d.next_event, np.nan))
        .query('event_type == "PullRequestEvent" and comm_event_type == "IssueCommentEvent"')
    )
    if(df_reopening_pr_before_comment.shape[0]>0):
        df_reopening_pr_before_comment = (
            df_reopening_pr_before_comment
            .rename(columns={'next_event_created_at':'comm_created_at', 
                             'next_repository':'comm_repository', 'next_login':'comm_login', 
                             'next_event_id':'comm_event_id'})
            .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
            [event_general+['PR_node_id',
              'comm_event_id','comm_event_type','comm_login','comm_repository','comm_created_at',
              'time_diff']]
        )

    df_reopening_pr_after_comment = (
        df_reopening_pr_and_comment_1
        .assign(prev_event_id=lambda d: d.event_id.shift(1))
        .assign(prev_event=lambda d: d.event_type.shift(1))
        .assign(prev_login=lambda d: d.login.shift(1))
        .assign(prev_repository=lambda d: d.repository.shift(1))
        .assign(prev_pr_number=lambda d: d.PR_number.shift(1))
        .assign(prev_event_created_at=lambda d: d.created_at.shift(1))
        .assign(comm_event_type=lambda d:
                np.where(((d.event_type == "PullRequestEvent") & (d.prev_event == "IssueCommentEvent") & 
                          (d.login == d.prev_login) & (d.repository == d.prev_repository) &
                          (d.PR_number == d.prev_pr_number)), 
                         d.prev_event, np.nan))
        .query('event_type == "PullRequestEvent" and comm_event_type == "IssueCommentEvent"')
    )
    if(df_reopening_pr_after_comment.shape[0]>0):
        df_reopening_pr_after_comment = (
            df_reopening_pr_after_comment
            .rename(columns={'prev_event_created_at':'comm_created_at',
                             'prev_repository':'comm_repository', 'prev_login':'comm_login', 
                             'prev_event_id':'comm_event_id'})
            .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
    
            [event_general+['PR_node_id',
              'comm_event_id','comm_event_type','comm_login','comm_repository','comm_created_at',
              'time_diff']]
        )

    df_reopening_pr_with_comment = pd.concat([df_reopening_pr_before_comment, df_reopening_pr_after_comment]).drop_duplicates()

    '''
    Save the event_ids that are processed in the PullRequestEvent and its corresponding IssueCommentEvent
    Change the field names and create the dataframe in the required format to be saved in .json
    text_length>0 = comment and close is done
    text_length=0 closed without any comment
    '''
    if(df_reopening_pr_with_comment.shape[0]>0):
        
        df_reopening_pr_with_comment = df_reopening_pr_with_comment[(df_reopening_pr_with_comment['time_diff'] <= UPPER_TIME_THRESHOLD) & 
                                                                    (df_reopening_pr_with_comment['time_diff'] >= LOWER_TIME_THRESHOLD)]
        list_event_id_covered.extend(df_reopening_pr_with_comment['event_id'].to_list())
        list_event_id_covered.extend(df_reopening_pr_with_comment['comm_event_id'].to_list())
    
        df_reopening_pr_with_comment_proc = (
            df_reopening_pr_with_comment
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Reopening pull request')
            .assign(pr_node_id=lambda d: d.PR_node_id)
            [general + ['pr_node_id']]
            .drop_duplicates()
            .sort_values('date')
        )

        df_all_activities = merge_pr_related(df_all_activities,df_reopening_pr_with_comment_proc)

    '''
    Obtain the reopenend pull request events that did not invovle any commeting activity while closing
    '''

    df_reopening_pr_without_comment= (
        df_events
        .query('event_type == "PullRequestEvent" and action == "reopened" and event_id not in @list_event_id_covered')
        [event_general+['PR_node_id']]
    )
    if(df_reopening_pr_without_comment.shape[0]>0):
        df_reopening_pr_without_comment = (
            df_reopening_pr_without_comment
            .rename(columns={'login':'contributor', 'created_at':'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Reopening pull request')
            .assign(pr_node_id=lambda d: d.PR_node_id)
            .drop_duplicates()
            .sort_values('date')
        )

        list_event_id_covered.extend(df_reopening_pr_without_comment['event_id'].to_list())
    
        df_all_activities = merge_pr_related(df_all_activities,df_reopening_pr_without_comment)

    return df_all_activities, list_event_id_covered

def ClosingPullRequest(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations
    
    Closing PR
    1. Closing PR and merging it (cannot comment) with a push that happened within 2 seconds 
    2. Closing PR and merging it, no push detected - PR is closed, but its corresponding push event (same sha) has happened long back, no push for some PRs
    3. Closing PR and rejecting it, with IssueCommentEvent that happened within 2 seconds
    4. Closing PR and rejecting it, without comment
    '''

    df_pr_merge = (
        df_events
        .query('event_type == "PullRequestEvent" and action == "closed" and merged == True')
        .dropna(axis=1, how='all')
        .drop_duplicates('event_id')
    )
    df_push_events = (
        df_events
        .query('event_type == "PushEvent"')
        .dropna(axis=1, how='all')
        .drop_duplicates('event_id')
    )
    if(df_pr_merge.shape[0]>0 and df_push_events.shape[0]>0):
        df_pr_merge_push = pd.merge(df_pr_merge, df_push_events, left_on=['login','repository'], right_on=['login','repository'])
    
        df_pr_merge_push = (
            df_pr_merge_push
            [['event_id_x','event_type_x','login','repository','created_at_x','PR_number',
              'PR_node_id',
              'event_id_y','event_type_y','created_at_y']]
            .rename(columns = {'event_id_x':'pr_event_id',
                               'event_type_x':'pr_event_type',
                               'login':'contributor',
                               'created_at_x':'date',
                               'PR_number':'pr_number',
                               'event_id_y':'push_event_id',
                               'event_type_y':'push_events_type',
                               'created_at_y':'push_date'})
            .assign(time_diff = lambda d: d.date - d.push_date)
        )
    
        pr_close_with_push = df_pr_merge_push[(df_pr_merge_push['time_diff'] <= UPPER_TIME_THRESHOLD) &
                                              (df_pr_merge_push['time_diff'] >= LOWER_TIME_THRESHOLD)]
        list_event_id_covered.extend(pr_close_with_push['pr_event_id'].to_list())
        list_event_id_covered.extend(pr_close_with_push['push_event_id'].to_list())

        df_pr_close_with_push_proc = (
            pr_close_with_push
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Closing pull request')
            .assign(pr_node_id=lambda d: d.PR_node_id)
            .assign(comment_node_id=None)
            [general + ['pr_node_id','comment_node_id']]
            .drop_duplicates()
            .sort_values('date')
        )

        df_all_activities = merge_pr_related(df_all_activities,df_pr_close_with_push_proc)

    '''
    Obtain PR events that are closed and merged, but dont have an associated push within the threshold
    '''
    df_pr_close_merge_no_push= (
        df_events
        .query('event_type == "PullRequestEvent" and action == "closed" and merged == True and event_id not in @list_event_id_covered')
        [event_general+['PR_node_id']]
        .rename(columns = {'event_id':'pr_event_id',
                           'login':'contributor',
                           'created_at':'date'})
    )

    if(df_pr_close_merge_no_push.shape[0]>0):

        list_event_id_covered.extend(df_pr_close_merge_no_push['pr_event_id'].to_list())
    
        df_pr_close_merge_no_push_proc = (
            df_pr_close_merge_no_push
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Closing pull request')
            .assign(pr_node_id=lambda d: d.PR_node_id)
            .assign(comment_node_id=None)
            [general + ['pr_node_id','comment_node_id']]
            .drop_duplicates()
            .sort_values('date')
        )

        df_all_activities = merge_pr_related(df_all_activities,df_pr_close_merge_no_push_proc)

    '''
    PR merging and closing does not invovlve any comment, but PR rejecting and closing has comment (IssueCommentEvent) functionality.
    So, identify the PR commeting activity associated with PR closing (reject) event

    PullRequestEvent and IssueCommentEvent (PR comment) occur consecutively (order can differ) if they are done at the same time.
    So, we have 2 dfs - df_closing_pr_before_comment and df_closing_pr_after_comment
    Commenting under PR is reported under IssueCommentEvent, so we need to filter and get the events corresponding to commeting under PRs.

    Then we replace the values with NaN or NaT where ever login, repo and pr_number are different between PullRequestEvent and IssueCommentEvent
    merge both the df's
    '''

    if(df_events.event_type.isin(['PullRequestEvent']).any() and  df_events.event_type.isin(['IssueCommentEvent']).any()):
        df_closing_issue_or_PR_comment = (
            df_events
            .query('(event_type == "PullRequestEvent" and action == "closed" and merged == False) or event_type == "IssueCommentEvent"')
            .drop_duplicates()
            [event_general+['PR_number','state','PR_node_id','comment_node_id']]
            .sort_values(['login','repository','created_at'])
        )

        df_closing_pr_and_comment_1 = df_closing_issue_or_PR_comment[df_closing_issue_or_PR_comment['PR_number'].notnull()]

        df_closing_pr_before_comment = (
            df_closing_pr_and_comment_1
            .assign(next_event_id=lambda d: d.event_id.shift(-1))
            .assign(next_event=lambda d: d.event_type.shift(-1))
            .assign(next_login=lambda d: d.login.shift(-1))
            .assign(next_repository=lambda d: d.repository.shift(-1))
            .assign(next_pr_number=lambda d: d.PR_number.shift(-1))
            .assign(next_pr_state=lambda d: d.state.shift(-1))
            .assign(next_event_created_at=lambda d: d.created_at.shift(-1))
            .assign(next_event_node_id=lambda d: d.comment_node_id.shift(-1))

            .assign(comm_event_type=lambda d: 
                    np.where(((d.event_type == "PullRequestEvent") & (d.next_event == "IssueCommentEvent") & 
                            (d.login == d.next_login) & (d.repository == d.next_repository) &
                            (d.PR_number == d.next_pr_number) & (d.state == d.next_pr_state)), 
                            d.next_event, np.nan))

            .query('event_type == "PullRequestEvent" and comm_event_type == "IssueCommentEvent"')
        )
        if(df_closing_pr_before_comment.shape[0]>0):
            df_closing_pr_before_comment = (
                df_closing_pr_before_comment
                .rename(columns={'next_event_created_at':'comm_created_at', 
                                'next_repository':'comm_repository', 'next_login':'comm_login', 
                                'next_event_id':'comm_event_id', 
                                'next_event_node_id':'comm_comment_node_id'})
                .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
                [event_general+['PR_node_id',
                'comm_event_id','comm_event_type','comm_login','comm_repository',
                'time_diff','comm_comment_node_id']]
            )

        df_closing_pr_after_comment = (
            df_closing_pr_and_comment_1
            .assign(prev_event_id=lambda d: d.event_id.shift(1))
            .assign(prev_event=lambda d: d.event_type.shift(1))
            .assign(prev_login=lambda d: d.login.shift(1))
            .assign(prev_repository=lambda d: d.repository.shift(1))
            .assign(prev_pr_number=lambda d: d.PR_number.shift(1))
            .assign(prev_pr_state=lambda d: d.state.shift(1))
            .assign(prev_event_created_at=lambda d: d.created_at.shift(1))
            .assign(prev_event_node_id=lambda d: d.comment_node_id.shift(1))

            .assign(comm_event_type=lambda d:
                    np.where(((d.event_type == "PullRequestEvent") & (d.prev_event == "IssueCommentEvent") & 
                            (d.login == d.prev_login) & (d.repository == d.prev_repository) &
                            (d.PR_number == d.prev_pr_number) & (d.state == d.prev_pr_state)), 
                            d.prev_event, np.nan))
            .query('event_type == "PullRequestEvent" and comm_event_type == "IssueCommentEvent"')
        )
        if(df_closing_pr_after_comment.shape[0]>0):
            df_closing_pr_after_comment = (
                df_closing_pr_after_comment
                .rename(columns={'prev_event_created_at':'comm_created_at', 
                                'prev_repository':'comm_repository', 'prev_login':'comm_login', 
                                'prev_event_id':'comm_event_id', 
                                'prev_event_node_id':'comm_comment_node_id'})
                .assign(time_diff=lambda d: d.created_at - d.comm_created_at)
                [event_general+['PR_node_id',
                'comm_event_id','comm_event_type','comm_login','comm_repository',
                'time_diff','comm_comment_node_id']]
            )

        df_closing_pr_with_comment = pd.concat([df_closing_pr_before_comment, df_closing_pr_after_comment]).drop_duplicates()

        if(df_closing_pr_with_comment.shape[0]>0):

            list_event_id_covered.extend(df_closing_pr_with_comment['event_id'].to_list())
            list_event_id_covered.extend(df_closing_pr_with_comment['comm_event_id'].to_list())
        
            df_closing_pr_with_comment_proc = (
                df_closing_pr_with_comment
                .rename(columns={'login': 'contributor', 
                                'created_at': 'date'})
                .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
                .assign(activity='Closing pull request')
                .assign(pr_node_id=lambda d: d.PR_node_id)
                .assign(comment_node_id = lambda d: d.comm_comment_node_id)
                [general + ['pr_node_id','comment_node_id']]
                .drop_duplicates()
                .sort_values('date')
            )

            df_all_activities = merge_pr_related(df_all_activities,df_closing_pr_with_comment_proc)

    df_pr_close_no_merge_without_comment = (
        df_events
        .query('event_type == "PullRequestEvent" and action == "closed" and merged == False and \
                event_id not in @list_event_id_covered')
        [event_general+['PR_node_id']]
    )

    if(df_pr_close_no_merge_without_comment.shape[0]>0):

        list_event_id_covered.extend(df_pr_close_no_merge_without_comment['event_id'].to_list())
    
        pr_close_without_comment = []
        pr_close_without_comment.extend(df_pr_close_no_merge_without_comment['event_id'].to_list())
    
        df_pr_close_no_merge_without_comment_proc = (
            df_pr_close_no_merge_without_comment
            .rename(columns={'login': 'contributor', 
                             'created_at': 'date'})
            .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
            .assign(activity='Closing pull request')
            .assign(pr_node_id=lambda d: d.PR_node_id)
            .assign(comment_node_id=None)
            [general + ['pr_node_id','comment_node_id']]
            .drop_duplicates()
            .sort_values('date')
        )
    
        df_all_activities = merge_pr_related(df_all_activities,df_pr_close_no_merge_without_comment_proc)

    return df_all_activities, list_event_id_covered

def CommentingPullRequest(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Commenting pull request: Filter the events based on IssueCommentEvent, where the PR_number field is not NA
    '''

    df_pr_commenting = (
        df_events
        [event_general+['comment_node_id']]
        .sort_values(['login','repository','created_at'])
        .rename(columns={'login': 'contributor',
                         'created_at': 'date',})
        .assign(activity = "Commenting pull request")
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )
    list_event_id_covered.extend(df_pr_commenting['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities,df_pr_commenting.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def CommentingPullRequestChanges(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Commenting pull request changes: Filter the events based on PullRequestReviewCommentEvent and 
                                     PullRequestReviewEvent with review_state as "commented"
    '''
    if(df_events.columns.isin(['comment_node_id']).any()):
        df_pr_review_commenting = (
            df_events
            [event_general+['comment_node_id']]
        )
    elif(df_events.columns.isin(['review_node_id']).any()):
        df_pr_review_commenting= (
            df_events
            [event_general+['review_node_id']]
        )
    df_pr_review_commenting = (
        df_pr_review_commenting
        .rename(columns={'login':'contributor', 
                         'created_at':'date'})
        .assign(activity = "Commenting pull request changes")
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
        )

    list_event_id_covered.extend(df_pr_review_commenting['event_id'].to_list())
    if(len(df_pr_review_commenting.query('event_type == "PullRequestReviewCommentEvent"')) > 0):
        df_pr_review_commenting = df_pr_review_commenting.query('event_type == "PullRequestReviewCommentEvent"') #The PullRequestReviewEvent with review_state as commented 
                    #will have an associated PullRequestReviewCommentEvent for comment, so have to capture that as an activity and not the PullRequestReviewEvent as such.
                    #Sometimes it may not be reported by GitHub Events API, in that case report the PullRequestReviewEvent itself.

    df_all_activities = pd.concat([df_all_activities,df_pr_review_commenting.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def ReviewingCode(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Reviewing code: Filter the events based on PullRequestReviewEvent with review_state as 
                    "approved"/"dismissed"/"changes_requested"
    '''

    df_pr_review_code = (
        df_events
        [event_general+['review_node_id']]
        .assign(activity = "Reviewing code")
        .rename(columns={'login':'contributor',
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(df_pr_review_code['event_id'].to_list())

    df_pr_review_code = df_pr_review_code.drop(['event_id'],axis=1).drop_duplicates()

    df_all_activities = pd.concat([df_all_activities,df_pr_review_code.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def CommentingCommits(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Commenting commits: Filter the events based on CommitCommentEvent
    '''

    df_commit_commenting = (
        df_events
        [event_general+['comment_node_id']]
        .assign(activity = "Commenting commit")
        .rename(columns={'login':'contributor',
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(df_commit_commenting['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities, df_commit_commenting.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def PushingCommits(df_events, list_event_id_covered, df_all_activities):
    '''
    args: df_events (DataFrame) - events
          list_event_id_covered (list) - a list of event id's that are covered in previous iterations
          df_all_activities (DataFrame) - DataFrame of all the previously identified activities for a contributor
    
    returns: df_all_activities (DataFrame) - Updated DataFrame of all activities that are identified for the contributor
             list_event_id_covered - Updated list of event id's that are covered in previous iterations

    Pushing commits: Filter the events based on PushEvent, remove the events that are already covered in pull request close event
    '''
    pushing_commits = (
        df_events
        [event_general+['push_id']]
        .assign(activity = "Pushing commits")
        .rename(columns={'login':'contributor', 
                         'created_at':'date'})
        .assign(date=lambda d: d.date.dt.tz_localize(tz='UTC').map(lambda x: x.isoformat()))
        .assign(GH_push_id=lambda d: d.push_id.astype('int64'))
        .drop_duplicates()
        .sort_values('date')
    )

    list_event_id_covered.extend(pushing_commits['event_id'].to_list())

    df_all_activities = pd.concat([df_all_activities, pushing_commits.drop_duplicates()[general]])

    return df_all_activities, list_event_id_covered

def activity_identification(df_events):
    '''
    args: df_events (DataFrame) - A DataFrame of contributor events
    
    returns: df_all_activities (DataFrame) - A DataFrame of contributor activities
    
    method:
    Get the events from DataFrame, identify the activities, and return it in DataFrame.
    '''

    '''
    Converting the timestamps to pandas datetime format for easy processing
    '''
    if(df_events.columns.isin(['PR_number']).any()):
        df_events = df_events.astype({'PR_number':'Int64'})
    if(df_events.columns.isin(['issue_number']).any()):
        df_events = df_events.astype({'issue_number':'Int64'})
    if(df_events.columns.isin(['issue_closed_at']).any()):
        df_events['issue_closed_at'] = pd.to_datetime(df_events.issue_closed_at, errors='coerce', format='%Y-%m-%dT%H:%M:%SZ').dt.tz_localize(None)
    df_events['created_at'] = pd.to_datetime(df_events.created_at, errors='coerce', format='%Y-%m-%dT%H:%M:%SZ').dt.tz_localize(None)
    
    df_events = df_events.astype({'event_id':'Int64'})
    df_events = df_events.sort_values('created_at')

    '''
    list_event_id_covered - event_ids that are already processed
    df_all_activities - DataFrame for all activities
    Invoke only the required activity functions based on events
    '''
    list_event_id_covered = []
    df_all_activities = pd.DataFrame()
    if(df_events.columns.isin(['ref_type']).any()):
        temp_df = df_events.query('event_type == "CreateEvent" and ref_type == "repository"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = CreatingRepository(temp_df, list_event_id_covered, df_all_activities)

        temp_df = df_events.query('event_type == "CreateEvent" and ref_type == "branch"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = CreateBranch(temp_df, list_event_id_covered, df_all_activities)
        
        if(df_events.columns.isin(['release_node_id']).any()):
            temp_df = df_events.query('event_type == "ReleaseEvent" or (event_type == "CreateEvent" and ref_type == "tag")')
            if(temp_df.shape[0]>0):
                df_all_activities, list_event_id_covered = PublishingRelease(temp_df, list_event_id_covered, df_all_activities)
    if(df_events.columns.isin(['release_node_id']).any() and ~df_events.columns.isin(['ref_type']).any()):
        temp_df = df_events.query('event_type == "ReleaseEvent"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = PublishingRelease(temp_df, list_event_id_covered, df_all_activities)
    
    if(df_events.columns.isin(['ref_type']).any()):
        temp_df = df_events.query('event_type == "CreateEvent" and ref_type == "tag" and event_id not in @list_event_id_covered')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = CreatingTag(temp_df, list_event_id_covered, df_all_activities)
        
        temp_df = df_events.query('event_type == "DeleteEvent" and ref_type == "tag"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = DeletingTag(temp_df, list_event_id_covered, df_all_activities)
        
        temp_df = df_events.query('event_type == "DeleteEvent" and ref_type == "branch"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = DeletingBranch(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "PublicEvent"')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = MakingRepositoryPublic(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "MemberEvent"')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = AddingCollaborator(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "ForkEvent"')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = ForkingRepository(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "WatchEvent"')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = StarringRepository(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "GollumEvent"')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = EditingWikiPage(temp_df, list_event_id_covered, df_all_activities)
    
    if(df_events.columns.isin(['action']).any()):
        if(df_events.columns.isin(['num_comments']).any() and df_events.columns.isin(['issue_closed_at']).any()):
            temp_df = (df_events[(df_events['event_type']=="IssuesEvent") & 
                                 (df_events['action']=="opened") & 
                                 ((df_events['num_comments']>0) | (df_events['issue_closed_at'].notnull()))]
                      )
            if(temp_df.shape[0]>0):
                df_all_activities, list_event_id_covered = TransferingIssue(temp_df, list_event_id_covered, df_all_activities)
        temp_df = df_events.query('event_type == "IssuesEvent" and action == "opened" and event_id not in @list_event_id_covered')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = OpeningIssue(temp_df, list_event_id_covered, df_all_activities)
    
        temp_df = df_events.query('(event_type == "IssuesEvent" and action == "closed") or event_type == "IssueCommentEvent"')
        temp_df = temp_df.dropna(axis=1, how='all')
        if(temp_df.shape[0]>0 and temp_df.columns.isin(['issue_node_id']).any() and temp_df.columns.isin(['issue_closed_at']).any()):
            df_all_activities, list_event_id_covered = ClosingIssue(temp_df, list_event_id_covered, df_all_activities)
    
        temp_df = df_events.query('((event_type == "IssuesEvent" and action == "reopened") or event_type == "IssueCommentEvent") \
        and event_id not in @list_event_id_covered')
        temp_df = temp_df.dropna(axis=1, how='all')
        if(temp_df.shape[0]>0 and temp_df.columns.isin(['issue_node_id']).any()):
            df_all_activities, list_event_id_covered = ReopeningIssue(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "IssueCommentEvent" and event_id not in @list_event_id_covered ')
    temp_df = temp_df.dropna(axis=1, how='all')
    if(temp_df.columns.isin(['issue_number']).any()):
        temp_df = temp_df[temp_df['issue_number'].notnull()]
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = CommentingIssue(temp_df, list_event_id_covered, df_all_activities)

    if(df_events.columns.isin(['action']).any()):
        temp_df = df_events.query('event_type == "PullRequestEvent" and action == "opened"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = OpeningPullRequest(temp_df, list_event_id_covered, df_all_activities)
    
        temp_df = df_events.query('((event_type == "PullRequestEvent" and action == "reopened") or event_type == "IssueCommentEvent") \
        and event_id not in @list_event_id_covered')
        temp_df = temp_df.dropna(axis=1, how='all')
        if(temp_df.shape[0]>0 and temp_df.columns.isin(['PR_node_id']).any()):
            df_all_activities, list_event_id_covered = ReopeningPullRequest(temp_df, list_event_id_covered, df_all_activities)
    
        temp_df = df_events.query('((event_type == "PullRequestEvent" and action == "closed") or \
        event_type == "PushEvent" or event_type == "IssueCommentEvent") and event_id not in @list_event_id_covered')
        temp_df = temp_df.dropna(axis=1, how='all')
        if(temp_df.shape[0]>0 and temp_df.columns.isin(['PR_node_id']).any() and temp_df.columns.isin(['merged']).any()):
            df_all_activities, list_event_id_covered = ClosingPullRequest(temp_df, list_event_id_covered, df_all_activities)
    
    if(df_events.columns.isin(['PR_number']).any()):
        temp_df = (df_events[(df_events['event_type'] == 'IssueCommentEvent') &
                             (df_events['PR_number'].notnull()) &  
                             (~df_events['event_id'].isin(list_event_id_covered))])
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = CommentingPullRequest(temp_df, list_event_id_covered, df_all_activities)

    if(df_events.columns.isin(['review_state']).any()):
        temp_df = df_events.query('(event_type == "PullRequestReviewCommentEvent") or \
        (event_type == "PullRequestReviewEvent" and review_state == "commented")')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = CommentingPullRequestChanges(temp_df, list_event_id_covered, df_all_activities)
    
        temp_df = df_events.query('event_type == "PullRequestReviewEvent" and review_state != "commented"')
        if(temp_df.shape[0]>0):
            df_all_activities, list_event_id_covered = ReviewingCode(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "CommitCommentEvent"')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = CommentingCommits(temp_df, list_event_id_covered, df_all_activities)
    
    temp_df = df_events.query('event_type == "PushEvent" and event_id not in @list_event_id_covered')
    if(temp_df.shape[0]>0):
        df_all_activities, list_event_id_covered = PushingCommits(temp_df, list_event_id_covered, df_all_activities)

    return(df_all_activities)