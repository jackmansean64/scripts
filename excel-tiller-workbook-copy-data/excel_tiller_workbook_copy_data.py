from datetime import time
import pandas as pd
import xlwings as xw
from tqdm import tqdm

# Request file paths from the user
source_file = input("Enter the path to the source Excel file: ").strip('"')
destination_file = input("Enter the path to the destination Excel file: ").strip('"')

# Define the columns for each table
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

# Read and filter the data
sheets = {
    "Transactions": transactions_columns,
    "Accounts": account_columns,
    "Balance History": balance_history_columns,
    "Categories": categories_columns
}

# Open the destination workbook using xlwings
app = xw.App(visible=False)
wb = xw.Book(destination_file)

try:
    for sheet_name, columns in tqdm(sheets.items(), desc="Copying sheets", unit="sheet"):
        # Read data from the source file
        df = pd.read_excel(source_file, sheet_name=sheet_name)
        df = df[columns]

        # Convert datetime.time objects to string representations
        for col in df.columns:
            if pd.api.types.is_datetime64_dtype(df[col]):
                df[col] = df[col].astype(str)
        df = df.map(lambda x: str(x) if isinstance(x, time) else x)

        # Get the sheet from the destination workbook
        ws = wb.sheets[sheet_name]

        # Clear existing data (if needed)
        ws.range('A2').options(expand='table').clear_contents()

        # Write DataFrame to Excel starting at cell A2
        ws.range('A2').options(pd.DataFrame, index=False, header=False).value = df

    # Save the workbook
    wb.save()
finally:
    # Ensure the workbook and app are closed even if an error occurs
    wb.close()
    app.quit()

print("Data copied successfully!")
