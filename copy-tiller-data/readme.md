This tool allows users to easily copy their financial data from one Tiller workbook to another. It will copy the contents of the four Tiller Foundation Sheets (Transactions, Balance History, Accounts, and Categories). The script will also copy the contents of the custom columns included in the [Cashflow and Networth Analysis Workbook](https://jaqkofalltrades.com/posts/cashflow-and-networth-analysis-workbook/) if they exist in the source workbook.

To use the script, run the executable or python script and drag your source and destination workbooks into the console window that pops up.

To create exe:
`pyinstaller -F copy_tiller_data.py`

## Remove duplicates (`remove_duplicates.py`)

After copying your data into a fresh spreadsheet and running the Tiller add-on's
fill tool, Tiller doesn't recognise the new sheet and re-adds every transaction,
creating duplicates: the copy you already categorised, plus a fresh
*uncategorised* copy.

This tool finds those duplicates and deletes the uncategorised copy, keeping the
categorised one. Duplicates are matched on the bank fields that survive a
re-fill (`Date`, `Amount`, `Account`, and `Full Description`) — not on
`Transaction ID`/`Date Added`, which Tiller regenerates on every fill.

For each set of duplicates: if one copy is categorised, that one is kept and the
uncategorised copy is deleted; if *every* copy is uncategorised, the first one is
kept and the rest are deleted.

It prints a compact, per-month report of everything it removes, makes a
timestamped `.xlsx` backup of the workbook, and asks for confirmation before
saving.

To use it, run the script and drag your workbook into the console window.

To create exe:
`pyinstaller -F remove_duplicates.py`
