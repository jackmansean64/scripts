import pandas as pd

# File paths
source_file = r'"C:\Users\Sean Jackman\Downloads\Tiller-Foundation-Template-source.xlsx"'
destination_file = r'"C:\Users\Sean Jackman\Downloads\Tiller-Foundation-Template-dest.xlsx"'

# Define the columns for each table
transactions_columns = [
    'Date', 'Description', 'Category', 'Amount', 'Labels', 'Notes', 'Account',
    'Account #', 'Institution', 'Month', 'Week', 'Transaction ID', 'Account ID',
    'Check Number', 'Full Description', 'Date Added'
]
account_columns = ['Account', 'Class Override', 'Group', 'Hide']
balance_history_columns = [
    'Account', 'Account #', 'Account ID', 'Institution', 'Balance', 'Month',
    'Week', 'Type', 'Unique Account Identifier', 'Date Added'
]
categories_columns = [
    'Category', 'Group', 'Type', 'Hide From Reports', 'Jan 2023', 'Feb 2023',
    'Mar 2023', 'Apr 2023', 'May 2023', 'Jun 2023', 'Jul 2023', 'Aug 2023',
    'Sep 2023', 'Oct 2023', 'Nov 2023', 'Dec 2023'
]

# Read and filter the data
sheets = {
    "Transactions": transactions_columns,
    "Accounts": account_columns,
    "Balance History": balance_history_columns,
    "Categories": categories_columns
}

# Open the ExcelWriter for the destination file
with pd.ExcelWriter(destination_file, engine='openpyxl') as writer:
    for sheet_name, columns in sheets.items():
        df = pd.read_excel(source_file, sheet_name=sheet_name, usecols=columns)
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print("Data copied successfully!")
