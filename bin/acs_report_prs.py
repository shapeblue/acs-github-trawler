#!/usr/bin/env python

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Usage:

Sample json file contents:

acs_report_prs.py --config=conf.txt
{
	"--gh_token":"************",
	"--prev_release_commit_sha":"************",
	"--repo_name":"apache/cloudstack",
	"--branch":"master",
	"--prev_release_ver":"4.14.0.0",
	"--new_release_ver":"4.15.0.0",
	"--tmp_dir":"/tmp",
	"--update_labels": "False",
	"--output_file_name": "prs_report.rst",
	"--required_tables":"['wip_features', 'merged_fixes', 'merged_features', 'dontknow', 'old_prs']"
}
                    
Additional Option:

    "--docker_created_config":"True"     used to know whether to remove conf file if in container (for some safety)    


requires: python3.8 + pip install docopt pygithub prettytable pygit2
+ git

"""

import docopt
import json
from github import Github
from prettytable import PrettyTable
import os.path
import sys
from  datetime import datetime, timedelta
from lib import processors
import operator
import re
import time
import shutil




def load_config():
    """
    Parse the command line arguments and load in the optional config file values
    """
    global gh_token

    args = docopt.docopt(__doc__)
    if args['--config'] and os.path.isfile(args['--config']):
        json_args = {}
        try:
            with open(args['--config']) as json_file:    
                json_args = json.load(json_file)
        except Exception as e:
            print(("Failed to load config file '%s'" % args['--config']))
            print(("ERROR: %s" % str(e)))
        if json_args:
            args = merge(args, json_args)
    #     since we are here, check that the required fields exist
    valid_input = True
    #if not args['--gh_token'] or (isinstance(args['--gh_token'], list)):
    try:
        gh_token = args['--gh_token']
    except:
        print("ERROR: gh_token is required")
        valid_input = False

    if not valid_input:
        sys.exit(__doc__)
    return args

def merge(primary, secondary):
    """
    Merge two dictionaries.
    Values that evaluate to true take priority over false values.
    `primary` takes priority over `secondary`.
    """
    return dict((str(key), primary.get(key) or secondary.get(key))
                for key in set(secondary) | set(primary))


# run the code...
if __name__ == '__main__':
    print('\nInitialising...\n\n')

    args = load_config()

# Must have either Commit SHA of last version or Verion number to proceed
    try:
        prev_release_ver = args['--prev_release_ver']
    except:
        prev_release_ver = "NULL"
    try:
        prev_release_commit_sha = args['--prev_release_commit_sha']
    except:
        prev_release_commit_sha = "NULL"

    if prev_release_commit_sha == "NULL" and prev_release_ver == "NULL":
        print("Starting commit SHA or version is required to continue")
        sys.exit()

#  set defaults for optional parameters

    try:
        repo_name = args['--repo']
    except:
        repo_name = "apache/cloudstack"

    try:
        new_release_ver = args['--new_release_ver']
    except:
        new_release_ver = 1

    try:
        branch = args['--branch']
    except:
        branch = 'master'
    
    try:    
        output_file_name = args['--output_file_name']
    except:
        output_file_name = "prs.rst"

    try:
        gh_base_url = args['--gh_base_url']
    except:
        gh_base_url = "https://github.com"

    try:
        required_tables = str(args['--required_tables'])
    except:
        required_tables = ['wip_features', 'merged_fixes', 'merged_features', 'dontknow', 'old_prs'] 

    try:
        col_title_width = int(args['--col_title_width'])
    except:
        col_title_width = 60
    
    # Delete config file if was dynamically
    
    try:
        docker_created_config = bool(args['--docker_created_config'])
    except:
        docker_created_config = bool(False)

    try:
        destination = str(args['--destination'])
    except:
        destination = "/opt"

    tmp_dir="/tmp"
    if docker_created_config:
        tmp_tmp_dir =  str(tmp_dir + "/docker_output")
        try:
            os.rmdir(tmp_tmp_dir)
        except OSError:
            print ("")
        
        try:
            os.mkdir(tmp_tmp_dir)
        except OSError:
            print ("")
        else:
            print ("Successfully created empty output directory %s " % tmp_tmp_dir)
            os.remove(str(args['--config']))

    tmp_repo_dir = str(tmp_dir) + "/repo"   
    
    gh = Github(gh_token)

    wip_features_table = PrettyTable(["PR Number", "Title", "Type", "Notes", "_index"])
    fixes_table = PrettyTable(["PR Number", "Title", "Type", "Severity", "_index"]) 
    features_table = PrettyTable(["PR Number", "Title", "Type", "Notes", "_index"])
    dontknow_table = PrettyTable(["PR Number", "Title"])
    old_pr_table = PrettyTable(["PR Number", "Title", "Type", "Notes", "_index"])
    old_pr_table.align["Title"] = "l"
    wip_features_table.align["Title"] = "l"
    features_table.align["Title"] = "l"
    fixes_table.align["Title"] = "l"
    dontknow_table.align["Title"] = "l"
    old_pr_table._max_width = {"Title":col_title_width}
    wip_features_table._max_width = {"Title":col_title_width}
    features_table._max_width = {"Title":col_title_width}
    fixes_table._max_width = {"Title":col_title_width}
    dontknow_table._max_width = {"Title":col_title_width}

    repo = gh.get_repo(repo_name)

    ## TODO - get commit -> commit date from tag on master.
    ## Searching seems a waste

    #repo_tags = repo.get_tags()


    if prev_release_commit_sha != "NULL":
        print("Previous Release Commit SHA found in conf file, skipping pre release SHA search.\n")
        prev_release_sha = prev_release_commit_sha
    else:
        print("Finding commit SHA for previous version " + prev_release_ver)
        for tag in repo_tags:
            if tag.name == prev_release_ver:
                prev_release_sha = tag.commit.sha

    commit = repo.get_commit(sha=prev_release_sha)
    prev_release_commit_date=str(commit.commit.author.date.date())
    if not commit:
        print("No starting point found via version tag or commit SHA")
        exit

    print("Enumerating Open WIP PRs in master\n")
    print("- Retrieving Pull Request Issues from Github")
    search_string = f"repo:apache/cloudstack is:open is:pr label:wip"
    issues = gh.search_issues(search_string)
    wip_features = 0
    old_prs = 0

    print("- Processing OPEN Pull Requests (as issues)\n")
    for issue in issues:
        pr = issue.repository.get_pull(issue.number)
        label = []
        pr_num = str(pr.number)
        labels = pr.labels
        if "wip_features" in required_tables:
            if [l.name for l in labels if l.name=='wip']:
                wip_features_table.add_row([pr_num, pr.title.strip(), "-", "-", 1]) 
                print("-- Found open PR : " + pr_num + " with WIP label")
                wip_features += 1
        if "old_prs" in required_tables:
            creation_date = pr.created_at
            check_date_old = datetime.now() - timedelta(days=365)
            check_date_very_old = datetime.now() - timedelta(days=2*365)
            if creation_date < check_date_very_old:
                print("**** More than 2 years old")
                old_prs += 1
                old_pr_table.add_row([pr_num, pr.title.strip(), "Very old PR", "Add label age:2years_plus", 2])

            elif creation_date < check_date_old:
                print("**** More than 1 year old")
                old_prs += 1
                old_pr_table.add_row([pr_num, pr.title.strip(), "Old PR", "Add label age:1year_plus", 1])


    print("\nEnumerating closed and merged PRs in master\n")

    print("- Retrieving Pull Request Issues from Github")
    search_string = f"repo:apache/cloudstack is:closed is:pr is:merged merged:>={prev_release_commit_date}"
    issues = gh.search_issues(search_string)
    features = 0
    fixes = 0
    uncategorised = 0

    print("\nFinding reverted PRs")
    reverted_shas = processors.get_reverted_commits(repo, branch,prev_release_commit_date, tmp_repo_dir)
    print("- Found these reverted commits:\n", reverted_shas)

    print("\nProcessing MERGED Pull Request Issues\n")
    for issue in issues:
        label_matches = 0
        pr = issue.repository.get_pull(issue.number)
        pr_commit_sha = pr.merge_commit_sha
        if pr_commit_sha in reverted_shas:
            print("- Skipping PR %s, its been reverted", pr.merge_commit_sha)
        else:
            label = []
            severity_label = []
            pr_num = str(pr.number)
            labels = pr.labels
            severity_label_match = 0
            severity_label_test = ''

            for l in labels:
                severity_label_test = l.name.find("Severity")
                if int(severity_label_test) != -1:
                    severity_label = l.name[9:]
                    severity_label_match += 1 
            if severity_label_match != 1:
                severity_label = "unmatched"
            
            index_dict = {"BLOCKER":"01","Critical":"02", "Major":"03", "Minor":"04", "Trivial":"05", "none":"98", "unmatched":"99"}

            severity_index = index_dict[severity_label]

            if "merged_features" in required_tables:
                if [l.name for l in labels if l.name=='type:new-feature' or l.name=='type:new_feature']:
                    features_table.add_row([pr_num, pr.title.strip(), "New Feature", "-", 1 ]) 
                    print("-- Found PR: " + pr_num + " with feature label")
                    features += 1
                    label_matches += 1
            if "merged_features" in required_tables:
                if [l.name for l in labels if l.name=='type:enhancement']:
                    features_table.add_row([pr_num, pr.title.strip(), "Enhancement", "-", 2]) 
                    print("-- Found PR: " + pr_num + " with enhancement label")
                    features += 1
                    label_matches += 1
            if "merged_fixes" in required_tables:
                if [l.name for l in labels if l.name == 'type:bug' or l.name == 'type:cleanup']:
                    fixes_table.add_row([pr_num, pr.title.strip(), "Bug Fix", severity_label, severity_index]) 
                    print("-- Found PR: " + pr_num + " with fix label, Severity of " + str(severity_label))
                    fixes += 1
                    label_matches += 1
            if "dontknow" in required_tables:
                if label_matches == 0:
                    print("-- Found PR: " + pr_num + " with no matching label")
                    dontknow_table.add_row([pr_num, pr.title.strip()])
                    uncategorised += 1

    print("\nwriting tables")

    if docker_created_config:
        output_file = str(tmp_tmp_dir + "/" + output_file_name)
    else:
        output_file = str(destination + "/" + output_file_name)

    with open(output_file ,"w") as file:

        if "wip_features" in required_tables:
            if wip_features > 0:
                wip_features_table.sortby = "_index"
                wip_features_table_txt = wip_features_table.get_string(fields=["PR Number", "Title", "Type", "Notes"])
                file.write('\nWork in Progress PRs\n\n')
                file.write(wip_features_table_txt)
                file.write('\n%s PRs listed\n\n' % str(wip_features))

        if "merged_features" in required_tables:
            if features > 0:
                features_table.sortby = "_index"
                features_table_txt = features_table.get_string(fields=["PR Number", "Title", "Type", "Notes"])
                file.write('New (merged) Features & Enhancements\n\n')
                file.write(features_table_txt)
                file.write('\n%s Features listed\n\n' % str(features))
            else:
                file.write('No new features merged yet for next release.\n\n')

        if "merged_fixes" in required_tables:
            if fixes > 0:
                fixes_table.sortby = "_index"
                fixes_table_txt = fixes_table.get_string(fields=["PR Number", "Title", "Type", "Severity"])
                file.write('Bug Fixes (merged)\n\n')        
                file.write(fixes_table_txt)
                file.write('\n%s Bugs listed\n\n' % str(fixes))
            else:
                file.write('No new fixes merged yet for next release.\n\n')

        if "dontknow" in required_tables:
            if uncategorised > 0:
                dontknow_table.sortby = "PR Number"
                dontknow_table_txt = dontknow_table.get_string(fields=["PR Number", "Title"])
                file.write('Uncategorised Merged PRs\n\n')
                file.write(dontknow_table_txt)
                file.write('\n%s uncategorised issues listed\n\n' % str(uncategorised))
            else:
                file.write('No Uncategorised PRs to report.\n\n')

        if "old_prs" in required_tables:
            old_pr_table.sortby = "Notes"
            old_pr_txt = old_pr_table.get_string(fields=["PR Number", "Title", "Type", "Notes"])
            file.write('Old PRs still open\n\n')
            file.write(old_pr_txt)
            file.write('\n%s Old PRs listed\n\n' % str(old_prs))
    file.close()
    print("\nTable has been output to %s\n\n" % output_file)
