"""Remove duplicate Tiller transactions created by re-filling a copied workbook.

When you copy your Tiller data into a fresh spreadsheet and then run the Tiller
add-on's "fill" tool, Tiller's database doesn't recognise the new sheet and
re-adds every transaction. The result is pairs of rows for the same bank
transaction: the copy you already categorised, and a fresh, *uncategorised*
copy Tiller just brought in.

This tool finds those duplicates and deletes the uncategorised copy, keeping the
one you've already categorised. It prints a compact report of everything it
removes and makes a timestamped backup of the workbook before saving.

To create exe:
    pyinstaller -F remove_duplicates.py
"""

import math
import os
import shutil
from datetime import date, datetime

import pandas as pd
import xlwings as xw

TRANSACTIONS_SHEET = "Transactions"
CATEGORY_COLUMN = "Category"

# Fields that identify the *same* bank transaction across a Tiller re-fill.
# Deliberately excludes Transaction ID / Date Added (regenerated on every fill)
# and Category (the field that differs between the two copies). "Full
# Description" is the raw, unedited bank text, so it survives re-fills better
# than the user-editable "Description"; we fall back to "Description" if it's
# the only one present.
DATE_COLUMN = "Date"
AMOUNT_COLUMN = "Amount"
ACCOUNT_COLUMN = "Account"

# Don't flood the console past this many deleted rows; the full list always goes
# to the CSV log regardless.
DISPLAY_ROW_CAP = 500


def clean_path(raw):
    """Normalise a path typed or dragged into the console.

    Dragging a file into a PowerShell terminal (VS Code's default on Windows)
    inserts it as a command, e.g. ``& 'C:\\path with spaces\\file.xlsx'``. Other
    shells wrap it in double quotes. Strip all of that down to a bare path.
    """
    path = raw.strip()
    if path.startswith("&"):  # PowerShell drag-and-drop call operator
        path = path[1:].strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in ("'", '"'):
        quote = path[0]
        path = path[1:-1]
        if quote == "'":
            # PowerShell escapes embedded single quotes by doubling them.
            path = path.replace("''", "'")
    return path


def is_blank(value):
    """True for empty cells (None, NaN, or whitespace-only strings)."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def normalise_key_value(column, value):
    """Normalise a cell into a stable, comparable key component."""
    if column == DATE_COLUMN:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value).strip()
    if column == AMOUNT_COLUMN:
        try:
            return f"{round(float(value), 2):.2f}"
        except (TypeError, ValueError):
            return str(value).strip()
    # Text columns: strip, upper-case, and collapse internal whitespace so
    # cosmetic differences don't hide a real duplicate.
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def build_key_columns(columns):
    """Pick the available columns that identify a unique bank transaction."""
    key_columns = []
    for column in (DATE_COLUMN, AMOUNT_COLUMN, ACCOUNT_COLUMN):
        if column in columns:
            key_columns.append(column)
    if "Full Description" in columns:
        key_columns.append("Full Description")
    elif "Description" in columns:
        key_columns.append("Description")
    return key_columns


def make_unique_columns(header):
    """Make column names unique so duplicate headers don't break lookups.

    A workbook can contain two columns with the same header. We never write the
    header row back (only data rows from row 2 down), so renaming duplicates here
    is purely internal and leaves the sheet untouched. Returns
    (unique_header, duplicate_counts) where duplicate_counts maps each repeated
    header name to how many times it appears.
    """
    seen = {}
    unique = []
    for name in header:
        label = "" if name is None else str(name)
        if label in seen:
            seen[label] += 1
            unique.append(f"{label}.{seen[label]}")
        else:
            seen[label] = 0
            unique.append(label)
    # seen[label] is the highest suffix used, so occurrences == seen[label] + 1.
    # Ignore phantom empty trailing columns (blank header names).
    duplicate_counts = {
        label: count + 1
        for label, count in seen.items()
        if count >= 1 and label.strip()
    }
    return unique, duplicate_counts


def warn_duplicate_headers(duplicate_counts):
    """Print a prominent warning naming each duplicate header that was found."""
    rule = "!" * 64
    plural = "s" if len(duplicate_counts) > 1 else ""
    print(f"\n{rule}")
    print(f"  WARNING: Duplicate column header{plural} in the Transactions sheet")
    for name, count in sorted(duplicate_counts.items()):
        print(f'    - "{name}"  (appears {count} times)')
    print("  The script will still work (columns are matched by position), but a")
    print("  duplicate header is usually an accidental extra column. Consider")
    print("  deleting the redundant column in your sheet.")
    print(f"{rule}\n")


def read_transactions(sheet):
    """Read the Transactions sheet into a DataFrame, preserving column order."""
    values = sheet.used_range.value
    if not values:
        return pd.DataFrame()
    # A single-column sheet comes back as a flat list; wrap it into rows.
    if not isinstance(values[0], list):
        values = [[v] for v in values]
    header, duplicate_counts = make_unique_columns(values[0])
    if duplicate_counts:
        warn_duplicate_headers(duplicate_counts)
    rows = values[1:]
    # Drop trailing rows that are entirely empty (stray formatting, etc.).
    rows = [row for row in rows if not all(is_blank(cell) for cell in row)]
    data_frame = pd.DataFrame(rows, columns=header)
    # Keep python objects (datetimes, None) intact for clean write-back.
    return data_frame.astype(object)


def find_duplicates(data_frame, key_columns):
    """Return the positional indices of duplicate rows to delete.

    Within each group of rows sharing the same identifying key:
    - if any copy is categorised, keep the categorised copy(ies) and delete the
      uncategorised duplicates (the ones Tiller re-filled);
    - if every copy is uncategorised, keep the first one encountered and delete
      the rest.
    """
    groups = {}
    for position in range(len(data_frame)):
        row = data_frame.iloc[position]
        key = tuple(normalise_key_value(column, row[column]) for column in key_columns)
        # positions accumulate in top-to-bottom sheet order ("encounter" order).
        groups.setdefault(key, []).append(position)

    delete_positions = []
    for positions in groups.values():
        if len(positions) < 2:
            continue
        uncategorised = [
            p for p in positions if is_blank(data_frame.iloc[p][CATEGORY_COLUMN])
        ]
        if len(uncategorised) < len(positions):
            # At least one copy is categorised: keep the categorised copy(ies)
            # and drop every uncategorised duplicate.
            delete_positions.extend(uncategorised)
        else:
            # Every copy is uncategorised: keep the first encountered, drop the rest.
            delete_positions.extend(positions[1:])

    return sorted(delete_positions)


def format_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return "????-??-??" if is_blank(value) else str(value)


def month_bucket(value):
    text = format_date(value)
    return text[:7] if len(text) >= 7 else "unknown"


def compact_line(row, description_column):
    date_text = format_date(row.get(DATE_COLUMN))
    amount = row.get(AMOUNT_COLUMN)
    try:
        amount_text = f"{float(amount):>12,.2f}"
    except (TypeError, ValueError):
        amount_text = f"{str(amount):>12}"
    description = str(row.get(description_column) or "")[:38] if description_column else ""
    account = str(row.get(ACCOUNT_COLUMN) or "")[:22]
    return f"  {date_text}  {amount_text}  {description:<38}  {account}"


def print_report(deleted_frame, total_rows, description_column):
    print("\n=== Duplicate removal summary ===")
    print(f"Transactions scanned:      {total_rows:,}")
    print(f"Duplicate rows to delete:  {len(deleted_frame):,}")

    if deleted_frame.empty:
        return

    ordered = deleted_frame.sort_values(by=DATE_COLUMN, key=lambda s: s.map(format_date))
    records = ordered.to_dict("records")

    # Per-month subtotals first — the compressed at-a-glance view.
    print("\n--- Deleted per month ---")
    counts = {}
    for record in records:
        counts[month_bucket(record.get(DATE_COLUMN))] = (
            counts.get(month_bucket(record.get(DATE_COLUMN)), 0) + 1
        )
    for month in sorted(counts):
        print(f"  {month}: {counts[month]:,}")

    print(f"\n--- Deleted transactions ({len(records):,}) ---")
    if len(records) <= DISPLAY_ROW_CAP:
        current_month = None
        for record in records:
            month = month_bucket(record.get(DATE_COLUMN))
            if month != current_month:
                print(f"{month}")
                current_month = month
            print(compact_line(record, description_column))
    else:
        print(
            f"(Over {DISPLAY_ROW_CAP:,} rows — per-month totals are above; showing the first 50 below.)"
        )
        for record in records[:50]:
            print(compact_line(record, description_column))


def write_back(sheet, kept_frame):
    """Replace the Transactions data rows with the kept rows."""
    header_width = len(kept_frame.columns)
    last_row = max(sheet.used_range.last_cell.row, 2)
    sheet.range((2, 1), (last_row, header_width)).clear_contents()
    if not kept_frame.empty:
        # NaN -> None so blank cells stay blank instead of writing "nan".
        clean = kept_frame.where(pd.notna(kept_frame), None)
        sheet.range((2, 1)).value = clean.values.tolist()


def main():
    workbook_path = clean_path(
        input("Enter the Tiller workbook path or drag the file here: ")
    )

    try:
        app = xw.App(visible=False)
        workbook = xw.Book(workbook_path)
    except Exception as error:
        print(f"An error occurred opening the workbook: {error}")
        input("Press enter to quit...")
        return

    try:
        try:
            sheet = workbook.sheets[TRANSACTIONS_SHEET]
        except Exception:
            print(f"Could not find a '{TRANSACTIONS_SHEET}' sheet in this workbook.")
            return

        data_frame = read_transactions(sheet)
        if data_frame.empty:
            print("No transactions found — nothing to do.")
            return
        if CATEGORY_COLUMN not in data_frame.columns:
            print(
                f"No '{CATEGORY_COLUMN}' column found, so duplicates can't be resolved by category."
            )
            return

        key_columns = build_key_columns(data_frame.columns)
        print(f"Matching duplicates on: {', '.join(key_columns)}")

        delete_positions = find_duplicates(data_frame, key_columns)
        deleted_frame = data_frame.iloc[delete_positions]
        description_column = (
            "Full Description"
            if "Full Description" in data_frame.columns
            else ("Description" if "Description" in data_frame.columns else None)
        )

        print_report(deleted_frame, len(data_frame), description_column)

        if not delete_positions:
            print("\nNo uncategorised duplicates found — leaving the workbook unchanged.")
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_path = os.path.splitext(workbook_path)[0]

        confirm = input(
            f"\nDelete these {len(delete_positions):,} uncategorised duplicate rows and save? (y/n): "
        )
        if confirm.strip().lower() != "y":
            print("No changes saved.")
            return

        backup_path = f"{base_path}.backup-{timestamp}.xlsx"
        try:
            shutil.copy2(workbook_path, backup_path)
            print(f"Backup of the original saved to:\n  {backup_path}")
        except Exception as error:
            print(f"Warning: couldn't create a backup ({error}).")
            if input("Proceed without a backup? (y/n): ").strip().lower() != "y":
                print("No changes saved.")
                return

        kept_frame = data_frame.drop(index=data_frame.index[delete_positions])
        write_back(sheet, kept_frame)
        workbook.save()
        print(f"Done. Removed {len(delete_positions):,} duplicate rows.")

    except Exception as error:
        print(f"An error occurred: {error}")
        input("Press enter to continue...")
    finally:
        workbook.close()
        app.quit()

    input("Press enter to close the window...")


if __name__ == "__main__":
    main()
