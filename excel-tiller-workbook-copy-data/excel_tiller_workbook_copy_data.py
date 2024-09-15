from datetime import time
import pandas as pd
import xlwings as xw
from tqdm import tqdm

source_file = input("Enter the path to the source Excel file: ").strip('"')
destination_file = input("Enter the path to the destination Excel file: ").strip('"')

transactions_columns = [
    'Date', 'Description', 'Category', 'Amount', 'Labels', 'Notes', 'Account',
    'Account #', 'Institution', 'Month', 'Week', 'Transaction ID', 'Account ID',
    'Check Number', 'Full Description', 'Date Added'
]
account_columns = ['Account', 'Class Override', 'Group', 'Hide']
balance_history_columns = [
    'Date', 'Time', 'Account', 'Account #', 'Account ID', 'Balance ID',
    'Institution', 'Balance', 'Month', 'Week', 'Type', 'Class', 'Account Status',
    'Unique Account Identifier', 'Date Added'
]
categories_columns = [
    'Category', 'Group', 'Type', 'Hide From Reports'
]

sheets = {
    "Transactions": transactions_columns,
    "Accounts": account_columns,
    "Balance History": balance_history_columns,
    "Categories": categories_columns
}

app = xw.App(visible=False)
workbook = xw.Book(destination_file)

try:
    for sheet_name, columns in tqdm(sheets.items(), desc="Copying sheets", unit="sheet"):
        try:
            df = pd.read_excel(source_file, sheet_name=sheet_name)
            df = df[columns]

            # Convert datetime.time objects to string representations to allow writing to Excel
            df = df.map(lambda x: str(x) if isinstance(x, time) else x)

            worksheets = workbook.sheets[sheet_name]
            worksheets.range('A2').options(expand='table').clear_contents()

            for col_idx, col_name in enumerate(df.columns, start=1):
                try:
                    worksheets.range(2, col_idx).options(transpose=True).value = df[col_name].tolist()
                except Exception as e:
                    print(f"Error writing column '{col_name}' to sheet '{sheet_name}': {str(e)}")

        except Exception as e:
            print(f"Error processing sheet '{sheet_name}': {str(e)}")

    workbook.save()
except Exception as e:
    print(f"An error occurred: {str(e)}")
finally:
    workbook.close()
    app.quit()

print("Data copied successfully!")
