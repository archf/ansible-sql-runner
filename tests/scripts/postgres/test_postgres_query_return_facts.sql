SELECT date_time, table_name FROM etl_merged_tables order by date_time desc limit %(nb_results)s;
