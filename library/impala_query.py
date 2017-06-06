#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: impala_query
short_description: Run arbitrary queries on a impala database.
description:
   - Run arbitrary queries on impala instances from the current host.
   - The function of this module is primarily to allow running queries which
     would benefit from bound parameters for SQL escaping.
   - Query results are returned as "query_results" as a list of dictionaries.
     Number of rows affected are returned as "row_count".
   - Can read queries from a .sql file
version_added: "2.3"
options:
  db:
    description:
      - name of the database to run queries against
    required: true
    default: null
  port:
    description:
      - Database port to connect to.
    required: false
    default: 5432
  login_user:
    description:
      - User (role) used to authenticate with Impala
    required: false
    default: impala
  login_password:
    description:
      - Password used to authenticate with Impala
    required: false
    default: null
  login_host:
    description:
      - Host running Impala.
    required: false
    default: localhost
  positional_args:
    description:
      - A list of values to be passed as positional arguments to the query.
      - Cannot be used with named_args
  named_args:
    description:
      - A dictionary of key-value arguments to pass to the query.
      - Cannot be used with positional_args
  fact: |
      Append the query_results to this key value, making this new variable
      available to subsequent plays during an ansible-playbook run.
notes:
   - This module uses impyla, a Python impala database adapter. You must
     ensure that impyla is installed on the host before using this module. If
     the remote host is the impala server (which is the default case), then
     impala must also be installed on the remote host. For Ubuntu-based
     systems, install the impala, libpq-dev, and python-impyla packages
     on the remote host before using this module.
requirements: [ impyla ]
author: "Felix Archambault (@archf)
'''

EXAMPLES = '''
# Insert or update a record in a table with positional arguments
- impala_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: SELECT * FROM a_table WHERE a_column=%s AND b_column=%s
    positional_args:
    - "positional string value 1"
    - "positional string value 2"

# Insert or update a record in a table with named arguments
- impala_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: SELECT * FROM some_table WHERE a_column=%(a_value)s AND b_column=%(b_value)s
    named_args:
      a_value: "positional string value 1"
      b_value: "positional string value 2"

# Run queries from a '.sql' file
- impala_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: "{{playbook_dir}}/scripts/my_sql_query_file.sql"
    named_args:
      a_value: "positional string value 1"
      b_value: "positional string value 2"

# Run queries from a '.sql' file and assign result in a fact available at
# for the rest of the ansible runtime.
- impala_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: SELECT * FROM some_table WHERE a_column=%(a_value)s AND b_column=%(b_value)s
    named_args:
      a_value: "positional string value 1"
      b_value: "positional string value 2"
    fact: my_key
'''

RETURN = '''
query_results:
    description: list of dictionaries in column:value form
    returned: changed
    type: list
    sample: [{"Column": "Value1"},{"Column": "Value2"}]
row_count:
    description: number of affected rows by query, if applicable
    returned: changed
    type: int
    sample: 5
ansible_facts:
    "my_key": {
        "column1": "value",
        "column2": "value"
        }
'''

HAS_IMPYLA = False
try:
    from impala.dbapi import connect
except ImportError:
    pass
else:
    HAS_IMPYLA = True

import traceback
import re

from ansible.module_utils.six import iteritems
from ansible.errors import AnsibleError

# ===========================================
# Impala module specific support methods.
#
# ===========================================
# Module execution.

def main():

    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(default='impala'),
            login_password=dict(default=None, no_log=True),
            login_host=dict(default=''),
            login_unix_socket=dict(default=''),
            port=dict(type='int', default=21050),
            db=dict(default=None),
            query=dict(type="str"),
            positional_args=dict(type="list"),
            named_args=dict(type="dict"),
            fact=dict(default=None),
            query_log=dict(type="str")
        ),
        supports_check_mode=False,
        mutually_exclusive=[
            ["positional_args", "named_args"]
        ],
    )

    if not HAS_IMPYLA:
        module.fail_json(msg="the python impyla module is required")

    # To use defaults values, keyword arguments must be absent, so
    # check which values are empty and don't include in the **kw
    # dictionary
    params_map = {
        "login_host":"host",
        "login_user":"user",
        "login_password":"password",
        "port":"port",
        "db": "database"
    }
    kw = dict((params_map[k], v) for (k, v) in iteritems(module.params)
              if k in params_map and v != "")

    is_localhost = "host" not in kw or kw["host"] == "" or kw["host"] == "localhost"

    if is_localhost and module.params["login_unix_socket"] != "":
        kw["host"] = module.params["login_unix_socket"]

    try:
        db_connection = connect(**kw)
        cursor = db_connection.cursor(user=kw['user'])
    except Exception:
        e = get_exception()
        module.fail_json(msg="Unable to connect to database: {0}".format(str(e)), exception=traceback.format_exc())

    # if query is a file, load the file and run it
    query = module.params["query"]

    if query.endswith('.sql'):
        try:
            with open(query, 'r') as fh:
                sql_file = fh.read().strip('\n')
        except Exception:
            e = get_exception()
            module.fail_json(msg="Unable to find '%s' in given path: %s" % (query, e))

    if not module.params['query_log']:
        module.fail_json(msg="No impala query log file path provided, can't continue the run")

    try:
        query_log = open(module.params['query_log'], 'a+')
        query_log.seek(0)
    except Exception:
        e = get_exception()
        module.fail_json(msg="Unable to find '%s' in given path: %s" % (module.params['query_log'], e))

    arguments = None

    # checks that the string is not empty, and that we split only at the end of lines
    compiled_regex = re.compile(r';\s+')
    queries = [line for line in compiled_regex.sub(';\n', sql_file).split(';\n') if line] if sql_file else [query]

    # read through all the already ran queries in the query log
    already_ran_queries = [line for line in query_log.read().strip('\n').split(';\n') if line]

    for query in queries:
        if query not in already_ran_queries:
            # prepare args
            if module.params["positional_args"] is not None:
                arguments = module.params["positional_args"]

            elif module.params["named_args"] is not None:
                arguments = module.params["named_args"]

            try:
                cursor.execute(query, arguments)
                query_log.write(query + '\n')
            except Exception:
                e = get_exception()
                module.fail_json(msg="Unable to execute query '%s': %s" % (query, e),
                                     query_arguments=arguments)

    if query_log:
        query_log.close()

    ansible_facts = {}
    query_results = []
    if cursor.rowcount > 0:
        # There's no good way to return results arbitrarily without inspecting
        # the SQL, so we act consistent and return the empty set when there's
        # nothing to return.
        try:
            query_results = [
                    {name: row[idx] for idx, name in enumerate(cursor.description)}
                    for row in cursor.fetchall()]
        except impala.error.ProgrammingError:
            pass

        rowcount = len(query_results)
        fact = module.params["fact"]
        if fact is not None:
            ansible_facts = {fact: query_results}
        else:
            ansible_facts = {}
    else:
        rowcount = 0

    statusmessage = cursor.status()

    # there's no easy way to check for this on impala
    changed = True
    db_connection.commit()
    db_connection.close()

    module.exit_json(changed=changed, stout_lines=statusmessage,
                     query_results=query_results,
                     ansible_facts=ansible_facts,
                     rowcount=rowcount)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.database import *

if __name__ == '__main__':
    main()
