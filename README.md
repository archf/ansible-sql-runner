# ansible-sql-runner

Run a sequence of sql queries or scripts on a target db.

## Requirements

### Ansible version

Minimum required ansible version is 2.2.

### Other considerations

It depends on the SQL engine you use. Here's the list of supported SQL engines
and their requirements, so be ready with your own or get here:-

  * postgresql requires [psycopg2](http://initd.org/psycopg/)
  * impala requires [impyla](https://github.com/cloudera/impyla)
  * phoenix requires the [phoenixdb ](http://python-phoenixdb.readthedocs.io/en/latest/)

## Description

There are two ways you can use this role.

**The filepath mode or fileglob mode**

In this mode, you will iterate over all recursively registered SQL scripts under
a given directory.

  * All SQL scripts under directory will be run against the same `sql_engine`
  * All scripts will be run in alphabetical order

**The declarative mode or advanced mode**

In this mode, you iterate over queries as defined in a precise input data
structure. This enables more capabilities. See below.

On complex setups, this allows your to run batch of queries while
alternating sql engine. For instance, you can
  1. run scripts on postgres
  2. switch to impala
  3. than go back to postgres
  4. than you switch to phoenix
  5. ...

  all without ever leaving the role.

Role invoked this way can perform one of both following tasks or loop.
  1. The first loop can lookup data on databases and can append results to
    * a variable in the `ansible_facts`
    * to a key you specify inside a special `dict` named `sql_facts`
  2. The second loop can perform various queries that can be templated
    * using entries in the `sql_facts` hash populated in the first loop
    * using other data available in the ansible runtime namespace

During a single role invocation, your credentials (user//password) will
be fetched from a dictionary that must be structure on a per `sql_engine` basis.

### Playbook examples

Given those variables commonly defined no mather the way you use this role.

```yaml
# putting the user/team at the second level level allows to naturally pass
# the role a data structure with everything needed to access the different
# engines for a complex maintenance activity when impersonating a specific
# a specific individual/group. It also allows to have even less levels.

# 3 levels example
app_sql_conn_creds:
  # per user/team then engine creds
  me:
    postgres:
      user: myuser
      password: 'userpassword'

  thisotherteam:
    postgres:
      user: teamname
      password: "teampassword"

# 2 levels example
app_sql_conn_creds:
    postgres:
      user: myuser
      password: 'userpassword'
    impala:
      user: teamname
      password: "teampassword"

app_sql_conn_targets:
  # contains ansible's postgresql_query module's arguments defining the
  # target
  postgres:
    host: <hostname or ip>
    port: <optional value (defaults to 5432 when using postgresql_query module)>
    ssl_mode: <optional value, defaults to 'prefer' for postgresql modules>
    ssl_rootcert: <optional value>
    unix_socket: <optional value>
    engine: postgres

  impala:
    host: <hostname or ip>
    user: <impala user>
    db: dbname
    engine: impala

# `sql_db` is a loose variable and is no tied to the engine because
#   1. A target might have multiple databases.
#   2. It may not exist and role objective would be to create it. This is
#       makes it easier to be consistent with other role coded with that
#       purpose in mind.
#   3. Has to be passed directly when using the fileglob mode
#   4. It is defined has 'omit' in the default vars.
sql_db: dbname
```

See also overridables variables defined in the [Default vars](#Default-vars)

Exact input data structures depends of the way you use the role. In any cases
either you let it reach for ansible globally defined variables or you pass it
explicitly what it expects. Refer to examples below for example usage.

**Fileglob mode example**

For that mode since you can interact with only one target//db, things are
much more specific.

```yaml
  - hosts: localhost

    vars:
      # change the path to some place of your choosing.
      sql_history_logfile: <path to the sql_history_logfile>

    roles:
      - { role: sql-runner,
          sql_conn_targets: "{{app_sql_conn_targets['postgres']}}",
          sql_conn_creds: "{{app_sql_conn_creds['me']['postgres']}}",
          sql_db: 'mydb',
          sql_scripts_dir: "{{playbook_dir}}/scripts/postgres_query_test/*"
          }
  ```

**Advanced mode example**

  ```yaml
  - hosts: localhost

    roles:
      - { role: sql-runner,
          sql_conn_targets: "{{app_sql_conn_targets}}",
          sql_conn_creds: "{{app_sql_conn_creds['me']}}",
          sql_queries: "{{app_sql_advanced_tasks}}"
          }
```

Where `app_sql_advanced_tasks` is defined as below. See inlined explanations.

```yaml
app_sql_advanced_tasks:

    # Fist loop that optionaly gather facts that can be used to alter later
    # scripts that contains named placeholder. Those should be mainly 'read'
    # queries that do not alter the database schema.
    sql_var_queries:

        # engine will default the the one in sql_conn_target if unspecified.
        # In that case
      - engine: postgres
        db: mydb
        # List of queries to run against a given db//engine.
        queries:
          - name: my_var
            query: "SELECT this_var FROM that_table limit %s"
            positional_args:
              - 1

          # run query from a file where path is relative to playbook dir
          - name: other_var
            db: <override 'mydb' value for this query>
            query: "{{playbook_dir}}/scripts/postgres/test_postgres_query_return_facts.sql"
            named_args:
              nb_results: 6

      - engine: impala
        db: myimpaladb
        queries:
        - name: impala_var
          query: <sql query where result will be assigned to impala_var key>

      # This will populate a `sql_facts` dict globally available for the rest of the
      # ansible runtime. You can pass that dict as a named_args to `postgresql_query`
      # or `impala_query` module.

      # ex:
      # "sql_facts":
      #   {
      #     "my_var": "my_value",
      #     "other_var": "other_value"
      #     "impala_var": impala_value
      #   }
      # ```

    # adm is a memotechnic shorthand for (admin|administration) queries
    sql_adm_queries:
      - engine: postgres
        db: mydb
        # List of queries that each contains a list of script to execute against an
        # sql engine perform. If scripts suffix is .sql.j2, it will be templated
        # locally first. All scripts are run in the defined order.
        queries:
          - query: "{{playbook_dir}}/scripts/postgres/test_postgres_query_use_facts.sql"
            named_args: "{{sql_facts}}"

      - engine: postgres
        # enable autocommit to allow database creation. Alternatively, enable
        # this globally but keep in mind your queries will be run even
        # in check_mode.
        autocommit: True
        # List of queries to run
        queries:
            query: "create database myotherdb"
            query: "create database mythirddb"

      - engine: impala
        db: myimpaladb
        queries:
          - query: a impala query
  ```

## Role Variables

### Variables conditionally loaded

None.

### Default vars

Defaults from `defaults/main.yml`.

```yaml
# Disable role debugging by default.
sql_runner_debug: False

# Empty fact dictionary to store query results for later use You can
# pre-populate it you want. This will be passed to sql query modules as
# named_args.
sql_facts: {}

# This file logs a list of sql queries that were performed. It allows
# rerunning the playbook without the executing sql scripts that were already
# done. Each line is either:
# - An SQL query
# - the full path of an sql scripts
sql_history_logfile: "{{playbook_dir}}/tmp/sql_history.log"

# Disable the autocommit behavior by default. Set this to true for instance if
# you happen to run a query that creates a database in postgres else psycopg2
# execution will fail. It is recommended however that you use the module
# postgresql_db module.  Running in check_mode with this will indeed execute
# all queries.
sql_autocommit: False

# This allows to fallback on a globally defined db name that exists on different
# sql_engine//targets when running in advanced mode. This is MUTUALLY EXCLUSIVE
# with sql_autocommit IF you create databases in advanced mode. Your play may
# fail. You have been warned.
sql_db: omit

```

## Todo

  * test ansible timeout behavior when logging long query
  * add jinja templating support for file queries in sql_advanced_mode?
  * better tests and document check mode usage

## License

MIT.

## Author Information

Felix Archambault.
