"""Remove duplicate Tiller transactions created by re-filling a copied workbook.

When you copy your Tiller data into a fresh spreadsheet and then run the Tiller
add-on's "fill" tool, Tiller's database doesn't recognise the new sheet and
re-adds every transaction. The result is pairs of rows for the same bank
transaction: the copy you already categorised, and a fresh, *uncategorised*
copy Tiller just brought in.

This tool finds those duplicates and deletes the uncategorised copy, keeping the
one you've already categorised. It prints a compact report of everything it
removes and makes a timestamped backup of the workbook before saving.

It also prints a second, advisory list: uncategorised rows sitting at the top of
the sheet but dated well *before* your newest categorised transaction. Those are
very likely re-adds whose twin didn't match exactly (edited description, shifted
post date, renamed account). Because that's a heuristic rather than a certain
match, the list is confirmed separately from the exact matches — you can delete
one, both, or neither.

To create exe:
    pyinstaller -F remove_duplicates.py
"""

import math
import os
import shutil
from datetime import date, datetime, timedelta

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

# Grace period for the "possible duplicate" heuristic. A legitimate new
# transaction can post a few days behind the newest thing you've categorised, so
# only rows dated more than this far back are treated as suspicious.
SUSPECT_TOLERANCE_DAYS = 7


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


def row_word(items):
    return "row" if len(items) == 1 else "rows"


def ask_yes_no(prompt):
    """Ask a yes/no question. Anything other than an explicit yes means no."""
    return input(prompt).strip().lower() in ("y", "yes")


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


def parse_date(value):
    """Best-effort conversion of a cell into a ``date`` for ordering comparisons.

    Returns None when the cell is blank or can't be read as a date, so callers
    can skip it rather than guess.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if is_blank(value):
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def find_suspected_duplicates(data_frame, delete_positions):
    """Flag uncategorised rows stranded at the top of the sheet with old dates.

    Tiller sorts the Transactions sheet newest-first and drops re-filled rows in
    at the top. A genuinely new transaction you simply haven't categorised yet is
    therefore dated on or after everything you *have* categorised. An
    uncategorised row sitting in that top block but dated well *before* your
    categorised transactions is almost always a re-add of an old transaction
    whose twin slipped past the exact-match check — an edited description, a
    shifted post date, a renamed account, a re-rounded amount.

    "Well before" allows SUSPECT_TOLERANCE_DAYS of slack: a legitimate new
    transaction can post a few days behind the newest thing you've categorised,
    and shouldn't be flagged for it.

    The match is a heuristic, so these are always confirmed separately from the
    exact matches rather than folded in with them.

    Returns (positions, cutoff_date).
    """
    if DATE_COLUMN not in data_frame.columns:
        return [], None

    # The unbroken run of uncategorised rows at the very top of the sheet.
    leading = []
    for position in range(len(data_frame)):
        if not is_blank(data_frame.iloc[position][CATEGORY_COLUMN]):
            break
        leading.append(position)
    if not leading or len(leading) == len(data_frame):
        return [], None

    newest_categorised = None
    for position in range(len(leading), len(data_frame)):
        row = data_frame.iloc[position]
        if is_blank(row[CATEGORY_COLUMN]):
            continue
        row_date = parse_date(row[DATE_COLUMN])
        if row_date is not None and (
            newest_categorised is None or row_date > newest_categorised
        ):
            newest_categorised = row_date
    if newest_categorised is None:
        return [], None

    cutoff = newest_categorised - timedelta(days=SUSPECT_TOLERANCE_DAYS)
    already_deleting = set(delete_positions)
    suspects = []
    for position in leading:
        if position in already_deleting:
            continue
        row_date = parse_date(data_frame.iloc[position][DATE_COLUMN])
        if row_date is not None and row_date < cutoff:
            suspects.append(position)
    return suspects, cutoff


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


def print_suspects(suspect_frame, cutoff, description_column):
    """Print the heuristic 'these look like duplicates too' list."""
    if suspect_frame.empty:
        return

    print(f"\n--- Possible duplicates ({len(suspect_frame):,}) ---")
    print(f"Uncategorised rows at the top of the sheet dated before {cutoff.isoformat()}")
    print(f"(more than {SUSPECT_TOLERANCE_DAYS} days behind your newest categorised transaction).")
    print("Tiller adds re-filled rows at the top, so an old date up here usually")
    print("means a re-add whose twin didn't match exactly (edited description,")
    print("shifted date, renamed account).")
    print("Check these over - you'll be asked separately whether to delete them.")

    ordered = suspect_frame.sort_values(by=DATE_COLUMN, key=lambda s: s.map(format_date))
    records = ordered.to_dict("records")
    for record in records[:DISPLAY_ROW_CAP]:
        print(compact_line(record, description_column))
    if len(records) > DISPLAY_ROW_CAP:
        print(f"  ... and {len(records) - DISPLAY_ROW_CAP:,} more.")


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

        suspect_positions, suspect_cutoff = find_suspected_duplicates(
            data_frame, delete_positions
        )
        print_suspects(
            data_frame.iloc[suspect_positions], suspect_cutoff, description_column
        )

        if not delete_positions and not suspect_positions:
            print("\nNo duplicates found — leaving the workbook unchanged.")
            return

        # Each list is confirmed separately: the exact matches are safe, the
        # possible duplicates are a heuristic the user may want to skip.
        remove_positions = []
        if delete_positions:
            if ask_yes_no(
                f"\nDelete the {len(delete_positions):,} exact-match duplicate"
                f" {row_word(delete_positions)} listed above? (y/n): "
            ):
                remove_positions.extend(delete_positions)
            else:
                print("Leaving the exact-match duplicates in place.")
        if suspect_positions:
            also = "Also delete" if remove_positions else "Delete"
            if ask_yes_no(
                f"\n{also} the {len(suspect_positions):,} possible duplicate"
                f" {row_word(suspect_positions)} listed above? (y/n): "
            ):
                remove_positions.extend(suspect_positions)
            else:
                print("Leaving the possible duplicates in place.")

        remove_positions = sorted(set(remove_positions))
        if not remove_positions:
            print("\nNothing selected for deletion — no changes saved.")
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_path = os.path.splitext(workbook_path)[0]

        backup_path = f"{base_path}.backup-{timestamp}.xlsx"
        try:
            shutil.copy2(workbook_path, backup_path)
            print(f"Backup of the original saved to:\n  {backup_path}")
        except Exception as error:
            print(f"Warning: couldn't create a backup ({error}).")
            if not ask_yes_no("Proceed without a backup? (y/n): "):
                print("No changes saved.")
                return

        kept_frame = data_frame.drop(index=data_frame.index[remove_positions])
        write_back(sheet, kept_frame)
        workbook.save()

        removed_exact = len(set(remove_positions) & set(delete_positions))
        removed_suspect = len(set(remove_positions) & set(suspect_positions))
        print(f"Done. Removed {len(remove_positions):,} rows.")
        if removed_exact and removed_suspect:
            print(
                f"  {removed_exact:,} exact-match, {removed_suspect:,} possible duplicates."
            )

    except Exception as error:
        print(f"An error occurred: {error}")
        input("Press enter to continue...")
    finally:
        workbook.close()
        app.quit()

    input("Press enter to close the window...")


if __name__ == "__main__":
    main()
