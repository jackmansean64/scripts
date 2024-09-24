from datetime import time
import pandas as pd
import xlwings as xw
from tqdm import tqdm

source_file = input("Enter source Excel file path or drag file here: ").strip('"')
destination_file = input("Enter destination Excel file path or drag file here: ").strip('"')

transactions_columns = [
    'Date', 'Description', 'Category', 'Amount', 'Account',
    'Account #', 'Institution', 'Month', 'Week', 'Transaction ID', 'Account ID',
    'Check Number', 'Full Description', 'Date Added'
]
optional_transactions_columns = ['Labels', 'Notes']
account_columns = ['Account', 'Class Override', 'Group', 'Hide']
balance_history_columns = [
    'Date', 'Time', 'Account', 'Account #', 'Account ID', 'Balance ID',
    'Institution', 'Balance', 'Month', 'Week', 'Type', 'Class', 'Account Status',
    'Date Added'
]
optional_balance_history_columns = ['Unique Account Identifier']
categories_columns = [
    'Category', 'Group', 'Type', 'Hide From Reports'
]

sheets = {
    "Transactions": transactions_columns,
    "Accounts": account_columns,
    "Balance History": balance_history_columns,
    "Categories": categories_columns
}

optional_columns = {
    "Transactions": optional_transactions_columns,
    "Balance History": optional_balance_history_columns
}

try:
    app = xw.App(visible=False)
    dest_workbook = xw.Book(destination_file)
except Exception as e:
    print(f"An error occurred: {str(e)}")
    input("Press enter to quit...")
    quit()

is_error = False
try:
    for sheet_name, columns in tqdm(sheets.items(), desc="Copying sheets", unit="sheet"):
        try:
            df = pd.read_excel(source_file, sheet_name=sheet_name)

            missing_columns = [col for col in columns if col not in df.columns]
            if missing_columns:
                print(
                    (f"Warning: The following columns are missing in sheet '{sheet_name}': {', '.join(missing_columns)}."
                     f" These columns are part of the Tiller Foundation Template.")
                )
                user_input = input("Would you like to proceed anyways? (y/n): ")
                if user_input.lower() != "y":
                    dest_workbook.close()
                    app.quit()
                    quit()

            # Check for optional columns and add them if they exist
            if sheet_name in optional_columns:
                for col in optional_columns[sheet_name]:
                    if col in df.columns:
                        columns.append(col)

            # Select only the columns that exist in the source workbook
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]

            # Convert datetime.time objects to string representations to allow writing to Excel
            df = df.map(lambda x: str(x) if isinstance(x, time) else x)

            dest_worksheets = dest_workbook.sheets[sheet_name]
            dest_worksheets.range('A2').options(expand='table').clear_contents()

            for col_idx, col_name in enumerate(df.columns, start=1):
                try:
                    dest_worksheets.range(2, col_idx).options(transpose=True).value = df[col_name].tolist()
                except Exception as e:
                    print(f"Error writing column '{col_name}' to sheet '{sheet_name}': {str(e)}")
                    input("Press enter to continue...")
                    is_error = True

        except Exception as e:
            print(f"Error processing sheet '{sheet_name}': {str(e)}")
            input("Press enter to continue...")
            is_error = True

except Exception as e:
    print(f"An error occurred: {str(e)}")
    input("Press enter to continue...")
    is_error = True
finally:
    if is_error:
        print("Errors occurred during processing. Please check the console for details.")
        save_input = input("Would you like to attempt to save the changes anyways? (y/n): ")
        if save_input.lower() == 'y':
            dest_workbook.save()
    else:
        print("Data copied successfully!")
        dest_workbook.save()
    dest_workbook.close()
    app.quit()

input("Press enter to close the window...")
