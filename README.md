# RABBIT

RABBIT is a recursive acronym for "RABBIT is an Activity-Based Bot Identification Tool".
It is based on a binary classifaction model to identify bot accounts based on their recent activities in GitHub.
RABBIT is quite efficient, being able to predict thousands of accounts per hour, without reaching GitHub's imposed hourly API rate limit of 5,000 queries.

The tool has been developed by Natarajan Chidambaram, researcher at the [Software Engineering Lab](http://informatique.umons.ac.be/genlog/) of the [University of Mons](https://www.umons.ac.be) (Belgium) as part of his PhD research in the context of [DigitalWallonia4.AI research project ARIAC (grant number 2010235)](https://www.digitalwallonia.be/ia/) and [TRAIL](https://trail.ac/en/). More details about the tool can be found in the  scientific publication cited below.

**Citation**: Natarajan Chidambaram, Tom Mens, and Alexandre Decan. 2024. ***RABBIT: A tool for identifying bot accounts based on their recent GitHub event history.*** In 21st International Conference on Mining Software Repositories (MSR ’24), April 15–16, 2024, Lisbon, Portugal. ACM, New York, NY, USA, 5 pages. https://doi.org/10.1145/3643991.3644877

## How it works
RABBIT accepts a GitHub account login name and/or a text file of multiple login names (one name per line) and requires a GitHub API key.
First the tool checks whether the login name corresponds to a valid existing account in GitHub and returns **invalid** otherwise. If the login name
corresponds to a GitHub App (based on the login name ending with [bot] and the Bot type returned by a call to the GitHub Users API), the tool predicts **app**.
For the remaining login names, a prediction of **bot**, **human** or **unknown** will be made after the following steps.
The first step consists of extracting the latest public events performed by the account in GitHub, using a one or more queries to the GitHub Events API.
If the number of events retrieved is less than the required threshold the prediction will be **unknown** due to a lack of data.
If enough events are available to make a prediction for the account, the second step converts the events into activities (belonging to 24 different activity types). The third step computes the following features for the account: mean Number of Activities per activity Type (NAT_mean), Number of activity Types (NT), median time (Delta) between Consecutive Activities of different Types (DCAT_median), Number of Owners of Repositories contributed to (NOR), Gini inequality of Duration of Consecutive Activities (DCA_gini) and mean Number of Activities per Repository (NAR_mean). 
The fourth step applies the classification model and returns the prediction of **bot** or **human** along with a confidence score between 0 and 1.

**Note about misclassifications.** RABBIT tool is based on a machine learning classifier that is trained and validated on a ground-truth dataset, and cannot reach a precision and recall of 100%. 
When running it on a set of GitHub accounts of your choice, it is therefore possible to have misclassifications (humans misclassified as bots, or vice versa). 
If you encounter such situations while running the tool, please inform us about it, so that we can strive to further improve the accuracy of the classification model. A known reason for the presence of misclassifications is a too limited number of activities available for the account.

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

## Usage
To execute **RABBIT**, you need to provide a *GitHub personal access token* (API key). You can follow the instructions [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) to obtain such a token.

You can execute the tool with all default parameters by running `rabbit <LOGIN_NAME> --key <APIKEY>` 
or `rabbit --input-file <path/to/loginnames.txt> --key <APIKEY>` or `rabbit -f <path/to/loginnames.txt> --key <APIKEY>`

Here is the list of parameters:

`<LOGIN_NAME>`            **A positional argument (not mandatory) for predicting type of single account, the login name of the account should be provided.**
> Example: $ rabbit natarajan-chidambaram --key token 

`--input-file <path/to/loginnames.txt>`            **For predicting the type of multiple accounts, a .txt file with the login names (one name per line) of the accounts should be provided as input.**
> Example: $ rabbit --input-file logins.txt --key token

_Either the positional argument `<LOGIN_NAME>` or `--input-file` is mandatory. In case both are given, then the accounts given with `--input-file` will be processed after the account given in the positional argument has been processed._

`--key <APIKEY>` 			**GitHub personal access token (key) required to extract events from the GitHub Events API.**
> Example: $ rabbit --input-file logins.txt --key token

_This parameter is mandatory and you can obtain an access token as described earlier_

`--min-events <MIN_EVENTS>` 		**Minimum number of events that are required to make a prediction.**
> Example: $ rabbit --input-file logins.txt --key token --min-events 10

_The default minimum number of events is 5._

`--max-queries <NUM_QUERIES>` 		**Maximum number of queries that will be made to the GitHub Events API for each account.**
> Example: $ rabbit --input-file logins.txt --key token --queries 2

_The default number of queries is 3, allowed values are 1, 2 or 3._

`--verbose`              		**Report the #events, #activities and values of the features that were used to make a prediction.**
> Example: $ rabbit --input-file logins.txt --key token --verbose

_The default value is False._

`--csv <FILE_NAME.csv>`                		Saves the result in comma-separated values (csv) format
`--json <FILE_NAME.json>`                	Outputs the result in json format
> Example: $ rabbit --input-file logins.txt --key token --json output.json

`--incremental`              		**Method of reporting the results**
> Example: $ rabbit --input-file logins.txt --key token --incremental

_The default value is False._

_If provided, the result will be printed on the screen or saved to the file once the prediction is made for each account. If not provided, the results will be printed/stored after making prediction for all the accounts in the provided list._

## Examples of RABBIT output (for illustration purposes only)

**With positional argument**
```
$ rabbit tensorflow-jenkins --key token
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
```

**With --input-file**
```
$ rabbit --input-file logins.txt --key token
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
           johnpbloch-bot             bot          0.996
      github-actions[bot]             app            1.0
```

**With combined use of positional argument and --input-file**
```
$ rabbit tensorflow-jenkins --input-file logins.txt --key token
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
           johnpbloch-bot             bot          0.996
      github-actions[bot]             app            1.0
    natarajan-chidambaram           human          0.984 
```

**With --start-time**
```
$ rabbit --input-file logins.txt --key token --start-time '2023-09-19 00:00:00'
                  account      prediction     confidence
       tensorflow-jenkins             bot          0.978
           johnpbloch-bot             bot          0.996
      github-actions[bot]             app            1.0
```

**With --min-events**
```
$ rabbit --input-file logins.txt --key token --min-events 10
                  account      prediction      confidence
       tensorflow-jenkins             bot           0.993
           johnpbloch-bot             bot           0.996
      github-actions[bot]             app             1.0
```

**With human contributor**
```
$ rabbit --input-file logins.txt --key token
                  account      prediction      confidence
       tensorflow-jenkins             bot           0.993
           johnpbloch-bot             bot           0.996
      github-actions[bot]             app             1.0
    natarajan-chidambaram           human           0.984 
```

**With --max-queries**
```
$ rabbit --input-file logins.txt --key token --max-queries 1
                  account      prediction      confidence
       tensorflow-jenkins             bot           0.956
           johnpbloch-bot             bot           0.976
      github-actions[bot]             app            1.0
    natarajan-chidambaram           human           0.984
```

**With --verbose**
```
$ rabbit --input-file logins.txt --key token --verbose
                  account      events      activities      NAT_mean      NT      DCAT_median      NOR      DCA_gini      NAR_mean      prediction      confidence
       tensorflow-jenkins         160            160          40.0      4.0             2.39      2.0         0.426        53.333             bot           0.993
           johnpbloch-bot         300            300         100.0      3.0            0.001      1.0         0.872         100.0             bot           0.996
      github-actions[bot]         NaN            NaN           NaN      NaN              NaN      NaN           NaN           NaN             app             1.0
    natarajan-chidambaram          74             74          14.8      5.0            0.211      3.0         0.951          24.5           human           0.984
```

**With --csv or --json**
```
$ rabbit --input-file logins.txt --key token --csv predictions.csv
```

```
$ rabbit --input-file logins.txt --key token --json predictions.json
```

**With --incremental**
```
$ rabbit --input-file logins.txt --key token --incremental
```

## License
This tool is distributed under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

## Contributors
[**Natarajan Chidambaram**](https://github.com/natarajan-chidambaram)

[**Alexandre Decan**](https://github.com/alexandredecan)

[**Tom Mens**](https://github.com/tommens)
