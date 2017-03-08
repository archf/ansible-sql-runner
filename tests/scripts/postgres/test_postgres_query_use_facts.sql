/* test a query using psycopg2 , named_args and ansible_facts */
SELECT table_name, date_time FROM etl_merged_tables where date_time = %(date_time_var)s;
SELECT table_name, date_time FROM etl_merged_tables order by date_time desc limit 12;
