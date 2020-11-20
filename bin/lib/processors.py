
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


import os
import re
import subprocess
from datetime import datetime
import subprocess
import shutil
import pygit2

def get_commits(repo, branch, tmp_dir):

    global prev_release_commit_date

    leading_4_spaces = re.compile('^    ')

    print("- Cloning repo to avoid too many Github API calls, sorry, this could take a while")
    dir_now = os.getcwd()
    #if os.path.isdir(tmp_repo_dir):
    #    shutil.rmtree(tmp_repo_dir)
    #os.mkdir(tmp_repo_dir)
    os.chdir(tmp_dir)
    repoClone = pygit2.clone_repository(repo.git_url, tmp_dir, bare=True, checkout_branch=branch)
    lines = subprocess.check_output(
        ['git', 'log'], stderr=subprocess.STDOUT
            ).decode("utf-8").split("\n")
    commits = []
    current_commit = {}
    def save_current_commit():
        title = current_commit['message'][0]
        message = current_commit['message'][1:]
        if message and message[0] == '':
            del message[0]
        current_commit['title'] = title
        current_commit['message'] = '\n'.join(message)
        commits.append(current_commit)
    for line in lines:
        if not line.startswith(' '):
            if line.startswith('commit '):
                if current_commit:
                    save_current_commit()
                    current_commit = {}
                current_commit['hash'] = line.split('commit ')[1]
            else:
                try:
                    key, value = line.split(':', 1)
                    current_commit[key.lower()] = value.strip()
                except ValueError:
                    pass
        else:
            current_commit.setdefault(
                'message', []
            ).append(leading_4_spaces.sub('', line))
    if current_commit:
        save_current_commit()
    os.chdir(dir_now)
    return commits

def get_reverted_commits(repo, branch, prev_release_commit_date, tmp_repo_dir):

    revertedcommits = []
    previous_commit_date = datetime.strptime(prev_release_commit_date, '%Y-%m-%d').date()
    commits = get_commits(repo, branch, tmp_repo_dir)
    for commit in commits:
        thiscommit = commit['title']
        reverted = re.match('^Revert "', thiscommit)
        if reverted:
            commitdatestr = commit['date']
            date_time_str = ' '.join(commitdatestr.split(" ")[:-1])
            commitdate = datetime.strptime(date_time_str, '%c').date()
            if commitdate > previous_commit_date:
                revertedcommit = re.search('.*This reverts commit ([A-Za-z0-9]*).*', commit['message'])
                revertedcommits.append(revertedcommit.group(1))
    return revertedcommits
