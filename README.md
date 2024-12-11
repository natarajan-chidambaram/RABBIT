[![](https://img.shields.io/github/v/release/natarajan-chidambaram/RABBIT?label=Latest%20Release)](https://github.com/natarajan-chidambaram/RABBIT/releases/latest)
[![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/natarajan-chidambaram/RABBIT/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/natarajan-chidambaram/RABBIT)

# RABBIT

![alt text](https://github.com/natarajan-chidambaram/rabbit/blob/main/logo.jpeg?raw=true)

RABBIT is a recursive acronym for "RABBIT is an Activity-Based Bot Identification Tool".
It is based on BIMBAS (stands for Bot Identification Model Based on Activity Sequences), a binary classification model to identify bot contributors based on their recent activities in GitHub.
RABBIT is quite efficient, being able to predict thousands of accounts per hour, without reaching GitHub's imposed hourly API rate limit of 5,000 queries per hour for authorised users.

The tool has been developed by Natarajan Chidambaram, a researcher at the [Software Engineering Lab](http://informatique.umons.ac.be/genlog/) of the [University of Mons](https://www.umons.ac.be) (Belgium) as part of his PhD research in the context of [DigitalWallonia4.AI research project ARIAC (grant number 2010235)](https://www.digitalwallonia.be/ia/) and [TRAIL](https://trail.ac/en/). 

This tool is developed as part of the research article titled: "A Bot Identification Model and Tool based on GitHub Activity Sequences" that is published at the Journal of Systems and Software, see [https://doi.org/10.1016/j.jss.2024.112287](https://doi.org/10.1016/j.jss.2024.112287).
**Citation**: Natarajan Chidambaram, Tom Mens, and Alexandre Decan. 2024. ***A Bot Identification Model and Tool based on GitHub Activity Sequences.*** Journal of Systems and Software, vol. 221, March 2025, doi: https://doi.org/10.1145/3643991.3644877.

## How it works
RABBIT accepts a GitHub contributor name (login name) and/or a text file of multiple login names (one name per line). It requires a GitHub API key if more than 15 queries are required to be made per hour.
First, the tool checks whether the login name corresponds to a valid existing GitHub contributor and returns **Invalid** otherwise. Then, based on a call to the GitHub Users API, if the login name does not correspond to the type "User" (e.g., GitHub App is reported as "Bot" and organization account as "Organization") the tool directly determines the type as provided by GitHub Users API without even querying their events.
For the contributors for which GitHub Users API provided their type as "User", BIMBAS will determine the type of contributor as **Bot**, **Human** or **Unknown** after the following steps.
The first step consists of extracting the latest public events performed by the contributor in GitHub, using one or more queries to the GitHub Events API.
If the number of events retrieved is less than the required threshold, the prediction will be **Unknown** due to a lack of data.
If enough events are available to determine the type of contributor, the second step converts the events into activities (belonging to 24 different activity types). The third step computes the contributor's behavioural features.
The fourth step executes **BIMBAS** and returns the type of contributor **Bot** or **Human** along with a confidence score between 0 and 1 (including both).

**Note about misclassifications.** RABBIT is based on a machine learning classification model (BIMBAS) that is trained and validated on a ground-truth dataset, and cannot reach a precision and recall of 100%. 
When running it on a set of GitHub contributors of your choice, it is therefore possible to have misclassifications (humans misclassified as bots, or vice versa). 
If you encounter such situations while running the tool, please inform us about it, so that we can strive to further improve the accuracy of the classification model. A known reason for the presence of misclassifications is a too limited number of activities available for the contributor.

## Installation
In order not to conflict with already installed packages on your machine, it is recommended to use a virtual environment to install RABBIT. You can create a _Python virtual environment_ and install and run the tool in this environment. You can use any virtual environment of your choice. Below are the steps to install and create a virtual environment with **virtualenv**.

Use the following command to install the virtual environment:
```
pip install virtualenv
```
Create a virtual environment in the folder where you want to place your files:
```
virtualenv <envname>
```
Start using the environment by:
```
source <envname>/bin/activate
```
After running this command your command line prompt will change to `(<envname>) ...` and now you can install RABBIT with the pip command.
When you are finished running the tool, you can quit the environment by:
```
deactivate
```
To install RABBIT, execute the following command:
```
pip install git+https://github.com/natarajan-chidambaram/RABBIT
```

Alternatively, `RABBIT` is available via [Nix](https://search.nixos.org/packages?channel=unstable&show=rabbit&from=0&size=50&sort=relevance&type=packages&query=rabbit).

## Usage
To execute **RABBIT** for many contributors (if more than 15 API queries are required per hour), you need to provide a *GitHub personal access token* (API key). You can follow the instructions [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) to obtain such a token.

You can execute the tool with all default parameters by running `rabbit <LOGIN_NAME>`. 

Here is the list of parameters:

`<LOGIN_NAME>`            **Any number of positional arguments specifying the login names of the contributors for which the type needs to be determined.**
> Example: $ rabbit natarajan-chidambaram tommens

`--input-file <path/to/loginnames.txt>`            **A text input file with the login names (one name per line) of the contributors for which the type needs to be determined.**
> Example: $ rabbit --input-file logins.txt

_Either the positional argument `<LOGIN_NAME>` or `--input-file` is mandatory. In case both are given, then the accounts given with `--input-file` will be processed after the accounts given as positional arguments have been processed._

`--key <APIKEY>` 			**GitHub personal access token (key) to extract events from the GitHub Events API.**    
_Note: APIKEY (--key) is mandatory if more than 15 queries are required to be made per hour_
> Example: $ rabbit --input-file logins.txt --key token

_You can obtain an access token as described earlier_

`--min-events <MIN_EVENTS>` 		**Minimum number of events that are required to determine the type of contributor.**
> Example: $ rabbit --input-file logins.txt --min-events 10

_The default minimum number of events is 5._

`--max-queries <NUM_QUERIES>` 		**Maximum number of queries that will be made to the GitHub Events API for each contributor. Reducing this value will lead to faster execution and less queries, at the expense of a reduced confidence in the results.**
> Example: $ rabbit --input-file logins.txt --queries 2

_The default number of queries is 3, allowed values are 1, 2 or 3._

`--min-confidence <MIN_CONFIDENCE>` 		**Minimum confidence on contributor type to stop further querying. If the desired minimum confidence is reached, no further API calls will be made for the given contributor.**
> Example: $ rabbit --input-file logins.txt --min-confidence 0.5

_The default minimum confidence is 1.0_

`--verbose`              		**Reports detailed information from the classification model such as the number of events, number of activities and values of the features that were used to determine the type of contributor.**
> Example: $ rabbit --input-file logins.txt --verbose

_The default value is False._

`--json <FILE_NAME.json>`                	**Saves the result in JSON format.**
> Example: $ rabbit --input-file logins.txt --json output.json

`--csv <FILE_NAME.csv>`                		**Saves the result in comma-separated values (CSV) format.**
> Example: $ rabbit --input-file logins.txt --csv types.csv

`--incremental`              		**Method of reporting the results.** _If provided, the result for the contributor will be reported as soon as its type is determined. If not provided, the results will be reported after determining the type of all provided contributors._
> Example: $ rabbit --input-file logins.txt --key token --incremental

_The default value is False._

## Examples of RABBIT output (for illustration purposes only)

**With positional arguments:**

GitHub 'User' accounts are classified as either Human or Bot using the classification model, and a confidence score between 0.0 and 1.0 is computed.
```
$ rabbit natarajan-chidambaram tensorflow-jenkins
              contributor            type     confidence
    natarajan-chidambaram           Human          0.984 
       tensorflow-jenkins             Bot          0.878
```

GitHub Apps interact and perform activities through a 'Bot' actor, which can be recognised in the contributor name by the `[bot]' suffix. They can be reported as Bot with 1.0 confidence based on their 'Bot' type in the GitHub Users API endpoint. (Because of the square brackets in the contributor name it needs to be surrounded by quotes.)
```
$ rabbit natarajan-chidambaram tensorflow-jenkins "github-actions[bot]"
              contributor            type     confidence
    natarajan-chidambaram           Human          0.984 
       tensorflow-jenkins             Bot          0.878
      github-actions[bot]             Bot            1.0
```

GitHub organization accounts are immediately retrieved with 1.0 confidence based on their 'Organization' type that can be retrieved from the GitHub Users API endpoint.
```
$ rabbit tensorflow-jenkins observerly
              contributor            type     confidence
       tensorflow-jenkins             Bot          0.878
               observerly    Organization            1.0
```

**With --input-file:** (Instead of providing each contributor name as a positional arguments, one can use an input text file containing all contributor names, one per line.)
```
$ rabbit --input-file logins.txt
              contributor            type     confidence
       tensorflow-jenkins             Bot          0.878
           johnpbloch-bot             Bot          0.996
      github-actions[bot]             Bot            1.0
```

**With combined use of positional arguments and --input-file:**
```
$ rabbit natarajan-chidambaram --input-file logins.txt
              contributor            type     confidence
    natarajan-chidambaram           Human          0.984 
       tensorflow-jenkins             Bot          0.878
           johnpbloch-bot             Bot          0.796
      github-actions[bot]             Bot            1.0
```

**With --verbose:** (Verbose provides detailed information used by the classficiation model, such as the number ofevents, number of activities NA, and values of the features that were used to determine the type of contributor. Details of these features can be found in the accompanying research publication.)

```
$ rabbit --input-file logins.txt --verbose
              contributor           type      confidence     events    NA      NT      NOR   ...   NAT_std      NAT_gini      NAT_IQR            
       tensorflow-jenkins            Bot           0.878       160    160       4        2   ...    17.093         0.541       15.503             
           johnpbloch-bot            Bot           0.796       300    300       3        1   ...    23.452         0.724       21.451             
      github-actions[bot]            Bot             1.0         -      -       -        -   ...         -             -            -             
                oberverly   Organization             1.0         -      -       -        -   ...         -             -            -      
    natarajan-chidambaram          Human           0.984        74     74       5        1   ...    14.834         0.924       12.113           
```

## License
This tool is distributed under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributors
[**Natarajan Chidambaram**](https://github.com/natarajan-chidambaram)

[**Alexandre Decan**](https://github.com/alexandredecan)

[**Tom Mens**](https://github.com/tommens)
