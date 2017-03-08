/* test a query using psycopg2 , named_args and ansible_facts */
SELECT table_name, date_time FROM etl_merged_tables order by table_name limit 5;
SELECT table_name, date_time FROM etl_merged_tables order by date_time desc limit 12;
