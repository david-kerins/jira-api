import os
import shutil
import time

from collections import Counter
from jira import JIRA
from jira.exceptions import JIRAError

import re
import requests
import simplejson as json

# debug flag and libs
verbose = False
# debug libs
#import httplib
#httplib.HTTPConnection.debuglevel= 1

day = time.strftime("%Y-%m-%d")

# Connection setup for the jira-python library
# NOTE: JIRA Python lib will look for credentials stored in ~/.netrc
options = {'server': 'https://bwa.url.for.jira/int/jira'}
jira = JIRA(options)

# The first try checks that each line in the rfds.txt file has an existing project in JIRA.
# If a project is missing it will warn the user and halt.  You have to manually create the missing projects.
# The second try will create the Version number if it does not exist.
# It will also create the 'webapp' and 'database' components for the
# project if they do not exist.
try:
    with open('./rfds.txt') as rfds:
        lines = rfds.read().splitlines()
        for line in lines:
            # Reset the booleans for each loop
            version_exists = False
            webapp = False
            database = False
            group = False
            dba_needed = False
            # Tokenize the current line
            tokens = line.strip(' \t\n\r').split("-")
            #tokens = line.split("-")
            app = tokens[0]
            version = tokens[1]
            env = tokens[2]
            deploytime = tokens[3]
            dba = tokens[4]

            # RFD dict
            rfd_dict = {}
            # DBA RFD-subtask
            rfd_st_dba_dict = {}
            # Jenkins RFD-subtask
            rfd_st_jenkins_dict = {}

            # Test that project/app exists in JIRA, if not bail on iteration
            try:
                project = jira.project(app.upper())
            except JIRAError as e:
                if e.status_code == 404:
                    print "Project %s doesn't exist." % app.upper()
                    print "You must manually create the %s project and then re-run this script." % app.upper()
                    continue

            if env == "qa":
                targetenv = "int"
            else:
                targetenv = tokens[2]

            if dba == "dba":
                dba_needed = True

            devgroup = app.upper() + "-developers"
            datetime = day + "T" + deploytime
            project = jira.project(app.upper())

            # Make sure Release Version exists in JIRA
            versions = jira.project_versions(project)
            print "Checking for the Version..."
            for v in versions:
                if v.name == version:
                    version_exists = True
            if not version_exists:
                print "The version %s does NOT exist.  Adding..." % version
                jira.create_version(version, app.upper())

            # Make sure Components exists in JIRA Project
            components = jira.project_components(project)
            print "Checking for Components..."
            for c in components:
                if c.name == "webapp":
                    webapp = True
                if c.name == "database":
                    database = True

            if not webapp:
                print "webapp component does not exist.  Adding..."
                jira.create_component(
                    "webapp", app.upper(), None, None, "UNASSIGNED", False)
            if not database:
                print "database component does not exist.  Adding..."
                jira.create_component(
                    "database", app.upper(), None, None, "UNASSIGNED", False)

            print "Checking for Developer Group... %s" % devgroup
            groups = jira.groups(query=devgroup)
            for g in groups:
                if g == devgroup:
                    group = True
            if not group:
                print "Developer group does not exist.  Adding %s" % devgroup
                jira.add_group(devgroup)

            # Populate the KV pairs for the RFD
            rfd_dict['project'] = {'key': '' + app.upper() + ''}

            if env == 'qa':
                rfd_dict['issuetype'] = {'name': 'Task'}
                rfd_dict['description'] = 'QA code review.'
            else:
                rfd_dict['issuetype'] = {'name': 'RFD'}

            rfd_dict['summary'] = 'Deploy ' + app.upper() + ' ' + \
                version.upper() + ' to ' + env.upper() + ''
            rfd_dict['fixVersions'] = [{'name': '' + version.upper() + ''}]
            rfd_dict['priority'] = {'name': 'Medium'}
            rfd_dict['customfield_10121'] = {
                'value': '' + targetenv.upper() + ''}
            rfd_dict['customfield_10636'] = '' + datetime + ':00.000-0700'

            rfd = jira.create_issue(fields=rfd_dict)
            print "Created RFD: %s" % rfd
            if verbose:
                print "RFD Dict"
                print rfd_dict

            if dba_needed:
                # Populate the KV pairs for the DBA RFD-subtask
                rfd_st_dba_dict['project'] = {'key': '' + app.upper() + ''}

                if env == 'qa':
                    rfd_st_dba_dict['issuetype'] = {'name': 'Sub-task'}
                else:
                    rfd_st_dba_dict['issuetype'] = {'name': 'RFD-subtask'}

                rfd_st_dba_dict['parent'] = {'key': '' + str(rfd) + ''}
                rfd_st_dba_dict['summary'] = 'Deploy ' + app.upper() + \
                    ' ' + version.upper() + '/00 to ' + env.upper() + ''
                rfd_st_dba_dict['description'] = '00\nREADME: []\nSCRIPTS: []'
                rfd_st_dba_dict['components'] = [{'name': 'database'}]
                rfd_st_dba_dict['customfield_10121'] = {
                    'value': '' + targetenv.upper() + ''}
                rfd_st_dba_dict['customfield_10636'] = '' + \
                    datetime + ':00.000-0700'

                rfd_dba_task = jira.create_issue(fields=rfd_st_dba_dict)
                print "Created DBA sub-task: %s " % rfd_dba_task

                if verbose:
                    print "DBA Subtask Dict"
                    print rfd_st_dba_dict

            if not env == 'qa':
                # Populate the KV pairs for the Jenkins RFD-subtask
                rfd_st_jenkins_dict['project'] = {'key': '' + app.upper() + ''}
                rfd_st_jenkins_dict['issuetype'] = {'name': 'RFD-subtask'}
                rfd_st_jenkins_dict['parent'] = {'key': '' + str(rfd) + ''}
                rfd_st_jenkins_dict['summary'] = 'Deploy ' + \
                    app.upper() + ' ' + version.upper() + ' to ' + env.upper() + ''
                rfd_st_jenkins_dict['description'] = 'JENKINS: '
                rfd_st_jenkins_dict['components'] = [{'name': 'webapp'}]
                rfd_st_jenkins_dict['customfield_10121'] = {
                    'value': '' + targetenv.upper() + ''}
                rfd_st_jenkins_dict['customfield_10636'] = datetime + \
                    ':00.000-0700'

                rfd_jenkins_task = jira.create_issue(
                    fields=rfd_st_jenkins_dict)
                print "Created Jenkins sub-task: %s " % rfd_jenkins_task

                if verbose:
                    print "Jenkins Subtask Dict"
                    print rfd_st_jenkins_dict

            if not env == 'qa':
                # Transition RFD to Schedule state
                print "Scheduling the RFD"
                jira.transition_issue(rfd, 'Submit')
                jira.transition_issue(rfd, 'Start review')
                jira.transition_issue(rfd, 'Approve')
                jira.transition_issue(rfd, 'Schedule')
                if dba_needed:
                    # Transition DBA subtask
                    print "Scheduling the DBA subtask"
                    #transitions = jira.transitions(rfd_dba_task)
                    # print [(t['id'], t['name']) for t in transitions]
                    jira.transition_issue(rfd_dba_task, 'Start review')
                    jira.transition_issue(rfd_dba_task, 'Approve')
                    jira.transition_issue(rfd_dba_task, 'Schedule')
                # Transition Jenkins subtask
                print "Scheduling the Jenkins subtask"
                #transitions = jira.transitions(rfd_jenkins_task)
                # print [(t['id'], t['name']) for t in transitions]
                jira.transition_issue(rfd_jenkins_task, 'Start review')
                jira.transition_issue(rfd_jenkins_task, 'Approve')
                jira.transition_issue(rfd_jenkins_task, 'Schedule')

            jira.add_watcher(rfd, project.lead.name)
    rfds.close()
except JIRAError as e:
    print "Something bad happened while processing the %s application JIRA tickets." % app.upper()
    rfds.close()
