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

global tmp_dir
global output_file_name
global destination

working_dir = os.environ.get('destination')
config_file = f"{working_dir}/conf.txt"

with open(config_file ,"w") as file:
    file.write('{\n')
    if 'gh_token' in os.environ:
        gh_token = os.environ.get('gh_token')
        file.write('    "--gh_token":"' + str(gh_token) + '",\n')

    if 'prev_release_commit_sha' in os.environ:
        prev_release_commit_sha = os.environ.get('prev_release_commit_sha')
        file.write('    "--prev_release_commit_sha":"' + str(prev_release_commit_sha) + '",\n')

    if 'branch' in os.environ:
        branch = os.environ.get('branch')
        file.write('    "--branch":"' + str(branch) + '",\n')

    if 'repo_name' in os.environ:
        repo_name = os.environ.get('repo_name')
        file.write('    "--repo_name":"' + str(repo_name) + '",\n')

    if 'gh_base_url' in os.environ:
        gh_base_url = os.environ.get('gh_base_url')
        file.write('    "--gh_base_url":"' + str(gh_base_url) + '",\n')

    if 'col_title_width' in os.environ:
        col_title_width = os.environ.get('col_title_width')
        file.write('    "--col_title_width":"' +  str(col_title_width) + '",\n')

    if 'tmp_dir' in os.environ:
        tmp_dir = os.environ.get('tmp_dir')
        file.write('    "--tmp_dir":"' + str(tmp_dir) + '",\n')
    else:
        file.write('    "--tmp_dir":"/tmp,"\n')

    if 'destination' in os.environ:
        destination = os.environ.get('destination')
        file.write('    "--destination":"' + str(destination) + '",\n')
    else:
        file.write('    "--destination":"/opt",\n')

    if 'output_file_name' in os.environ:
        output_file_name = os.environ.get('output_file_name')
        file.write('    "--output_file_name":"' + str(output_file_name) + '",\n')
    else:
        file.write('    "--output_file_name":"prs.rst",\n')
        
    if 'update_labels' in os.environ:
        update_labels = os.environ.get('update_labels')
        file.write('    "--update_labels":"' + str(update_labels) + '",\n')
     
    file.write('    "--docker_created_config":"True"')
    file.write('\n}\n   ')   
    file.close()

    # Clear vars from environment 'memory'
    os.environ.clear()
