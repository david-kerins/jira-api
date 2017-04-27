# jira-api

This python script depends on the jira-python library.

Once you have cloned this repo, cd into jira-api and then git clone the jira-python library dependencies.

  git clone https://github.com/david-kerins/jira.git

Then get the deployments from the calendar and paste into the excel file.

Then copy the derived file names from column H of the spreadsheet.

Paste these strings into the rfds.txt file.

Then execute the python script.

python make_deployment_tickets.py
