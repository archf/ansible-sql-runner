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

ANSIBLE_METADATA = {'status': ['stableinterface'],
                    'supported_by': 'community',
                    'version': '1.0'}
DOCUMENTATION = '''
---
module: postgresql_query
short_description: Run arbitrary queries on a postgresql database.
description:
   - Run arbitrary queries on postgresql instances from the current host.
   - The function of this module is primarily to allow running queries which
     would benefit from bound parameters for SQL escaping.
   - Query results are returned as "query_results" as a list of dictionaries.
     Number of rows affected are returned as "row_count".
   - Can read queries from a .sql file
version_added: "2.3"
options:
  db:
    description:
      - name of database to connect to.
    required: true
    default: null
  port:
    description:
      - Database port to connect to.
    required: false
    default: 5432
  user:
    description:
      - User (role) used to authenticate with PostgreSQL
    required: false
    default: postgres
  password:
    description:
      - Password used to authenticate with PostgreSQL
    required: false
    default: null
  host:
    description:
      - Host running PostgreSQL.
    required: false
    default: localhost
  unix_socket:
    description:
      - Path to a Unix domain socket for local connections
    required: false
    default: null
  sslmode:
    description:
      - SSL settings for the database connection.
      - allowed values are "disable","allow","prefer","require",
        "verify-ca","verify-full"
      - See http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING
    required: false
    default: prefer
  query:
    description:
      - SQL query to run. Variables can be escaped with psycopg2 syntax.
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
   - The default authentication assumes that you are either logging in as or
     sudo'ing to the postgres account on the host.
   - This module uses psycopg2, a Python PostgreSQL database adapter. You must
     ensure that psycopg2 is installed on the host before using this module. If
     the remote host is the PostgreSQL server (which is the default case), then
     PostgreSQL must also be installed on the remote host. For Ubuntu-based
     systems, install the postgresql, libpq-dev, and python-psycopg2 packages
     on the remote host before using this module.
requirements: [ psycopg2 ]
author: "Felix Archambault (@archf), Will Rouesnel (@wrouesnel)"
'''

EXAMPLES = '''
# Insert or update a record in a table with positional arguments
- postgresql_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: SELECT * FROM a_table WHERE a_column=%s AND b_column=%s
    positional_args:
    - "positional string value 1"
    - "positional string value 2"

# Insert or update a record in a table with named arguments
- postgresql_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: SELECT * FROM some_table WHERE a_column=%(a_value)s AND b_column=%(b_value)s
    named_args:
      a_value: "positional string value 1"
      b_value: "positional string value 2"


# Run queries from a '.sql' file
- postgresql_query:
    db: acme
    user: django
    password: ceec4eif7ya
    query: "{{playbook_dir}}/scripts/my_sql_query_file.sql"
    named_args:
      a_value: "positional string value 1"
      b_value: "positional string value 2"

# Run queries from a '.sql' file and assign result in a fact available at
# for the rest of the ansible runtime.
- postgresql_query:
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

HAS_PSYCOPG2 = False
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    pass
else:
    HAS_PSYCOPG2 = True

import traceback


# embedding content of lib/ansible/module/utils for ansible 2.2 while this
# module is not upstream. Later on replace that class by:
# import ansible.module_utils.postgres as pgutils

class Postgres():
    @staticmethod
    def ensure_libs(sslrootcert=None):
        if not HAS_PSYCOPG2:
            raise LibraryError('psycopg2 is not installed. we need psycopg2.')
        if sslrootcert and psycopg2.__version__ < '2.4.3':
            raise LibraryError('psycopg2 must be at least 2.4.3 in order to use the ssl_rootcert parameter')

        # no problems
        return None

    @staticmethod
    def postgres_common_argument_spec():
        return dict(
            login_user        = dict(default='postgres'),
            login_password    = dict(default='', no_log=True),
            login_host        = dict(default=''),
            login_unix_socket = dict(default=''),
            port              = dict(type='int', default=5432),
            ssl_mode          = dict(default='prefer', choices=['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']),
            ssl_rootcert      = dict(default=None),
        )
pgutils = Postgres()

from ansible.module_utils.six import iteritems
from ansible.errors import AnsibleError

# ===========================================
# PostgreSQL module specific support methods.
#

# todo: move query in here
def run_query():
    pass


# ===========================================
# Module execution.
#

def main():
    argument_spec = pgutils.postgres_common_argument_spec()

    argument_spec.update(dict(
        db=dict(default=None),
        query=dict(type="str"),
        positional_args=dict(type="list"),
        named_args=dict(type="dict"),
        fact=dict(default=None),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ["positional_args", "named_args"]
        ],
    )

    if not HAS_PSYCOPG2:
        module.fail_json(msg="the python psycopg2 module is required")

    changed = False

    # To use defaults values, keyword arguments must be absent, so
    # check which values are empty and don't include in the **kw
    # dictionary
    params_map = {
        "login_host":"host",
        "login_user":"user",
        "login_password":"password",
        "port":"port",
        "db": "database",
        "ssl_mode":"sslmode",
        "ssl_rootcert":"sslrootcert"
    }
    kw = dict( (params_map[k], v) for (k, v) in iteritems(module.params)
              if k in params_map and v != '' and v is not None)

    # If a login_unix_socket is specified, incorporate it here.
    is_localhost = "host" not in kw or kw["host"] == "" or kw["host"] == "localhost"

    if is_localhost and module.params["login_unix_socket"] != "":
        kw["host"] = module.params["login_unix_socket"]

    # if db is None:
    #     module.fail_json(msg="a database must be specified")

    try:
        pgutils.ensure_libs(sslrootcert=module.params.get('ssl_rootcert'))
        # module.exit_json(msg=kw)
        db_connection = psycopg2.connect(**kw)
        # Using RealDictCursor allows access to row results by real column name
        cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception:
        e = get_exception()
        module.fail_json(msg="unable to connect to database: {0}".format(str(e)), exception=traceback.format_exc())

    # if query is a file, load the file and run it
    query = module.params["query"]
    if query.endswith('.sql'):
        try:
            query = open(query, 'r', encoding="utf8").read().strip('\n')
            # module.fail_json(msg="query :'%s'" % query)
        except Exception:
            e = get_exception()
            module.fail_json(msg="Unable to find '%s' in given path." % query)

    # module.exit_json(msg="query args: %s" % module.params["positional_args"])
    arguments = None

    # prepare args
    if module.params["positional_args"] is not None:
        arguments = module.params["positional_args"]

    elif module.params["named_args"] is not None:
        arguments = module.params["named_args"]

    try:
        cursor.execute(query, arguments)
    except Exception:
        e = get_exception()
        module.fail_json(msg="Unable to execute query: %s" % e,
                         query_arguments=arguments)

    query_results = []
    if cursor.rowcount > 0:
        # There's no good way to return results arbitrarily without inspecting
        # the SQL, so we act consistent and return the empty set when there's
        # nothing to return.
        try:
            query_results = cursor.fetchall()
        except psycopg2.ProgrammingError:
            pass

        rowcount = len(query_results)
        fact = module.params["fact"]
        ansible_facts = {fact: query_results}

        # to populate a fact, query must return only one row
        # if fact is not None and rowcount != 1:
        #     module.fail_json(msg="Unable to assign result to fact '%s': query must return only one row"
        #                      % fact,
        #                      query_results=query_results,
        #                      rowcount=rowcount)
        # else:
        #     ansible_facts = {fact : query_results[0]}

    else:
        rowcount = 0

    statusmessage = cursor.statusmessage

    # todo: naive check, look for the lack of 'altering/writing' commands
    # set changed flag only on non read-only command
    if "SELECT" in statusmessage:
        changed = False
    else:
        changed = True

    if changed:
        if module.check_mode:
            db_connection.rollback()
        else:
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
