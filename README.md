# RABBIT is an Activity-Based Bot Identification Tool

**RABBIT** is a recursive acronym for "Rabbit is an Activity-Based Bot Identification Tool".
It is a command-line tool based on machine learning classifiers to identify whether a GitHub user account is controlled by a bot (and automated agent) or a human based on its recent GitHub event sequence. This tool requires as input a text file of logins (one per line, each login uniquely determining a given GitHub user account), your personal GitHub API key, and your user login associated with this key, in order to predict the type (bot or human) of each of the logins prodived in the input text file. 
To do so, **RABBIT** executes four steps:
 1. Extract (through the GitHub Events API) a sequence of public events performed by the user account corresponding to the provided login. If the number of events is less than the optional threshold `--min-events`, then more events will be queried until the maximum number of queries (optional parameter `--queries`) is reached. This step results, for each considered account, in a sequence of public events (belonging to 15 different event types).
For each user account ,the tool will query the GitHub Events API with 100 events per query until the maximum number of queries (not more than 3) have been reached.
 2. Convert the extracted events into activities (belonging to 24 different activity types) performed by the user account. 
 3. Use the activity sequence of the user account to compute the following features: mean Number of Activities per activity Type (NAT_mean), Number of activity Types (NT), median time (Delta) between Consecutive Activities of different Types (DCAT_median), Number of Owners of Repositories contributed to (NOR), Gini inequality of Duration of Consecutive Activities (DCA_gini) and mean Number of Activities per Repository (NAR_mean). 
 4. Apply a classification model (that was trained on activities performed by 386 bot accounts and 415 human accounts and evaluated on activities performed by 258 bot accounts and 276 human accounts) to predict the user account type along with the confidence of the prediction.

***Note about misclassifications.*** **RABBIT** is based on a machine learning classifier that is trained and validated on a ground-truth dataset, and therefore cannot reach a precision and recall of 100%.
When running the tool on a set of GitHub user accounts, it is therefore possible that the tool misclassifies some bots as humans, or vice versa. 
A known reason for such misclassifications is if the user account has generated very few GitHub events.
If you should encounter such misclassifications after running the tool, please inform us about it, so that we can strive to further improve the accuracy of the classification model. 
Considering the restrictions imposed on using the GitHub Events API, to enable the tool to be used in practice, we trained, validated and tested the classification model for all user accounts in our ground-truth dataset by making 3 queries to the GitHub Events API as on 14 November 2023. 
We imposed as a lower bound condition that a user account should have performed at least 5 events to predict its type.


## Citing this tool
**RABBIT** is part of an empirical research aiming to identify bots in GitHub based on recent their activities. To refer to this tool in any scientific (or other) publication, please use the following citation:
  
* **RABBIT: A tool for identifying bot accounts based on their recent GitHub event history.** Natarajan Chidambaram, Alexandre Decan, Tom Mens. *International Conference on Mining Software Repositories - Data and Tool Showcase Track*, 2024.

## Installation
Given that **RABBIT** has multiple dependencies, and in order not to conflict with already installed packages, we recommended to install and create a _Python virtual environment_ and then install and run the tool in this environment. You can use any virtual environment of your choice. Below are the steps to do so with **virtualenv**.

Install the virtual environment tool:
```
pip install virtualenv
```
Create a virtual environment in the folder where you want to place your files:
```
virtualenv <name>
```
Start the environment:
```
source <name>/bin/activate
```
After running this command your command line prompt will change to `(<name>) ...`.
Now you can install **RABBIT** with the following pip command. (You only need to do this once.)
```
pip install git+https://github.com/natarajan-chidambaram/RABBIT
```

Start using **RABBIT** (usage instructions are below).
When you are finished, quit the virtual environment:
```
deactivate
```

## Usage
To execute **RABBIT**, you need to provide a *GitHub personal access token* (API key). You can follow the instructions [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) to obtain such a token.

You can execute the tool with all default parameters by running

`rabbit <path/to/names.txt> --key <your API key> --username <your GitHub login>`

Here is the list of parameters:

`<names.txt>`                    **This is positional argument, should be provided as the first input to the tool**
> Example: $ rabbit path/to/names.txt --key token --username login

_This input is mandatory and should specify path to a text file containing all the login names of the GitHub user accounts that need to be analysed. Each login name should appear on a separate line in the file._

`--key <APIKEY>` 			**GitHub personal access token (API key) required to extract events from the GitHub Events API**
> Example: $ rabbit path/to/names.txt --key token --username login

_This parameter is mandatory._

`--username <LOGIN>`         **login for the GitHub user account associated to the API key**
> Example: $ rabbit path/to/names.txt --key token --username login

_This parameter is mandatory._

`--start-time <START_TIME>` 		**Start time to be considered for analysing the accounts' event sequences**
> Example: $ rabbit path/to/names.txt --key token --username login --start-time '2023-01-01 00:00:00'

_The default start-time is 90 days before the current time._

`--min-events <MIN_EVENTS>` 		**Minimum number of events required for each account to make a prediction**
> Example: $ rabbit path/to/names.txt --key token --username login --min-events 10

_The default minimum number of events is 5._

`--queries <NUM_QUERIES>` 		**Number of queries to be made to the GitHub Events API for each account**
> Example: $ rabbit path/to/names.txt --key token --username login --queries 2

_The default number of queries is 3, allowed values are 1, 2 or 3. A single query can retrieve up to 100 events._

`--verbose`              		**Report the values of the features that were used to make the prediction**
> Example: $ rabbit path/to/names.txt --key token --username login --verbose

_The default value is False._

`--csv <FILE_NAME.csv>`                		Outputs the result in comma-separated values (csv) format

`--json <FILE_NAME.json>`                	Outputs the result in JSON format
> Example: $ rabbit path/to/names.txt --key token --username login --json output.json

`--min-confidence`              	**Minimum confidence required to report the prediction for an account**
> Example: $ rabbit path/to/names.txt --key token --username login --min-confidence 0.5

_The default minimum confidence is 0.0._

`--incremental`              		**Method of reporting the results**
> Example: $ rabbit path/to/names.txt --key token --username username --incremental

_If this parameter is not provided, the results will only be output after making a prediction for all the accounts provided as input.
If it is provided, the results will be output incrementally for each account as soon as a prediction is made for that account._

## Examples of RABBIT output (for illustration purposes only)

**With required parameters only**
```
$ rabbit names.txt --username login --key token
                   account      events      prediction      confidence
1       tensorflow-jenkins         160             bot           0.993
2       johnpbloch-bot             300             bot           0.996
3    natarajan-chidambaram          74           human           0.984   
```

**With --start-time**
```
$ rabbit names.txt --username login --key token --start-time '2023-09-19 00:00:00'
                   account      events      prediction     confidence
1       tensorflow-jenkins         112             bot          0.978
2       johnpbloch-bot             300             bot          0.996
```

**With --min-events**
```
$ rabbit names.txt --username login --key token --min-events 10
                   account      events      prediction      confidence
1       tensorflow-jenkins         160             bot           0.993
2       johnpbloch-bot             300             bot           0.996
```

**With --queries**
```
$ rabbit names.txt --username login --key token --queries 1
                   account      events      prediction      confidence
1       tensorflow-jenkins         100             bot           0.956
2       johnpbloch-bot             100             bot           0.976
3    natarajan-chidambaram          74           human           0.984
```

**With --verbose**
```
$ rabbit names.txt --username login --key token --verbose
                   account      events      activites      NAT_mean      NT      DCAT_median      NOR      DCA_gini      NAR_mean      prediction      confidence
1       tensorflow-jenkins         160            160          40.0     4.0             2.39      2.0         0.426        53.333             bot           0.993
2       johnpbloch-bot             300            300         100.0     3.0            0.001      1.0         0.872         100.0             bot           0.996
3    natarajan-chidambaram          74             74          14.8     5.0            0.211      3.0         0.951          24.5           human           0.984
```

**With --csv or --json**
```
$ rabbit names.txt --username login --key token --csv predictions.csv
```

```
$ rabbit names.txt --username login --key token --json predictions.json
```

**With --min-confidence**
```
$ rabbit names.txt --username login --key token --min-confidence 0.7
                   account      events      prediction                  confidence
1       tensorflow-jenkins         160             bot                       0.993
2       johnpbloch-bot             300             bot                       0.996
3       boring-cyborg[bot]          36         Unknown      < confidence threshold
```

**With --incremental**
```
$ rabbit names.txt --username login --key token --incremental
```

## License
This tool is distributed under [Apache2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributors

The tool has been developed by Natarajan Chidambaram, researcher at the [Software Engineering Lab](http://informatique.umons.ac.be/genlog/) of the [University of Mons](https://www.umons.ac.be) (Belgium) as part of his PhD research in the context of [DigitalWallonia4.AI research project ARIAC (grant number 2010235)](https://www.digitalwallonia.be/ia/) and [TRAIL](https://trail.ac/en/)

[**Natarajan Chidambaram**](https://github.com/natarajan-chidambaram)

[**Alexandre Decan**](https://github.com/alexandredecan)

[**Tom Mens**](https://github.com/tommens)
