-- All 1,067,371 source rows, one-to-one with the workbook (raw_id), written by pipelines/ingestion/extract.py.
select * from read_parquet('data/interim/raw_lines.parquet')
