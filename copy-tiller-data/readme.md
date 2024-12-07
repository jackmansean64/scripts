This tool allows users to easily copy their financial data from one Tiller workbook to another. It will copy the contents of the four Tiller Foundation Sheets (Transactions, Balance History, Accounts, and Categories). The script will also copy the contents of the custom columns included in the [Cashflow and Networth Analysis Workbook](https://jaqkofalltrades.com/posts/cashflow-and-networth-analysis-workbook/) if they exist in the source workbook.

To use the script, run the executable or python script and drag your source and destination workbooks into the console window that pops up.

To create exe:
`pyinstaller -F copy_tiller_data.py`  
