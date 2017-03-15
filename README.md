# ansible-sql-runner

Run a sequence of sql queries or scripts on a target db.

## Requirements

### Ansible version

Minimum required ansible version is 2.2.

### Other considerations

It depends on the SQL engine you use. Here's the list of supported SQL engines
and their requirements.

  * postgresql requires [psycopg2](http://initd.org/psycopg/)
  * impala requires [impyla](https://github.com/cloudera/impyla)
  * phoenix requires the [phoenixdb ](http://python-phoenixdb.readthedocs.io/en/latest/)


## Description

There are two ways you can use this role.

**The filepath mode or fileglob mode**

In this mode, your iterate over all recursively registered SQL scripts under
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

Given those defined variables.

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

# `sql_db` is a loose variable and is no tied to the engine because
#   1. A target might have multiple databases.
#   2. It may not exist and role objective would be to create it. This is
#       makes it easier to be consistent with other role coded with that
#       purpose in mind.
#   3. Has to be passed directly when using the fileglob mode
sql_db: dbname
```

Input data structures depends of the way you use the role. In any cases either
you let it reach for ansible globally defined variables or you pass it
explicitly what it expects.

**Fileglob mode example**

For that mode since you can interact with only one target//db, things are
much more specific.

```yaml
  - hosts: localhost

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

  - { role: sql-runner,
      sql_conn_targets: "{{app_sql_conn_targets}}",
      sql_conn_creds: "{{app_sql_conn_creds['me']}}",
      sql_queries: "{{app_sql_advanced_tasks}"
      }
```

Where `my_sql_advanced_tasks` is defined as below. See inlined explanations.

```yaml
app_sql_advanced_tasks:

    # Fist loop that optionaly gather facts that can be used to alter later
    # scripts that contains named placeholder. Those should be mainly 'read'
    # queries that do not alter the database state.
    sql_var_queries:

        # engine will default the the one in sql_conn_target if unspecified.
        # In that case
      - engine: postgres
        db: mydb
        # List of queries to run
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
        queries:
        - name: impala_var
          query: <sql query to gather to assign impala_var value>

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

    # List of queries that each contains a list of script to execute against an
    # sql engine perform. If scripts suffix is .sql.j2, it will be templated
    # locally first. All scripts are run in the defined order.
    # adm is a memotechnic shorthand for (admin|administration|maintenance) queries
    sql_adm_queries:
      - engine: postgres
        queries:
          - query: "{{playbook_dir}}/scripts/postgres/test_postgres_query_use_facts.sql"
            named_args: "{{sql_facts}}"

      - engine: impala
        queries:
          - query: a second query
  ```


## Role Variables

### Variables conditionally loaded

None.

### Default vars

Defaults from `defaults/main.yml`.

```yaml
# Disable role debugging by default.
db_upgrader_debug: True

# Empty fact list that will be populated with results for later use as
# named_args.
sql_facts: {}

# This file logs a list of sql queries that were performed. It allows
# rerunning the playbook without the executing sql scripts that were already
# done. Each line is either:
# - An SQL query
# - the full path of an sql scripts
sql_history_logfile: "{{playbook_dir}}/tmp/sql_history.log"

```


## Installation

### Install with Ansible Galaxy

```shell
ansible-galaxy install archf.sql-runner
```

Basic usage is:

```yaml
- hosts: all
  roles:
    - role: archf.sql-runner
```

### Install with git

If you do not want a global installation, clone it into your `roles_path`.

```shell
git clone git@github.com:archf/ansible-sql-runner.git /path/to/roles_path
```

But I often add it as a submdule in a given `playbook_dir` repository.

```shell
git submodule add git@github.com:archf/ansible-sql-runner.git <playbook_dir>/roles/sql-runner
```

As the role is not managed by Ansible Galaxy, you do not have to specify the
github user account.

Basic usage is:

```yaml
- hosts: all
  roles:
  - role: sql-runner
```

## Ansible role dependencies

None.

## Todo

  * test ansible timeout behavior when logging long query
  * add jinja templating support for file queries in sql_advanced_mode?

## License

MIT.

## Author Information

Felix Archambault.

---
This README was generated using ansidoc. This tool is available on pypi!

```shell
pip3 install ansidoc

# validate by running a dry-run (will output result to stdout)
ansidoc --dry-run <rolepath>

# generate you role readme file
ansidoc <rolepath>
```

You can even use it programatically from sphinx. Check it out.