# Data sources

One source. No API key, no account.

| Item | Value |
|---|---|
| Dataset | Online Retail II, UCI Machine Learning Repository, dataset id 502 |
| Creator | Daqing Chen (2012) |
| DOI | https://doi.org/10.24432/C5CG6D |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), stated on the UCI dataset page |
| Download | https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip (HTTP 200, no key) |
| Zip | 45,622,418 bytes, sha256 `572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb` |
| Workbook | `online_retail_II.xlsx`, 45,622,278 bytes, sha256 `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980` |
| Retrieved | 2026-10-11 (exact timestamp in `data/manifests/raw_manifest.json`) |
| Attribution (site footer) | Online Retail II, Daqing Chen (2012), UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D, licensed CC BY 4.0. Derived aggregates, modified; not the original file. |

## What was verified on the first read (OBSERVED, from the file)
- Sheets: `Year 2009-2010` (525,461 rows) and `Year 2010-2011` (541,910 rows); total 1,067,371, matching UCI's `num_instances`.
- Columns: Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country.
- Date range 2009-12-01 07:45 to 2011-12-09 12:50 (naive timestamps, UK local time per the source description).
- The two sheets overlap: 22,523 rows dated 2010-12-01 to 2010-12-09 appear in both, and the two copies are identical
  (multiset difference is empty in both directions). They are counted once.
- Missing Customer ID: 107,927 rows (sheet 1) and 135,080 rows (sheet 2). Missing Description: 2,928 and 1,454.
- Raw workbook rows: Invoice starts with `C` in 10,206 + 9,288 rows; Quantity < 0 in 12,326 + 10,624 rows; Price <= 0 in 3,690 + 2,517 rows.
- Six `A` invoices (stock code `B`, "Adjust bad debt") carry prices of -53,594.36 to +11,062.06 GBP.
- Unit price is in GBP (the source describes a UK-registered retailer; the currency is not a column).

The full row and amount ledger, produced by the pipeline, is `reconciliation.json` and `data/manifests/cleaning_ledger.json`.

## Storage
The workbook and zip live in `data/raw/` (gitignored). `pipelines/ingestion/fetch.py` re-creates them; the manifest with
sha256 is committed. Interim Parquet and the DuckDB star schema are gitignored and rebuilt by `pipelines/run_all.py`.

## What the source is not
- Not demographic: no age, gender, income, or location finer than country. None are invented.
- Not a store: online, wholesale-like gift-ware, many buyers are trade customers. Do not read "customer" as "household".
- Not a random sample: it is the complete ledger of one company for 24 months, with a single holiday season in each year.
- No cost, margin, stock or supplier data. Newsvendor costs are therefore SIMULATED assumptions.
- No product category column. Product families are DERIVED by a published keyword rule.
