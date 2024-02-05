# RABBIT

Rabbit is an Activity Based Bot Identification Tool.
This is a machine learning-based tool to identify bot accounts based on their recent activities in GitHub.
The tool has been developed by Natarajan Chidambaram, researcher at the [Software Engineering Lab](http://informatique.umons.ac.be/genlog/) of the [University of Mons](https://www.umons.ac.be) (Belgium) as part of his PhD research in the context of [DigitalWallonia4.AI research project ARIAC (grant number 2010235)](https://www.digitalwallonia.be/ia/) and [TRAIL](https://trail.ac/en/)

This tool accepts an account name and/or a text file of GitHub account names (one account name per line) and a GitHub API key to give predictions after the following four steps.
The first step consists of extracting the public events performed by accounts in GitHub. If the number of events is less than the provided threshold (`--min-events`), then more events will be queried until the maximum number of queries (`--max-queries`)is reached. This step results in a set of events. 
The second step identifies activities (belonging to 24 different activity types) performed by the account in GitHub. 
The third step constitutes identifying the account behavioural features, namely, mean Number of Activities per activity Type (NAT_mean), Number of activity Types (NT), median time (Delta) between Consecutive Activities of different Types (DCAT_median), Number of Owners of Repositories contributed to (NOR), Gini inequality of Duration of Consecutive Activities (DCA_gini) and mean Number of Activities per Repository (NAR_mean). 
The fourth step simply applies the classification model that we trained on activities performed by 386 bots and 415 humans and evaluated on activities performed by 258 bots and 276 human accounts in GitHub and gives the prediction on the type of account along with the prediction confidence.

**Note about misclassifications** The tool is based on a machine learning classifier that is trained and validated on a ground-truth dataset if the account is bot or human along with their activity sequences, and cannot reach a precision and recall of 100%. 
When running the tool on a set of GitHub accounts of your choice, it is therefore possible that the tool may produce misclassifications in practice (humans misclassified as bots, or vice versa). 
If you encounter such situations while running the tool, please inform us about it, so that we can strive to further improve the accuracy of the classification algorithm. A known reason for the presence of misclassifications is the presence of very few activities in GitHub.
Since we considered the practical limitations of GitHub Events API, and to enable the tool to be used in practice, we trained, validated and tested the classification model by making 3 queries to the GitHub Events API as of 14 November 2023 for all the accounts in our collection. Also, we applied a lower bound condition that a contributor should have performed at least 5 events to predict their type.
The tool will query the GitHub Events API with 100 events per query until the required user's number of queries (through optional parameters) or until 3 queries have been made per account to the GitHub Events API.

## Submission
The tool is part of an empirical research endeavour aiming to identify bots in GitHub based on recent activities in GitHub repositories. An associated research paper is submitted at the International Conference on Mining Software Repositories 2024 (MSR2024) - Data and Tool Showcase Track under the title "**RABBIT: A tool for identifying bot accounts based on their recent GitHub event history**"

## Installation
Given that this tool has many dependencies, and in order not to conflict with already installed packages, it is recommended to use a virtual environment before its installation. You can install and create a _Python virtual environment_ and then install and run the tool in this environment. You can use any virtual environment of your choice. Below are the steps to install and create a virtual environment with **virtualenv**.

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

## Usage
To execute **RABBIT**, you need to provide a *GitHub personal access token* (API key). You can follow the instructions [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) to obtain such a token.

You can execute the tool with all default parameters by running `rabbit <path/to/names.txt> --key <token>`

Here is the list of parameters:

`--file <names.txt>`            **For predicting type of multiple accounts, a .txt file with the login names (one name per line) of the accounts should be provided to the tool.**
> Example: $ rabbit --file path/to/names.txt --key token

`--u <LOGIN_NAME>`            **For predicting type of single account, the login name of the account should be provided to the tool.**
> Example: $ rabbit --u contributorname --key token 

_Either of the above inputs `--file` or `--u` is mandatory for the tool. In case if both are given, then the accounts given with `--file` will be processed after the account given in `--u` is processed._

`--key <APIKEY>` 			**GitHub personal access token (key) required to extract events from the GitHub Events API**
> Example: $ rabbit path/to/names.txt --key token

_This parameter is mandatory and you can obtain an access token as described earlier_

`--start-time <START_TIME>` 		**Start time to be considered for anlysing the account's activity**
> Example: $ rabbit path/to/names.txt --key token --start-time '2023-01-01 00:00:00'

_The default start-time is 90 days before the current time._

`--min-events <MIN_EVENTS>` 		**Minimum number of events that are required to make a prediction**
> Example: $ rabbit path/to/names.txt --key token --min-events 10

_The default minimum number of events is 5._

`--max-queries <NUM_QUERIES>` 		**Number of queries that will be made to the GitHub Events API for each account**
> Example: $ rabbit path/to/names.txt --key token --queries 2

_The default number of queries is 3, allowed values are 1, 2 or 3._

`--verbose`              		**Also report the #events, #activities and values of the features that were used to make the prediction**
> Example: $ rabbit path/to/names.txt --key token --verbose

_The default value is False._

`--csv <FILE_NAME.csv>`                		Saves the result in comma-separated values (csv) format
`--json <FILE_NAME.json>`                	Outputs the result in json format
> Example: $ rabbit path/to/names.txt --key token --json output.json

`--incremental`              		**Method of reporting the results**
> Example: $ rabbit path/to/names.txt --key token --incremental

_The default value is False._

_If provided, the result will be printed on the screen or saved to the file once the prediction is made for each account. If not provided, the results will be printed/stored after making prediction for all the accounts in the provided list._

## Examples of RABBIT output (for illustration purposes only)

**With --file**
```
$ rabbit --file names.txt --key token
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
           johnpbloch-bot             bot          0.996
```

**With --u**
```
$ rabbit --u tensorflow-jenkins --key token
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
```

**With --file and --u**
```
$ rabbit --u tensorflow-jenkins --file names.txt --key token
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
           johnpbloch-bot             bot          0.996
    natarajan-chidambaram           human          0.984 
```

**With --start-time**
```
$ rabbit names.txt --key token --start-time '2023-09-19 00:00:00'
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
           johnpbloch-bot             bot          0.996
```

**With --min-events**
```
$ rabbit names.txt --key token --min-events 10
                  account      prediction      confidence
       tensorflow-jenkins             bot           0.993
           johnpbloch-bot             bot           0.996
```

**With human contributor**
```
$ rabbit names.txt --key token
                  account      prediction      confidence
       tensorflow-jenkins             bot           0.993
           johnpbloch-bot             bot           0.996
    natarajan-chidambaram           human           0.984   
```

**With --max-queries**
```
$ rabbit names.txt --key token --max-queries 1
                  account      prediction      confidence
       tensorflow-jenkins             bot           0.956
           johnpbloch-bot             bot           0.976
    natarajan-chidambaram           human           0.984
```

**With --verbose**
```
$ rabbit names.txt --key token --verbose
                  account      events      activities      NAT_mean      NT      DCAT_median      NOR      DCA_gini      NAR_mean      prediction      confidence
       tensorflow-jenkins         160            160          40.0     4.0             2.39      2.0         0.426        53.333             bot           0.993
           johnpbloch-bot         300            300         100.0     3.0            0.001      1.0         0.872         100.0             bot           0.996
    natarajan-chidambaram          74             74          14.8     5.0            0.211      3.0         0.951          24.5           human           0.984
```

**With --csv or --json**
```
$ rabbit names.txt --key token --csv predictions.csv
```

```
$ rabbit names.txt --key token --json predictions.json
```

**With --incremental**
```
$ rabbit names.txt --key token --incremental
```

## License
This tool is distributed under [Apache2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributors
[**Natarajan Chidambaram**](https://github.com/natarajan-chidambaram)

[**Alexandre Decan**](https://github.com/alexandredecan)

[**Tom Mens**](https://github.com/tommens)
