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
  fixed_issues.py [--config=<config.json>]
                  [-t <arg> | --gh_token=<arg>] 
                  [-c <arg> | --prev_rel_commit=<arg>]
                  [-b <arg> | --branch=<arg>]  
                  [--repo=<arg>] 
                  [--gh_base_url=<arg>] 
                  [--col_title_width=<arg>] 

  fixed_issues.py (-h | --help)
Options:
  -h --help                         Show this screen.
  --config=<config.json>            Path to a JSON config file with an object of config options.
  --gh_token=<arg>         Required: Your Github token from https://github.com/settings/tokens 
                                      with `repo/public_repo` permissions.
  --prev_rel_commit=<arg>  Required: The commit hash of the previous release.
  --branches=<arg>         Required: Comma separated list of branches to report on (eg: 4.7,4.8,4.9).
  --new_release_ver=<arg            not used in this iteration yet

                                      The last one is assumed to be `master`, so `4.7,4.8,4.9` would
                                      actually be represented by 4.7, 4.8 and master.
  --repo=<arg>                      The name of the repo to use [default: apache/cloudstack].
  --gh_base_url=<arg>               The base Github URL for pull requests 
                                      [default: https://github.com/apache/cloudstack/pull/].
  --col_title_width=<arg>          The width of the title column [default: 60].
  --docker_created_config=<arg>     used to know whether to remove conf file if in container (for some safety)    

Sample json file contents:

{
	"--gh_token":"******************",
	"--prev_release_commit":"",
	"--repo_name":"apache/cloudstack",
	"--branch":"4.11",
	"--prev_release_ver":"4.11.1.0",
	"--new_release_ver":"4.11.2.0"
}

requires: python3.8 + docopt pygithub prettytable gitpython

"""
from typing import DefaultDict
import docopt
import json
from github import Github
import os.path
import re
import sys
from prettytable import PrettyTable
from datetime import datetime, timedelta
from lib import processors


def load_config():
    """
    Parse the command line arguments and load in the optional config file values
    """
    args = docopt.docopt(__doc__)
    args['--update_labels'] = ''
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
    for arg in ['--gh_token', '--branch', '--repo']:
        if not args[arg] or (isinstance(args[arg], list) and not args[arg][0]):
            print(("ERROR: %s is required" % arg))
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

def label_match(label_string, text_string):

    global issue_matched_count
    global issue_labels_mismatch
    global issue_all_bad
    global bad_issue_count
    global no_match_count
    global issue_desc_exist
    global issue_label_exist
    global label_to_add
    global issue_missing_labels
    global issue_improvement_rename

    search_string = '.*- \[ ?x ?\] ' + text_string + ' .*'
    #print('--- Looking for ' + text_string + ' in description')
    if label_string != "type:healthcheckrun":
        if re.search(search_string, str(issue.body), re.I):
            issue_desc_exist += 1
            if label_string in existing_label_names:
                issue_label_exist += 1
                issue_matched_count += 1
            else:
                label_to_add = label_string
                issue_missing_labels += 1
                issue_labels_mismatch += 1
        else:
            if label_string in existing_label_names:
                issue_label_exist += 1
                issue_labels_mismatch += 1
            else:
                no_match_count += 1

    return issue_matched_count, issue_labels_mismatch, no_match_count, issue_desc_exist, \
        issue_label_exist,  label_to_add, issue_missing_labels


def label_reconcile(prtype_text,label_to_add):
    
    global issue_matched_count
    global issue_labels_mismatch
    global issue_all_bad
    global bad_issue_count
    global no_match_count
    global issue_desc_exist
    global issue_label_exist
    global issue_missing_labels
    global issue_improvement_rename
    global labels_mismatched
    global labels_added
    global labels_matched
    global labels_all_bad
    global labels_mismatch_table
    global update_labels
    global labels_all_bad_table
    global labels_added_table
    global prev_release_commit_date


    if issue_matched_count == 1:
        labels_matched += 1
        print("---- Matching label found - no action")
    else:
        if issue_desc_exist > 1 or issue_label_exist > 1:
            print("XXXX Too many label or description matches")
            labels_mismatch_table.add_row([pr_num, pr.title.strip(), prtype_text, "Label/description mismatch"])
            labels_mismatched += 1
        else:
            if issue_desc_exist > 0 and issue_label_exist > 0:
                print("XXXX Label and description don't match")
                labels_mismatch_table.add_row([pr_num, pr.title.strip(), prtype_text, "Label/description mismatch"])
                labels_mismatched += 1

            elif (issue_label_exist > 0 and issue_desc_exist == 0):
                print("XXX Label without description")
                labels_mismatch_table.add_row([pr_num, pr.title.strip(), prtype_text, "Label without description"])
                labels_mismatched += 1

            elif issue_desc_exist == 1 and issue_label_exist == 0:
                labels_added += 1
                add_label_res =  "++++ label '" + label_to_add[5:] + "' added"
                print(add_label_res)
                add_label_text = add_label_res[5:]
                labels_added_table.add_row([pr_num, pr.title.strip(), prtype_text, add_label_text])
                if update_labels:
                    pr.add_to_labels(label_to_add)

            elif no_match_count == len(label_names):
                labels_all_bad += 1
                labels_all_bad_table.add_row([pr_num, pr.title.strip(), prtype_text, "No label or description"])
                print("XXXX No type labels or type in description")
            else:
                print("**** Something went wrong, I'm confused")


# run the code... 
if __name__ == '__main__':
    print('\nInitialising...\n\n')

    args = load_config()
#   repository details
    gh_token = args['--gh_token']
    gh = Github(gh_token)
    repo_name = args['--repo']
    branch = args['--branch']
    gh_base_url = args['--gh_base_url']
    prev_release_ver = args['--prev_release_ver']
    prev_release_commit = args['--prev_release_commit_sha']
    draft_pr_label = "wip"
    update_labels = args['--update_labels']
    if update_labels != '':
        update_labels = bool(args['--update_labels'])
    else:
        update_labels = bool(False)
    col_title_width = 60

    repo = gh.get_repo(repo_name)
    labels_added_table = PrettyTable(["PR Number", "Title", "PR Type", "Result"])
    labels_added_table.align["PR Type"] = "l"
    labels_added_table.align["Title"] = "l"
    labels_added_table.align["Result"] = "l"
    labels_added_table._max_width = {"Title":col_title_width}

    labels_all_bad_table = PrettyTable(["PR Number", "Title", "PR Type", "Result"]) 
    labels_all_bad_table.align["Title"] = "l"
    labels_all_bad_table.align["Result"] = "l"
    labels_all_bad_table._max_width = {"Title":col_title_width}

    labels_mismatch_table = PrettyTable(["PR Number", "Title", "PR Type", "Result"])
    labels_mismatch_table.align["Title"] = "l"
    labels_mismatch_table.align["Result"] = "l"
    labels_mismatch_table._max_width = {"Title":col_title_width}
   
    labels_old_table = PrettyTable(["PR Number", "Title", "PR Type", "Result"])
    labels_old_table.align["Title"] = "l"
    labels_old_table.align["Result"] = "l"
    labels_old_table._max_width = {"Title":col_title_width}

    labels_file = "./labels"
    labels_added = 0
    labels_mismatched = 0
    labels_all_bad = 0
    labels_matched = 0

    old_prs = 0
    label_names = {"type:bug": "Bug fix", "type:enhancement": "Enhancement", "type:experimental-feature": \
                "Experimental feature", "type:new_feature": "New feature", "type:cleanup": "Cleanup", \
                "type:breaking_change": "Breaking change"}


    ## TODO - get commit -> commit date from tag on master.
    ## Searching seems a waste

    #repo_tags = repo.get_tags()

    if prev_release_commit:
        print("Previous Release Commit SHA found in conf file, skipping pre release SHA search.\n")
        prev_release_sha = prev_release_commit
    else:
        print("Finding commit SHA for previous version " + prev_release_ver)
        for tag in repo_tags:
            if tag.name == prev_release_ver:
                prev_release_sha = tag.commit.sha
                #print(prev_release_sha)
    commit = repo.get_commit(sha=prev_release_sha)
    prev_release_commit_date=str(commit.commit.author.date.date())    #break

    if not commit:
        print("No starting point found via version tag or commit SHA")
        exit


    print("Enumerating Open PRs in '" + repo_name + "' \n")
    print("- Retrieving Pull Request Issues from Github")
    search_string = f"repo:" + repo_name + " is:open is:pr"
    issues = gh.search_issues(search_string)

    print("- Processing Open Pull Request Issues\n")
    for issue in issues:
        existing_labels = []
        label = []
        existing_label_names = []
        issue_matched_count = 0
        issue_labels_mismatch = 0
        issue_all_bad = 0
        issue_improvement_rename = 1
        bad_issue_count = 0
        no_match_count = 0
        issue_desc_exist = 0
        issue_label_exist = 0
        label_to_add = ''
        issue_missing_labels = 0

        pr = issue.repository.get_pull(issue.number)
        pr_num = str(pr.number)
        is_draft = pr.draft
        print("\n-- Checking OPEN pr#: " + pr_num)
        existing_labels = pr.labels

        for label in existing_labels:
            existing_label_names.append(label.name)
        
        if is_draft:
            prtype = 'Draft PR'
            if draft_pr_label not in existing_label_names:
                print("**** Daft PR missing wip label - adding label")
                labels_added_table.add_row([pr_num, pr.title.strip(), prtype, "WIP label added"])
                labels_added += 1
                if update_labels:
                    pr.add_to_labels("status:work-in-progress")
        if not is_draft:
            prtype = 'Open PR'
            if draft_pr_label in existing_label_names:
                print("**** PR with incorrect wip label - removing label")
                labels_added_table.add_row([pr_num, pr.title.strip(), prtype, "WIP label removed"])
                labels_added += 1
                if update_labels:
                    pr.remove_from_labels("status:work-in-progress")
        
        creation_date = pr.created_at
        check_date_old = datetime.now() - timedelta(days=365)
        check_date_very_old = datetime.now() - timedelta(days=2*365)
        if creation_date < check_date_very_old:
            print("**** More than 2 years old - adding label")
            old_prs += 1
            labels_old_table.add_row([pr_num, pr.title.strip(), "Very old PR", "Add label age:2years_plus"])
            if update_labels:
                pr.add_to_labels("age:2years_plus")
                try:
                    pr.remove_from_labels("age:1year_plus")
                except:
                    print("")
    
        elif creation_date < check_date_old:
            print("**** More than 1 year old - adding label")
            old_prs += 1
            labels_old_table.add_row([pr_num, pr.title.strip(), "Old PR", "Add label age:1year_plus"])
            if update_labels:
                pr.add_to_labels("age:1year_plus")

        for label_name in label_names:
            label_match(label_name, label_names[label_name])

        label_reconcile(prtype,label_to_add)

    print("\nEnumerating MERGED PRs in master\n")

    print("- Retrieving Pull Request Issues from Github")
    search_string = f"repo:apache/cloudstack is:merged merged:>={prev_release_commit_date}"
    issues = gh.search_issues(search_string)
    features = 0
    fixes = 0
    uncategorised = 0
    enhancements = 0
    match_found = 0

    print("\nProcessing Merged Pull Request Issues\n")
    for issue in issues:
        existing_labels = []
        label = []
        existing_label_names = []
        issue_matched_count = 0
        issue_labels_mismatch = 0
        issue_all_bad = 0
        issue_improvement_rename = 1
        bad_issue_count = 0
        no_match_count = 0
        issue_desc_exist = 0
        issue_label_exist = 0
        label_to_add = ''
        issue_missing_labels = 0

        pr = issue.repository.get_pull(issue.number)
        pr_num = str(pr.number)

        print("\n-- Checking MERGED pr#: " + pr_num)
        existing_labels = pr.labels

        for label in existing_labels:
            existing_label_names.append(label.name)

        for label_name in label_names:
            label_match(label_name, label_names[label_name])
        
        label_reconcile("MERGED",label_to_add)


    print("\nwriting tables")
    labels_to_add_txt = labels_added_table.get_string()
    labels_all_bad_txt = labels_all_bad_table.get_string()
    mismatched_labels_txt = labels_mismatch_table.get_string()
    labels_old_txt = labels_old_table.get_string()
    report_title = 'Results of ' + repo_name + ' open PR label trawling\n'
    underline_length = len(report_title)
    underline = '=' * underline_length


    with open(labels_file ,"w") as file:
        file.write(report_title)
        file.write(underline)

        file.write('\n\n%s PR labels matched \n\n' % str(labels_matched))

        file.write('\nLabels Updated in PRs:\n\n')
        file.write(labels_to_add_txt)
        file.write('\n%s PRs Updated\n\n\n' % str(labels_added))

        file.write('\nPR with label not matching description:\n\n')
        file.write(mismatched_labels_txt)
        file.write('\n%s PRs found\n\n\n' % str(labels_mismatched))

        file.write('PRs without label or description\n\n')
        file.write(labels_all_bad_txt)
        file.write('\n%s Unmatched PRs\n\n' % str(labels_all_bad))

        file.write('Old PRs\n\n')
        file.write(labels_old_txt)
        file.write('\n%s Old PRs\n\n' % str(old_prs))
    file.close()
    with open(labels_file ,"r") as file:
        print(file.read())
    file.close()
    print(("\nTable has been output to %s\n\n" % labels_file))
