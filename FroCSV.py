#!/usr/bin/env python3

import os
import sys
import csv
import re
import tempfile
from datetime import datetime

from tqdm import tqdm
from colorama import init as colorama_init, Fore, Style

# Raise CSV field size limit to avoid "field larger than field limit"
try:
    csv.field_size_limit(sys.maxsize)
except Exception:
    try:
        csv.field_size_limit(2**31 - 1)
    except Exception:
        pass

colorama_init(autoreset=True)

# color palette (light-tone for dark terminals)
H_TITLE = Fore.LIGHTCYAN_EX + Style.BRIGHT
H_SECTION = Fore.LIGHTBLUE_EX + Style.BRIGHT
C_PROMPT = Fore.LIGHTYELLOW_EX + Style.BRIGHT
C_INPUT = Fore.LIGHTWHITE_EX + Style.BRIGHT
C_NOTICE = Fore.LIGHTMAGENTA_EX
C_SUCCESS = Fore.LIGHTGREEN_EX
C_WARN = Fore.LIGHTRED_EX
C_INFO = Fore.LIGHTBLUE_EX

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def print_banner():
    print("\n" + "=" * 76)
    print(H_TITLE + " " * 5 + "FroCSV v1.6 | Designed by karthxk (https://karthxk0.github.io/)" + Style.RESET_ALL)
    print("=" * 76)


def prompt(text: str, example: str = None) -> str:
    line = C_PROMPT + text + Style.RESET_ALL
    if example:
        line += C_INPUT + f" (e.g. {example})" + Style.RESET_ALL
    line += "\n" + C_PROMPT + "> " + Style.RESET_ALL
    return input(line).strip()


def prompt_simple(sym="> ") -> str:
    return input(C_PROMPT + sym + Style.RESET_ALL).strip()


def _strip_quotes(s: str) -> str:
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_path_list(path_str):
    paths = []
    # Use csv.reader to correctly parse commas inside quoted paths
    try:
        parts = next(csv.reader([path_str], skipinitialspace=True))
    except StopIteration:
        parts = []
        
    for part in parts:
        s = part.strip()
        if not s:
            continue
        s = _strip_quotes(s)
        s = os.path.expanduser(s)
        paths.append(s)
    return paths


def normalize_single_path(path_str):
    s = path_str.strip()
    s = _strip_quotes(s)
    s = os.path.expanduser(s)
    return os.path.abspath(s)


def discover_csv_files_from_sources():
    print()
    print(H_SECTION + "Enter one or more CSV files or folders separated by commas." + Style.RESET_ALL)
    print(H_SECTION + "Paths may be Windows or Linux style and may be enclosed in quotes." + Style.RESET_ALL)
    src_input = prompt("Source CSV path(s)", r'"/mnt/c/data", C:\data\file1.csv')
    raw_paths = parse_path_list(src_input)

    csv_files = []
    seen = set()

    for p in raw_paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for fname in files:
                    if fname.lower().endswith(".csv"):
                        full = os.path.abspath(os.path.join(root, fname))
                        if full not in seen:
                            csv_files.append(full)
                            seen.add(full)
        elif os.path.isfile(p) and p.lower().endswith(".csv"):
            full = os.path.abspath(p)
            if full not in seen:
                csv_files.append(full)
                seen.add(full)
        else:
            print(C_WARN + f"Warning: {p} is not a CSV file or directory. Skipping." + Style.RESET_ALL)

    if not csv_files:
        print(C_WARN + "No CSV files found in the provided paths." + Style.RESET_ALL)
        return []

    print("\n" + "-" * 68)
    print(H_SECTION + "Detected CSV files:" + Style.RESET_ALL)
    for i, f in enumerate(csv_files, 1):
        print(f"  {i}. {f}")
    return csv_files


def parse_index_spec(spec, max_len, what="index"):
    indices = set()
    if not spec.strip():
        return []
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            try:
                start_s, end_s = part.split("-", 1)
                start = int(start_s)
                end = int(end_s)
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    if 1 <= i <= max_len:
                        indices.add(i - 1)
                    else:
                        print(C_WARN + f"Warning: {what} {i} out of range 1..{max_len}, skipped." + Style.RESET_ALL)
            except ValueError:
                print(C_WARN + f"Warning: could not parse range '{part}', skipped." + Style.RESET_ALL)
        else:
            try:
                i = int(part)
                if 1 <= i <= max_len:
                    indices.add(i - 1)
                else:
                    print(C_WARN + f"Warning: {what} {i} out of range 1..{max_len}, skipped." + Style.RESET_ALL)
            except ValueError:
                print(C_WARN + f"Warning: could not parse '{part}' as integer index, skipped." + Style.RESET_ALL)
    return sorted(indices)


def create_log_file(tool_name, target_file, is_new_output, dest_dir=None):
    if dest_dir:
        dest_dir = normalize_single_path(dest_dir)
    if target_file:
        target_file = normalize_single_path(target_file)
    if is_new_output and dest_dir:
        log_dir = dest_dir
    else:
        log_dir = os.path.dirname(target_file) if target_file else os.getcwd()
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{tool_name}_{ts}"
    log_name = f"FroCSVLog_{run_id}.log"
    log_path = os.path.join(log_dir, log_name)
    f = open(log_path, "w", encoding="utf-8", newline="")
    return log_path, f, run_id


def log_both(log_fh, msg=""):
    print(msg)
    if log_fh:
        log_fh.write(strip_ansi(msg) + "\n")


def log_run_header(log_fh, tool_name, run_id, log_path, target_file):
    log_fh.write("=" * 80 + "\n")
    log_fh.write("Built by karthxk (https://karthxk0.github.io/) - LOG\n")
    log_fh.write("=" * 80 + "\n")
    log_fh.write(f"Tool       : {tool_name}\n")
    log_fh.write(f"Run ID     : {run_id}\n")
    log_fh.write(f"Target file: {target_file}\n")
    log_fh.write(f"Log path   : {log_path}\n")
    log_fh.write(f"Timestamp  : {datetime.now().isoformat(timespec='seconds')}\n")
    log_fh.write("=" * 80 + "\n\n")


def log_summary_section(log_fh, summary_lines, effect_line):
    log_fh.write("[SUMMARY OF INPUTS]\n")
    for line in summary_lines:
        log_fh.write("  " + strip_ansi(line) + "\n")
    log_fh.write("\n[PLANNED OPERATION]\n")
    log_fh.write("  " + strip_ansi(effect_line) + "\n\n")


def safe_open_csv_reader(path):
    return open(path, "r", encoding="utf-8", newline="", errors="replace")


def safe_open_csv_writer(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return open(path, "w", encoding="utf-8", newline="")


def confirm_operation(summary_lines, effect_line):
    print("\n" + "-" * 72)
    print(H_SECTION + "Summary of your inputs:" + Style.RESET_ALL)
    for line in summary_lines:
        print("  " + line)
    print("\n" + H_SECTION + "Planned operation:" + Style.RESET_ALL)
    print("  " + effect_line)
    print("-" * 72)
    ans = prompt_simple("Proceed with this operation? (y/n) > ")
    return ans.lower() in ("y", "yes")


def header_comparison_lines(old_header, new_header):
    lines = []
    lines.append("Idx | Old column name                    | New index")
    lines.append("-" * 76)
    for i, col in enumerate(old_header, 1):
        try:
            new_idx = new_header.index(col) + 1
        except ValueError:
            new_idx = "-"
        lines.append(f"{i:3d} | {col:<34.34} | {new_idx}")
    extra_cols = [c for c in new_header if c not in old_header]
    if extra_cols:
        lines.append("")
        lines.append("New columns (not in original):")
        for c in extra_cols:
            lines.append(f"  - {c}")
    return lines


def print_header_comparison(old_header, new_header, log_fh=None):
    lines = header_comparison_lines(old_header, new_header)
    print("\n" + H_SECTION + "[Column order comparison]" + Style.RESET_ALL)
    for line in lines:
        if "|" in line and "Old column name" not in line:
            print(C_INFO + line + Style.RESET_ALL)
        else:
            print(line)
    if log_fh:
        log_fh.write("[COLUMN ORDER COMPARISON]\n")
        for line in lines:
            log_fh.write(line + "\n")
        log_fh.write("\n")


# -------------------------
# Tool 1: CSV Details
# -------------------------
def tool_csv_details():
    tool_name = "details"
    files = discover_csv_files_from_sources()
    if not files:
        return

    all_lines = []
    print("\n" + "-" * 72)
    print(H_SECTION + "CSV Details Tool" + Style.RESET_ALL)
    print("-" * 72)

    summary = [
        f"Tool: {H_SECTION}CSV Details{Style.RESET_ALL}",
        f"Number of files: {C_INPUT}{len(files)}{Style.RESET_ALL}",
    ]
    effect = (
        f"This operation will scan {C_INPUT}{len(files)}{Style.RESET_ALL} file(s) "
        "and report number of columns, column names, row counts and file sizes."
    )

    if not confirm_operation(summary, effect):
        print(C_WARN + "Operation cancelled." + Style.RESET_ALL)
        return

    for path in files:
        print("\n" + "=" * 76)
        print(H_TITLE + f"File: {path}" + Style.RESET_ALL)
        print("=" * 76)
        lines = []
        lines.append("=" * 76)
        lines.append(f"File: {path}")
        try:
            size_bytes = os.path.getsize(path)
            size_mb = size_bytes / (1024 * 1024)
            lines.append(f"Size: {size_bytes} bytes ({size_mb:.2f} MB)")
        except Exception:
            lines.append("Size: (could not determine)")

        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header = next(reader, [])
                num_cols = len(header)
                lines.append(f"Columns: {num_cols}")
                lines.append("Column names:")
                for i, col in enumerate(header, 1):
                    lines.append(f"  {i:3d}. {col}")

                row_count = 0
                try:
                    for _ in tqdm(reader, desc=f"Counting rows for {os.path.basename(path)}", unit="row"):
                        row_count += 1
                except csv.Error as e:
                    warn_msg = (
                        f"CSV parsing error while counting rows: {e}. "
                        "Falling back to simple line count (may be faster but less reliable)."
                    )
                    print(C_WARN + warn_msg + Style.RESET_ALL)
                    lines.append("Warning: CSV parsing error when counting rows; used fallback line count.")
                    fh.seek(0)
                    next(fh, None)
                    row_count = 0
                    for _ in tqdm(fh, desc=f"Counting lines for {os.path.basename(path)}", unit="line"):
                        row_count += 1
                lines.append(f"Data rows (excluding header): {row_count}")
                lines.append("")
        except Exception as e:
            print(C_WARN + f"Failed to read file {path}: {e}" + Style.RESET_ALL)
            lines.append(f"Error reading file: {e}")

        for l in lines:
            if l.startswith("File: "):
                print(H_SECTION + l + Style.RESET_ALL)
            elif l.startswith("Size: "):
                print(C_INPUT + l + Style.RESET_ALL)
            elif l.startswith("Columns:"):
                print(C_INFO + l + Style.RESET_ALL)
            elif l.startswith("Column names:"):
                print(C_INFO + l + Style.RESET_ALL)
            elif l.startswith("Data rows"):
                print(C_NOTICE + l + Style.RESET_ALL)
            elif l.startswith("Warning:"):
                print(C_WARN + l + Style.RESET_ALL)
            else:
                print(l)

        all_lines.extend(lines)

    save_choice = prompt_simple("Do you want to save this CSV details report to a text log file? (y/n) > ")
    if save_choice.lower() not in ("y", "yes"):
        print(C_WARN + "CSV details were not saved to a file." + Style.RESET_ALL)
        return

    dest_root_input = prompt("Enter destination folder for CSV details log file", r'/path/to/output_dir')
    dest_root = normalize_single_path(dest_root_input)
    os.makedirs(dest_root, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{tool_name}_{ts}"
    log_name = f"FroCSVLog_{run_id}.log"
    log_path = os.path.join(dest_root, log_name)

    with open(log_path, "w", encoding="utf-8", newline="") as log_fh:
        log_fh.write("=" * 80 + "\n")
        log_fh.write("Built by karthxk (https://karthxk0.github.io/) - LOG\n")
        log_fh.write("=" * 80 + "\n")
        log_fh.write(f"Tool      : {tool_name}\n")
        log_fh.write(f"Run ID    : {run_id}\n")
        log_fh.write(f"Log path  : {log_path}\n")
        log_fh.write(f"Timestamp : {datetime.now().isoformat(timespec='seconds')}\n")
        log_fh.write("=" * 80 + "\n\n")
        log_summary_section(log_fh, summary, effect)
        log_fh.write("[CSV FILE DETAILS]\n\n")
        for l in all_lines:
            log_fh.write(l + "\n")

    print(C_SUCCESS + f"CSV details log saved to: {log_path}" + Style.RESET_ALL)

# -------------------------
# Tool 2: Merge CSV files
# -------------------------
def tool_merge_csv():
    tool_name = "merge"
    files = discover_csv_files_from_sources()
    if len(files) < 2:
        print(C_WARN + "Need at least 2 CSV files to merge." + Style.RESET_ALL)
        return

    print("\n" + H_SECTION + "Merge mode:" + Style.RESET_ALL)
    print("  1. Merge into a NEW CSV file")
    print("  2. Merge into an EXISTING CSV file (one of the inputs)")
    mode = prompt_simple("> ")
    if mode not in ("1", "2"):
        print(C_WARN + "Invalid merge mode." + Style.RESET_ALL)
        return

    if mode == "1":
        dest_path_input = prompt("Enter destination path for NEW merged CSV file", r'/path/to/merged.csv')
        dest_path = normalize_single_path(dest_path_input)
        if not dest_path.lower().endswith(".csv"):
            dest_path += ".csv"
        is_new_output = True
    else:
        print("\nSelect the EXISTING CSV file to merge into:")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f}")
        idx = prompt("Enter index of existing file", "1")
        try:
            idx = int(idx)
            base_file = files[idx - 1]
        except Exception:
            print(C_WARN + "Invalid selection." + Style.RESET_ALL)
            return
        dest_path = normalize_single_path(base_file)
        is_new_output = False

    file_list_str = ", ".join(os.path.basename(f) for f in files)
    summary = [
        f"Tool: {H_SECTION}Merge CSV files{Style.RESET_ALL}",
        f"Input files count: {C_INPUT}{len(files)}{Style.RESET_ALL}",
        f"Files: {C_INPUT}{file_list_str}{Style.RESET_ALL}",
        f"Mode: {C_INPUT}{'NEW file' if is_new_output else 'EXISTING file'}{Style.RESET_ALL}",
    ]
    if is_new_output:
        summary.append(f"New output path: {C_INPUT}{dest_path}{Style.RESET_ALL}")
        effect = (
            f"All rows from {C_INPUT}{len(files)}{Style.RESET_ALL} input file(s) "
            f"will be combined into a single NEW file at {C_INPUT}{dest_path}{Style.RESET_ALL}, "
            "aligning columns by header name and creating new columns when needed."
        )
    else:
        summary.append(f"Existing base file: {C_INPUT}{dest_path}{Style.RESET_ALL}")
        effect = (
            f"All rows from {C_INPUT}{len(files)}{Style.RESET_ALL} input file(s) "
            f"will be merged into the selected base file {C_INPUT}{dest_path}{Style.RESET_ALL}. "
            "Existing rows in that file are preserved; new columns may be added."
        )

    if not confirm_operation(summary, effect):
        print(C_WARN + "Operation cancelled." + Style.RESET_ALL)
        return

    master_cols = []
    master_set = set()

    print(C_INFO + "\nBuilding master column set across all files..." + Style.RESET_ALL)
    for path in tqdm(files, desc="Scanning headers", unit="file"):
        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header = next(reader, [])
        except Exception:
            header = []
        for col in header:
            if col not in master_set:
                master_set.add(col)
                master_cols.append(col)

    dest_dir_for_log = os.path.dirname(dest_path) if dest_path else None
    log_path, log_fh, run_id = create_log_file(tool_name, dest_path, is_new_output, dest_dir=dest_dir_for_log)
    log_run_header(log_fh, tool_name, run_id, log_path, dest_path)
    log_summary_section(log_fh, summary, effect)

    log_both(log_fh, C_INFO + "[MASTER COLUMNS]" + Style.RESET_ALL)
    for i, col in enumerate(master_cols, 1):
        log_both(log_fh, f"  {i:3d}. {col}")

    dest_dir_for_output = os.path.dirname(dest_path) if dest_path else os.getcwd()
    dest_dir_for_output = normalize_single_path(dest_dir_for_output)
    os.makedirs(dest_dir_for_output, exist_ok=True)

    total_rows_written = 0
    temp_fd = None
    temp_path = None
    try:
        prefix = os.path.basename(dest_path)
        fd, temp_path = tempfile.mkstemp(prefix=prefix + ".tmp.", suffix=".csv", dir=dest_dir_for_output, text=True)
        temp_fd = fd
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as out_fh:
            writer = csv.DictWriter(out_fh, fieldnames=master_cols)
            writer.writeheader()
            for path in files:
                log_both(log_fh, C_NOTICE + f"Processing input file: {path}" + Style.RESET_ALL)
                try:
                    with safe_open_csv_reader(path) as fh:
                        reader = csv.DictReader(fh)
                        for row in tqdm(reader, desc=f"Merging {os.path.basename(path)}", unit="row", leave=False):
                            out_row = {col: row.get(col, "") for col in master_cols}
                            writer.writerow(out_row)
                            total_rows_written += 1
                except csv.Error as e:
                    log_both(log_fh, f"CSV parsing error while merging {path}: {e}")
            try:
                out_fh.flush()
                os.fsync(out_fh.fileno())
            except Exception:
                pass

    except Exception as e:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        print(C_WARN + f"Error writing merged file: {e}" + Style.RESET_ALL)
        log_both(log_fh, f"Error writing merged file: {e}")
        log_fh.close()
        return

    try:
        if not temp_path or not os.path.exists(temp_path):
            cand = None
            basename_prefix = os.path.basename(dest_path)
            for fname in os.listdir(dest_dir_for_output):
                if fname.startswith(basename_prefix + ".tmp.") and fname.endswith(".csv"):
                    cand = os.path.join(dest_dir_for_output, fname)
                    break
            if cand and os.path.exists(cand):
                temp_path = cand
            else:
                raise FileNotFoundError(f"Temporary merged file not found in {dest_dir_for_output}")

        os.replace(temp_path, dest_path)

    except Exception as e:
        print(C_WARN + f"Error replacing temp merged file into destination: {e}" + Style.RESET_ALL)
        log_both(log_fh, f"Error during final replace: {e}")
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        log_fh.close()
        return

    log_both(log_fh, f"Total rows written (excluding header): {total_rows_written}")
    log_both(log_fh, f"Merged output: {dest_path}")
    log_fh.close()
    print(C_SUCCESS + f"\nMerge completed. Output: {dest_path}" + Style.RESET_ALL)
    print(C_SUCCESS + f"Log saved to: {log_path}" + Style.RESET_ALL)


# -------------------------
# Tool 3: Duplicate checker
# -------------------------
def tool_duplicate_checker():
    tool_name = "duplicate_checker"
    files = discover_csv_files_from_sources()
    if not files:
        return

    print("\n" + H_SECTION + "Duplicate checker operates on each file independently." + Style.RESET_ALL)

    for path in files:
        print("\n" + "-" * 72)
        print(H_SECTION + f"Processing file: {path}" + Style.RESET_ALL)

        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header = next(reader)
        except Exception as e:
            print(C_WARN + f"Could not read header of {path}: {e}" + Style.RESET_ALL)
            continue

        print("\nColumns:")
        for i, col in enumerate(header, 1):
            print(f"  {i}. {col}")
        spec = prompt("Enter column indices to check for duplicates", "1, 3, 6-8")
        indices = parse_index_spec(spec, len(header), what="column")
        if not indices:
            print(C_WARN + "No valid columns selected, skipping file." + Style.RESET_ALL)
            continue
        cols = [header[i] for i in indices]

        print("\nWhat do you want to do with detected duplicates?")
        print("  1. List duplicates")
        print("  2. Delete duplicates (keep one best row per unique value)")
        mode = prompt_simple("> ")
        if mode not in ("1", "2"):
            print(C_WARN + "Invalid mode, skipping file." + Style.RESET_ALL)
            continue

        summary = [
            f"Tool: {H_SECTION}Duplicate checker{Style.RESET_ALL}",
            f"File: {C_INPUT}{path}{Style.RESET_ALL}",
            f"Columns to check: {C_INPUT}{cols}{Style.RESET_ALL}",
            f"Action: {C_INPUT}{'List' if mode == '1' else 'Delete'}{Style.RESET_ALL}",
        ]
        if mode == "1":
            effect = ("Each selected column will be scanned for duplicate entries. "
                      "Duplicate rows will be listed in terminal and in the log file.")
        else:
            effect = ("For every set of identical values in a selected column, keep ONE row "
                      "(prefer row with more non-empty fields); delete the rest.")

        if not confirm_operation(summary, effect):
            print(C_WARN + "Skipping file." + Style.RESET_ALL)
            continue

        is_new_output = (mode == "2")
        dest_dir = os.path.dirname(path)
        log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
        log_run_header(log_fh, tool_name, run_id, log_path, path)
        log_summary_section(log_fh, summary, effect)

        if mode == "1":
            dup_maps = {col: {} for col in cols}
            try:
                with safe_open_csv_reader(path) as fh:
                    reader = csv.DictReader(fh)
                    row_num = 0
                    for row in tqdm(reader, desc="Scanning for duplicates", unit="row"):
                        row_num += 1
                        for col in cols:
                            val = row.get(col, "")
                            cmap = dup_maps[col]
                            if val not in cmap:
                                cmap[val] = (row_num, dict(row))
                            else:
                                prev = cmap[val]
                                if isinstance(prev, tuple):
                                    cmap[val] = [prev, (row_num, dict(row))]
                                else:
                                    prev.append((row_num, dict(row)))
            except csv.Error as e:
                print(C_WARN + f"CSV parsing error: {e}. Aborting duplicate list for this file." + Style.RESET_ALL)
                log_both(log_fh, f"CSV parsing error while scanning duplicates: {e}")
                log_fh.close()
                continue

            dup_count_total = 0
            log_both(log_fh, C_NOTICE + "[DUPLICATE ROWS]" + Style.RESET_ALL)
            for col in cols:
                cmap = dup_maps[col]
                for val, info in cmap.items():
                    if isinstance(info, list):
                        dup_count_total += len(info)
                        log_both(log_fh, C_INFO + f"\nColumn '{col}' duplicate value: '{val}'" + Style.RESET_ALL)
                        for (rnum, row) in info:
                            print(C_INFO + f"[DUPLICATE] Column: {col} | Row: {rnum} | Value: {val}" + Style.RESET_ALL)
                            print(f"  {row}")
                            log_both(log_fh, f"  Row {rnum}: {row}")

            log_both(log_fh, C_SUCCESS + f"\nTotal duplicate rows (counting all columns): {dup_count_total}" + Style.RESET_ALL)
            log_fh.close()
            print(C_SUCCESS + f"Listing complete. Log saved to: {log_path}" + Style.RESET_ALL)

        else:
            delete_rows = set()
            best_for_key = {}

            def count_non_empty(row_dict):
                return sum(1 for v in row_dict.values() if v not in ("", None))

            try:
                with safe_open_csv_reader(path) as fh:
                    reader = csv.DictReader(fh)
                    row_num = 0
                    for row in tqdm(reader, desc="Analyzing duplicates", unit="row"):
                        row_num += 1
                        for col in cols:
                            val = row.get(col, "")
                            if val == "":
                                continue
                            key = (col, val)
                            non_empty_count = count_non_empty(row)
                            if key not in best_for_key:
                                best_for_key[key] = (row_num, non_empty_count)
                            else:
                                best_row, best_count = best_for_key[key]
                                if non_empty_count > best_count:
                                    delete_rows.add(best_row)
                                    best_for_key[key] = (row_num, non_empty_count)
                                else:
                                    delete_rows.add(row_num)
            except csv.Error as e:
                print(C_WARN + f"CSV parsing error: {e}. Aborting duplicate deletion for this file." + Style.RESET_ALL)
                log_both(log_fh, f"CSV parsing error while analyzing duplicates: {e}")
                log_fh.close()
                continue

            total_deleted = len(delete_rows)
            log_both(log_fh, f"Rows marked for deletion: {total_deleted}")

            temp_path = path + ".frocsv_tmp"
            try:
                with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(temp_path) as out_fh:
                    reader = csv.reader(in_fh)
                    writer = csv.writer(out_fh)
                    header = next(reader, [])
                    writer.writerow(header)
                    row_idx = 0
                    kept = 0
                    for row in tqdm(reader, desc="Writing filtered file", unit="row"):
                        row_idx += 1
                        if row_idx in delete_rows:
                            continue
                        writer.writerow(row)
                        kept += 1
                os.replace(temp_path, path)
            except Exception as e:
                print(C_WARN + f"Error writing filtered file: {e}" + Style.RESET_ALL)
                log_both(log_fh, f"Error writing filtered file: {e}")
                log_fh.close()
                continue

            log_both(log_fh, f"Total rows kept (excluding header): {kept}")
            log_both(log_fh, f"Final file (overwritten): {path}")
            log_fh.close()
            print(C_SUCCESS + f"Duplicate deletion complete. File updated: {path}" + Style.RESET_ALL)
            print(C_SUCCESS + f"Log saved to: {log_path}" + Style.RESET_ALL)


# -------------------------
# Tool 4: Column aligner
# -------------------------
def apply_shift_operations(header, ops):
    for source_names, anchor_name in ops:
        new_header = [h for h in header if h not in source_names]
        if anchor_name not in new_header:
            insert_pos = len(new_header)
        else:
            insert_pos = new_header.index(anchor_name)
        for i, name in enumerate(source_names):
            new_header.insert(insert_pos + i, name)
        header = new_header
    return header

def apply_swap_operations(header, swaps):
    for left_names, right_names in swaps:
        if len(left_names) != len(right_names):
            raise ValueError("Unequal list sizes in swap operation.")
        for ln, rn in zip(left_names, right_names):
            if ln not in header or rn not in header:
                continue
            i = header.index(ln)
            j = header.index(rn)
            header[i], header[j] = header[j], header[i]
    return header

def parse_shift_spec(spec, max_len, idx_to_name):
    ops = []
    if not spec.strip():
        return ops
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ">" not in part:
            print(C_WARN + f"Warning: cannot parse shift operation '{part}', skipped." + Style.RESET_ALL)
            continue
        left, right = part.split(">", 1)
        left, right = left.strip(), right.strip()
        left_indices = parse_index_spec(left, max_len, what="column")
        if not left_indices:
            print(C_WARN + f"Warning: no valid source indices in '{part}', skipped." + Style.RESET_ALL)
            continue
        try:
            anchor_idx = int(right)
        except ValueError:
            print(C_WARN + f"Warning: invalid anchor index '{right}' in '{part}', skipped." + Style.RESET_ALL)
            continue
        if not (1 <= anchor_idx <= max_len):
            print(C_WARN + f"Warning: anchor index {anchor_idx} out of range, skipped." + Style.RESET_ALL)
            continue
        source_names = [idx_to_name[i] for i in left_indices]
        anchor_name = idx_to_name[anchor_idx - 1]
        ops.append((source_names, anchor_name))
    return ops

def parse_swap_spec(spec, max_len, idx_to_name):
    swaps = []
    if not spec.strip():
        return swaps
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "<>" not in part:
            print(C_WARN + f"Warning: cannot parse swap operation '{part}', skipped." + Style.RESET_ALL)
            continue
        left, right = part.split("<>", 1)
        left_indices = parse_index_spec(left.strip(), max_len, what="column")
        right_indices = parse_index_spec(right.strip(), max_len, what="column")
        if not left_indices or not right_indices:
            print(C_WARN + f"Warning: invalid indices in '{part}', skipped." + Style.RESET_ALL)
            continue
        if len(left_indices) != len(right_indices):
            print(C_WARN + f"Error: unequal columns for swap '{part}', skipped." + Style.RESET_ALL)
            continue
        left_names = [idx_to_name[i] for i in left_indices]
        right_names = [idx_to_name[i] for i in right_indices]
        swaps.append((left_names, right_names))
    return swaps

def tool_column_aligner():
    tool_name = "column_aligner"
    files = discover_csv_files_from_sources()
    if not files:
        return

    first = files[0]
    print("\n" + "-" * 72)
    print(H_SECTION + f"Using first file to define column operations: {first}" + Style.RESET_ALL)

    try:
        with safe_open_csv_reader(first) as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
    except Exception as e:
        print(C_WARN + f"Could not read header from {first}: {e}" + Style.RESET_ALL)
        return

    print("\nColumns (from first file):")
    for i, col in enumerate(header, 1):
        print(f"  {i}. {col}")

    idx_to_name = {i: name for i, name in enumerate(header)}
    print("\nChoose column aligner sub-tool:")
    print("  1. Shift column(s) to a new position (e.g. 1>2, 3>6, 7-10>13)")
    print("  2. Swap column(s) (e.g. 1<>2, 3-5<>7-9)")
    mode = prompt_simple("> ")
    if mode not in ("1", "2"):
        print(C_WARN + "Invalid mode." + Style.RESET_ALL)
        return

    if mode == "1":
        spec = prompt("Enter shift operations", "1>2, 3>6, 7-10>13")
        shift_ops = parse_shift_spec(spec, len(header), idx_to_name)
        if not shift_ops:
            print(C_WARN + "No valid shift operations parsed." + Style.RESET_ALL)
            return
        new_header = apply_shift_operations(header[:], shift_ops)
        mode_desc = "Shift"
    else:
        spec = prompt("Enter swap operations", "1<>2, 3-5<>7-9")
        swap_ops = parse_swap_spec(spec, len(header), idx_to_name)
        if not swap_ops:
            print(C_WARN + "No valid swap operations parsed." + Style.RESET_ALL)
            return
        new_header = apply_swap_operations(header[:], swap_ops)
        mode_desc = "Swap"

    print("\n" + H_SECTION + "New column order preview (first file):" + Style.RESET_ALL)
    for i, col in enumerate(new_header, 1):
        print(f"  {i}. {col}")

    print("\nSave changes in:")
    print("  1. OVERWRITE existing files")
    print("  2. NEW files in a destination folder")
    mode_out = prompt_simple("> ")
    if mode_out not in ("1", "2"):
        print(C_WARN + "Invalid choice." + Style.RESET_ALL)
        return

    dest_root = None
    if mode_out == "2":
        dest_root_input = prompt("Enter destination folder for new files", r'/path/to/output_dir')
        dest_root = normalize_single_path(dest_root_input)
        os.makedirs(dest_root, exist_ok=True)

    summary = [
        f"Tool: {H_SECTION}Column aligner{Style.RESET_ALL}",
        f"Files to process: {C_INPUT}{len(files)}{Style.RESET_ALL}",
        f"Mode: {C_INPUT}{mode_desc}{Style.RESET_ALL}",
        f"Output: {C_INPUT}{'Overwrite' if mode_out == '1' else 'New files'}{Style.RESET_ALL}",
    ]
    effect = "Columns will be reordered in ALL selected CSV files based on the order defined from the FIRST file."

    if not confirm_operation(summary, effect):
        print(C_WARN + "Operation cancelled." + Style.RESET_ALL)
        return

    for path in files:
        print("\n" + "-" * 72)
        print(H_SECTION + f"Aligning columns in: {path}" + Style.RESET_ALL)
        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header_file = next(reader, [])
        except Exception as e:
            print(C_WARN + f"Could not read header of {path}: {e}" + Style.RESET_ALL)
            continue

        if header_file != header:
            print(C_WARN + "Header differs from the first file. Missing columns will appear as blank." + Style.RESET_ALL)

        actual_set = set(header_file)
        final_header = [c for c in new_header if c in actual_set]
        for c in header_file:
            if c not in final_header:
                final_header.append(c)

        is_new_output = (mode_out == "2")
        dest_dir = dest_root if dest_root else os.path.dirname(path)
        log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
        log_run_header(log_fh, tool_name, run_id, log_path, path)
        log_summary_section(log_fh, summary, effect)

        print_header_comparison(header_file, final_header, log_fh=log_fh)

        out_path = os.path.join(dest_root, os.path.basename(path)) if mode_out == "2" else path + ".frocsv_tmp"
        try:
            with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                reader = csv.DictReader(in_fh)
                writer = csv.DictWriter(out_fh, fieldnames=final_header)
                writer.writeheader()
                count = 0
                for row in tqdm(reader, desc="Reordering rows", unit="row"):
                    out_row = {col: row.get(col, "") for col in final_header}
                    writer.writerow(out_row)
                    count += 1
        except csv.Error as e:
            print(C_WARN + f"CSV parsing error while aligning: {e}" + Style.RESET_ALL)
            log_both(log_fh, f"CSV parsing error while aligning: {e}")
            log_fh.close()
            continue
        except Exception as e:
            print(C_WARN + f"Error during write: {e}" + Style.RESET_ALL)
            log_both(log_fh, f"Error during write: {e}")
            log_fh.close()
            continue

        log_both(log_fh, f"Total rows processed (excluding header): {count}")
        if mode_out == "1":
            os.replace(out_path, path)
            log_both(log_fh, f"File overwritten: {path}")
            print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
        else:
            log_both(log_fh, f"New file saved: {out_path}")
            print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)

        log_fh.close()
        print(C_SUCCESS + f"Log saved to: {log_path}" + Style.RESET_ALL)


# -------------------------
# Tool 5: Column merger
# -------------------------
def tool_column_merger():
    tool_name = "column_merger"
    files = discover_csv_files_from_sources()
    if not files:
        return

    for path in files:
        print("\n" + "-" * 72)
        print(H_SECTION + f"Column merger for file: {path}" + Style.RESET_ALL)
        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header = next(reader, [])
        except Exception as e:
            print(C_WARN + f"Could not read header of {path}: {e}" + Style.RESET_ALL)
            continue
        if not header:
            print(C_WARN + "File has no header, skipping." + Style.RESET_ALL)
            continue

        print("\nColumns:")
        for i, col in enumerate(header, 1):
            print(f"  {i}. {col}")

        spec = prompt("Enter columns to MERGE into a single column", "1, 2-4")
        indices = parse_index_spec(spec, len(header), what="column")
        if not indices:
            print(C_WARN + "No valid columns selected, skipping file." + Style.RESET_ALL)
            continue
        selected_cols = [header[i] for i in indices]

        print("\nMerge target:")
        print("  1. Merge into an EXISTING column (one of the selected)")
        print("  2. Merge into a NEW column")
        mode = prompt_simple("> ")
        if mode not in ("1", "2"):
            print(C_WARN + "Invalid choice, skipping file." + Style.RESET_ALL)
            continue

        if mode == "1":
            print("\nSelect target column (by index) from the selected ones:")
            for i, col in enumerate(selected_cols, 1):
                print(f"  {i}. {col}")
            t_idx = prompt("Target column index", "1")
            try:
                t_idx = int(t_idx)
                if not (1 <= t_idx <= len(selected_cols)):
                    raise ValueError
                target_col = selected_cols[t_idx - 1]
            except Exception:
                print(C_WARN + "Invalid target index, skipping file." + Style.RESET_ALL)
                continue
            create_new_col = False
            new_col_name = target_col
        else:
            new_col_name = prompt("Enter NEW column name to merge into", "MergedData")
            if not new_col_name:
                print(C_WARN + "Empty column name, skipping." + Style.RESET_ALL)
                continue
            target_col = new_col_name
            create_new_col = True

        print("\nSave changes in:")
        print("  1. OVERWRITE existing file")
        print("  2. NEW file in a destination folder")
        mode_out = prompt_simple("> ")
        if mode_out not in ("1", "2"):
            print(C_WARN + "Invalid choice, skipping file." + Style.RESET_ALL)
            continue
        dest_root = None
        if mode_out == "2":
            dest_root_input = prompt("Enter destination folder for new file", r'/path/to/output_dir')
            dest_root = normalize_single_path(dest_root_input)
            os.makedirs(dest_root, exist_ok=True)

        summary = [
            f"Tool: {H_SECTION}Column Merger{Style.RESET_ALL}",
            f"File: {C_INPUT}{path}{Style.RESET_ALL}",
            f"Columns to merge: {C_INPUT}{selected_cols}{Style.RESET_ALL}",
            f"Target column: {C_INPUT}{target_col}{Style.RESET_ALL}",
            f"New column? {C_INPUT}{'Yes' if create_new_col else 'No (existing)'}{Style.RESET_ALL}",
            f"Output: {C_INPUT}{'Overwrite existing' if mode_out == '1' else 'New file'}{Style.RESET_ALL}",
        ]
        effect = ("For each row, if exactly ONE of the selected columns has a non-empty value, that value "
                  "will be moved into the target column. Rows where multiple selected columns contain data "
                  "will be skipped and logged.")
        if not confirm_operation(summary, effect):
            print(C_WARN + "Skipping file." + Style.RESET_ALL)
            continue

        is_new_output = (mode_out == "2")
        dest_dir = dest_root if dest_root else os.path.dirname(path)
        log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
        log_run_header(log_fh, tool_name, run_id, log_path, path)
        log_summary_section(log_fh, summary, effect)

        log_both(log_fh, C_INFO + "[COLUMNS TO MERGE]" + Style.RESET_ALL)
        for i, c in enumerate(selected_cols, 1):
            log_both(log_fh, f"  {i:3d}. {c}")
        log_both(log_fh, f"Target column: {target_col}")

        if create_new_col:
            if new_col_name in header:
                log_both(log_fh, C_WARN + f"Note: new column name '{new_col_name}' already exists; will reuse it." + Style.RESET_ALL)
                create_new_col = False
                new_header = header[:]
            else:
                new_header = header + [new_col_name]
        else:
            new_header = header[:]

        col_has_data = {col: False for col in new_header}
        skipped_rows = 0
        merged_rows = 0
        total_rows = 0

        out_path = os.path.join(dest_root, os.path.basename(path)) if mode_out == "2" else path + ".frocsv_tmp"
        try:
            with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                reader = csv.DictReader(in_fh)
                writer = csv.DictWriter(out_fh, fieldnames=new_header)
                writer.writeheader()
                for row in tqdm(reader, desc="Merging columns", unit="row"):
                    total_rows += 1
                    for col in new_header:
                        if col not in row:
                            row[col] = ""
                    values = [(col, row.get(col, "")) for col in selected_cols]
                    non_empty = [(c, v) for c, v in values if v not in ("", None)]
                    if len(non_empty) == 0:
                        pass
                    elif len(non_empty) == 1:
                        col_name, val = non_empty[0]
                        row[target_col] = val
                        merged_rows += 1
                        for c in selected_cols:
                            if c != target_col and c in row:
                                row[c] = ""
                    else:
                        skipped_rows += 1

                    for col in new_header:
                        if row.get(col, "") not in ("", None):
                            col_has_data[col] = True

                    writer.writerow({col: row.get(col, "") for col in new_header})
        except csv.Error as e:
            log_both(log_fh, f"CSV parsing error during merge: {e}")
            print(C_WARN + f"CSV parsing error during merge: {e}" + Style.RESET_ALL)
            log_fh.close()
            continue
        except Exception as e:
            print(C_WARN + f"Unexpected error during merge: {e}" + Style.RESET_ALL)
            log_both(log_fh, f"Unexpected error during merge: {e}")
            log_fh.close()
            continue

        log_both(log_fh, f"Total rows processed: {total_rows}")
        log_both(log_fh, f"Rows successfully merged: {merged_rows}")
        log_both(log_fh, f"Rows skipped (multiple values): {skipped_rows}")

        empty_merged_cols = [c for c in selected_cols if c != target_col and not col_has_data.get(c, False)]
        if empty_merged_cols:
            print(C_NOTICE + f"\nThese merged-from columns ended up completely empty: {empty_merged_cols}" + Style.RESET_ALL)
            ans = prompt_simple("Do you want to drop these empty columns? (y/n) > ")
            if ans.lower() in ("y", "yes"):
                temp2 = out_path + ".tmp2"
                with safe_open_csv_reader(out_path) as in_fh, safe_open_csv_writer(temp2) as out_fh:
                    reader = csv.DictReader(in_fh)
                    final_header = [c for c in reader.fieldnames if c not in empty_merged_cols]
                    writer = csv.DictWriter(out_fh, fieldnames=final_header)
                    writer.writeheader()
                    for row in tqdm(reader, desc="Dropping empty columns", unit="row"):
                        writer.writerow({c: row.get(c, "") for c in final_header})
                os.replace(temp2, out_path)
                log_both(log_fh, f"Dropped empty columns: {empty_merged_cols}")

        if mode_out == "1":
            os.replace(out_path, path)
            log_both(log_fh, f"File overwritten: {path}")
            print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
        else:
            log_both(log_fh, f"New file saved: {out_path}")
            print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)

        log_fh.close()
        print(C_SUCCESS + f"Log saved to: {log_path}" + Style.RESET_ALL)


# -------------------------
# Tool 6: CSV Splitter
# -------------------------
def tool_csv_splitter():
    tool_name = "csv_splitter"
    files = discover_csv_files_from_sources()
    if not files:
        return

    print("\nSplit based on:")
    print("  1. Rows")
    print("  2. Columns")
    mode = prompt_simple("> ")
    if mode not in ("1", "2"):
        print(C_WARN + "Invalid choice." + Style.RESET_ALL)
        return

    if mode == "1":
        rows_per_file_str = prompt("Enter number of DATA rows per split file (excluding header)", "100000")
        try:
            rows_per_file = int(rows_per_file_str)
            if rows_per_file <= 0:
                raise ValueError
        except ValueError:
            print(C_WARN + "Invalid number." + Style.RESET_ALL)
            return

        keep_header_all = prompt_simple("Copy header row into EVERY split file? (y/n) > ").lower() in ("y", "yes")
        dest_root_input = prompt("Enter destination folder for split files", r'/path/to/output_dir')
        dest_root = normalize_single_path(dest_root_input)
        os.makedirs(dest_root, exist_ok=True)

        summary = [
            f"Tool: {H_SECTION}CSV Splitter (rows){Style.RESET_ALL}",
            f"Files: {C_INPUT}{len(files)}{Style.RESET_ALL}",
            f"Rows per split: {C_INPUT}{rows_per_file}{Style.RESET_ALL}",
            f"Header in all files: {C_INPUT}{keep_header_all}{Style.RESET_ALL}",
            f"Destination: {C_INPUT}{dest_root}{Style.RESET_ALL}",
        ]
        effect = f"Each input CSV will be split into multiple files with up to {rows_per_file} data rows."

        if not confirm_operation(summary, effect):
            print(C_WARN + "Operation cancelled." + Style.RESET_ALL)
            return

        for path in files:
            print("\n" + "-" * 72)
            print(H_SECTION + f"Splitting file (rows): {path}" + Style.RESET_ALL)
            log_path, log_fh, run_id = create_log_file(tool_name, path, True, dest_dir=dest_root)
            log_run_header(log_fh, tool_name, run_id, log_path, path)
            log_summary_section(log_fh, summary, effect)

            base_name = os.path.splitext(os.path.basename(path))[0]
            total_rows = 0
            part_idx = 0
            out_fh = None
            try:
                with safe_open_csv_reader(path) as in_fh:
                    reader = csv.reader(in_fh)
                    header = next(reader, [])
                    row_count_in_part = 0
                    for row in tqdm(reader, desc=f"Splitting {base_name}", unit="row"):
                        if row_count_in_part == 0:
                            part_idx += 1
                            if out_fh:
                                out_fh.close()
                            out_path = os.path.join(dest_root, f"{base_name}_part{part_idx:04d}.csv")
                            out_fh = safe_open_csv_writer(out_path)
                            out_writer = csv.writer(out_fh)
                            # Bugfix: If splitting starts, always write header to first file if headers exist,
                            # write to subsequent files only if keep_header_all is True.
                            if header and (part_idx == 1 or keep_header_all):
                                out_writer.writerow(header)
                        out_writer.writerow(row)
                        row_count_in_part += 1
                        total_rows += 1
                        if row_count_in_part >= rows_per_file:
                            row_count_in_part = 0
                    if out_fh:
                        out_fh.close()
            except Exception as e:
                print(C_WARN + f"Error splitting file {path}: {e}" + Style.RESET_ALL)
                log_both(log_fh, f"Error splitting file: {e}")
                log_fh.close()
                continue

            log_both(log_fh, f"Total data rows processed: {total_rows}")
            log_both(log_fh, f"Total split parts created: {part_idx}")
            log_fh.close()
            print(C_SUCCESS + f"Split complete for {path}. Log: {log_path}" + Style.RESET_ALL)

    else:
        dest_root_input = prompt("Enter destination folder for column-subset files", r'/path/to/output_dir')
        dest_root = normalize_single_path(dest_root_input)
        os.makedirs(dest_root, exist_ok=True)

        for path in files:
            print("\n" + "-" * 72)
            print(H_SECTION + f"Column-based splitting (subset) for file: {path}" + Style.RESET_ALL)
            try:
                with safe_open_csv_reader(path) as fh:
                    reader = csv.reader(fh)
                    header = next(reader, [])
            except Exception as e:
                print(C_WARN + f"Could not read file header: {e}" + Style.RESET_ALL)
                continue
            if not header:
                print(C_WARN + "File has no header, skipping." + Style.RESET_ALL)
                continue

            print("\nColumns:")
            for i, col in enumerate(header, 1):
                print(f"  {i}. {col}")
            spec = prompt("Enter columns to KEEP in the new file", "1, 4, 6-8")
            indices = parse_index_spec(spec, len(header), what="column")
            if not indices:
                print(C_WARN + "No valid columns selected, skipping file." + Style.RESET_ALL)
                continue
            selected_cols = [header[i] for i in indices]

            summary = [
                f"Tool: {H_SECTION}CSV Splitter (columns subset){Style.RESET_ALL}",
                f"File: {C_INPUT}{path}{Style.RESET_ALL}",
                f"Columns to keep: {C_INPUT}{selected_cols}{Style.RESET_ALL}",
                f"Destination: {C_INPUT}{dest_root}{Style.RESET_ALL}",
            ]
            effect = "Create a NEW CSV containing ONLY the selected columns."
            if not confirm_operation(summary, effect):
                print(C_WARN + "Skipping file." + Style.RESET_ALL)
                continue

            log_path, log_fh, run_id = create_log_file(tool_name, path, True, dest_dir=dest_root)
            log_run_header(log_fh, tool_name, run_id, log_path, path)
            log_summary_section(log_fh, summary, effect)

            log_both(log_fh, C_INFO + "[COLUMNS KEPT]" + Style.RESET_ALL)
            for i, c in enumerate(selected_cols, 1):
                log_both(log_fh, f"  {i:3d}. {c}")

            base_name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(dest_root, f"{base_name}_cols_subset.csv")
            try:
                with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                    reader = csv.DictReader(in_fh)
                    writer = csv.DictWriter(out_fh, fieldnames=selected_cols)
                    writer.writeheader()
                    count = 0
                    for row in tqdm(reader, desc="Writing subset", unit="row"):
                        out_row = {c: row.get(c, "") for c in selected_cols}
                        writer.writerow(out_row)
                        count += 1
            except Exception as e:
                print(C_WARN + f"Error creating subset file: {e}" + Style.RESET_ALL)
                log_both(log_fh, f"Error creating subset file: {e}")
                log_fh.close()
                continue

            log_both(log_fh, f"Total rows processed (excluding header): {count}")
            log_both(log_fh, f"New file saved: {out_path}")
            log_fh.close()
            print(C_SUCCESS + f"Column-subset file saved: {out_path}" + Style.RESET_ALL)
            print(C_SUCCESS + f"Log saved to: {log_path}" + Style.RESET_ALL)


# -------------------------
# Tool 7: Data deletion
# -------------------------
def tool_data_deletion():
    tool_name = "data_deletion"
    files = discover_csv_files_from_sources()
    if not files:
        return

    print("\nChoose deletion tool type:")
    print("  1. Empty cell based deletion")
    print("  2. Column-based deletion")
    print("  3. Row-based deletion")
    mode = prompt_simple("> ")
    if mode not in ("1", "2", "3"):
        print(C_WARN + "Invalid choice." + Style.RESET_ALL)
        return

    print("\nApply changes:")
    print("  1. OVERWRITE existing files")
    print("  2. Write to NEW files in a destination folder")
    mode_out = prompt_simple("> ")
    if mode_out not in ("1", "2"):
        print(C_WARN + "Invalid choice." + Style.RESET_ALL)
        return

    dest_root = None
    if mode_out == "2":
        dest_root_input = prompt("Enter destination folder for modified files", r'/path/to/output_dir')
        dest_root = normalize_single_path(dest_root_input)
        os.makedirs(dest_root, exist_ok=True)

    for path in files:
        print("\n" + "-" * 72)
        print(H_SECTION + f"Deletion tool for file: {path}" + Style.RESET_ALL)

        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header = next(reader, [])
        except Exception as e:
            print(C_WARN + f"Could not read header of {path}: {e}" + Style.RESET_ALL)
            continue

        if not header:
            print(C_WARN + "File has no header, skipping." + Style.RESET_ALL)
            continue

        if mode == "1":
            print("\nEmpty cell deletion mode:")
            print("  1. Column-wise: delete ROWS where selected columns have empty cells.")
            print("  2. Row-wise: delete COLUMNS that have empty cells in selected rows.")
            sub = prompt_simple("> ")
            if sub not in ("1", "2"):
                print(C_WARN + "Invalid choice, skipping file." + Style.RESET_ALL)
                continue

            if sub == "1":
                print("\nColumns:")
                for i, col in enumerate(header, 1):
                    print(f"  {i}. {col}")
                spec = prompt("Select columns whose EMPTY cells should trigger ROW deletion", "1, 3-5")
                indices = parse_index_spec(spec, len(header), what="column")
                if not indices:
                    print(C_WARN + "No valid columns, skipping file." + Style.RESET_ALL)
                    continue
                selected_cols = [header[i] for i in indices]

                summary = [
                    f"Tool: {H_SECTION}Empty-cell deletion (column-wise){Style.RESET_ALL}",
                    f"File: {C_INPUT}{path}{Style.RESET_ALL}",
                    f"Columns to inspect for empties: {C_INPUT}{selected_cols}{Style.RESET_ALL}",
                    f"Output: {C_INPUT}{'Overwrite' if mode_out == '1' else 'New file'}{Style.RESET_ALL}",
                ]
                effect = "Delete ANY ROW where any of the selected columns contains an empty cell."
                if not confirm_operation(summary, effect):
                    print(C_WARN + "Skipping file." + Style.RESET_ALL)
                    continue

                is_new_output = (mode_out == "2")
                dest_dir = dest_root if dest_root else os.path.dirname(path)
                log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
                log_run_header(log_fh, tool_name, run_id, log_path, path)
                log_summary_section(log_fh, summary, effect)

                out_path = os.path.join(dest_dir if is_new_output else os.path.dirname(path), os.path.basename(path)) if is_new_output else path + ".frocsv_tmp"
                try:
                    with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                        reader = csv.DictReader(in_fh)
                        writer = csv.DictWriter(out_fh, fieldnames=reader.fieldnames)
                        writer.writeheader()
                        total = 0
                        deleted = 0
                        for row in tqdm(reader, desc="Filtering rows", unit="row"):
                            total += 1
                            if any(row.get(c, "") in ("", None) for c in selected_cols):
                                deleted += 1
                                continue
                            writer.writerow(row)
                except Exception as e:
                    print(C_WARN + f"Error during filtering: {e}" + Style.RESET_ALL)
                    log_both(log_fh, f"Error during filtering: {e}")
                    log_fh.close()
                    continue

                if mode_out == "1":
                    os.replace(out_path, path)
                    print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
                else:
                    print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)
                log_fh.close()

            else:
                row_spec = prompt("Enter DATA row numbers to inspect for empties (excluding header row)", "23, 34-56")
                selected_rows = parse_index_spec(row_spec, 10**12, what="row")
                if not selected_rows:
                    print(C_WARN + "No valid rows, skipping file." + Style.RESET_ALL)
                    continue
                selected_rows_set = set(i + 1 for i in selected_rows)

                summary = [
                    f"Tool: {H_SECTION}Empty-cell deletion (row-wise){Style.RESET_ALL}",
                    f"File: {C_INPUT}{path}{Style.RESET_ALL}",
                    f"Rows to inspect (data rows): {C_INPUT}{sorted(selected_rows_set)}{Style.RESET_ALL}",
                    f"Output: {C_INPUT}{'Overwrite' if mode_out == '1' else 'New file'}{Style.RESET_ALL}",
                ]
                effect = "Delete ANY COLUMN that contains an empty cell in any of the specified data rows."
                if not confirm_operation(summary, effect):
                    print(C_WARN + "Skipping file." + Style.RESET_ALL)
                    continue

                is_new_output = (mode_out == "2")
                dest_dir = dest_root if dest_root else os.path.dirname(path)
                log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
                log_run_header(log_fh, tool_name, run_id, log_path, path)

                cols_to_delete = set()
                try:
                    with safe_open_csv_reader(path) as in_fh:
                        reader = csv.DictReader(in_fh)
                        data_row_idx = 0
                        for row in tqdm(reader, desc="Scanning rows", unit="row"):
                            data_row_idx += 1
                            if data_row_idx in selected_rows_set:
                                for col in header:
                                    if row.get(col, "") in ("", None):
                                        cols_to_delete.add(col)
                except Exception as e:
                    print(C_WARN + f"Error scanning rows: {e}" + Style.RESET_ALL)
                    log_fh.close()
                    continue

                keep_cols = [c for c in header if c not in cols_to_delete]
                out_path = os.path.join(dest_dir, os.path.basename(path)) if is_new_output else path + ".frocsv_tmp"
                try:
                    with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                        reader = csv.DictReader(in_fh)
                        writer = csv.DictWriter(out_fh, fieldnames=keep_cols)
                        writer.writeheader()
                        for row in tqdm(reader, desc="Writing new file", unit="row"):
                            writer.writerow({c: row.get(c, "") for c in keep_cols})
                except Exception as e:
                    print(C_WARN + f"Error writing file: {e}" + Style.RESET_ALL)
                    log_fh.close()
                    continue

                if mode_out == "1":
                    os.replace(out_path, path)
                    print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
                else:
                    print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)
                log_fh.close()

        elif mode == "2":
            print("\nChoose selection semantics:")
            print("  1. Select columns TO DELETE")
            print("  2. Select columns TO KEEP (all other columns will be deleted)")
            choice = prompt_simple("> ")
            if choice not in ("1", "2"):
                print(C_WARN + "Invalid choice, skipping file." + Style.RESET_ALL)
                continue

            print("\nColumns:")
            for i, col in enumerate(header, 1):
                print(f"  {i}. {col}")
            spec = prompt("Select columns (indices) according to above selection semantics", "1, 3-5")
            indices = parse_index_spec(spec, len(header), what="column")
            if not indices:
                print(C_WARN + "No valid columns, skipping file." + Style.RESET_ALL)
                continue

            if choice == "1":
                cols_to_delete = [header[i] for i in indices]
                keep_cols = [c for c in header if c not in cols_to_delete]
                op_text = f"Delete columns: {cols_to_delete}"
            else:
                keep_cols = [header[i] for i in indices]
                cols_to_delete = [c for c in header if c not in keep_cols]
                op_text = f"Keep columns: {keep_cols} (delete rest)"

            summary = [
                f"Tool: {H_SECTION}Column-based deletion{Style.RESET_ALL}",
                f"File: {C_INPUT}{path}{Style.RESET_ALL}",
                f"Operation: {C_INPUT}{op_text}{Style.RESET_ALL}",
                f"Output: {C_INPUT}{'Overwrite' if mode_out == '1' else 'New file'}{Style.RESET_ALL}",
            ]
            effect = "This operation will permanently delete the selected columns (or delete all except selected ones)."
            if not confirm_operation(summary, effect):
                print(C_WARN + "Skipping file." + Style.RESET_ALL)
                continue

            is_new_output = (mode_out == "2")
            dest_dir = dest_root if dest_root else os.path.dirname(path)
            log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
            log_run_header(log_fh, tool_name, run_id, log_path, path)

            out_path = os.path.join(dest_dir, os.path.basename(path)) if is_new_output else path + ".frocsv_tmp"
            try:
                with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                    reader = csv.DictReader(in_fh)
                    writer = csv.DictWriter(out_fh, fieldnames=keep_cols)
                    writer.writeheader()
                    for row in tqdm(reader, desc="Writing filtered file", unit="row"):
                        writer.writerow({c: row.get(c, "") for c in keep_cols})
            except Exception as e:
                print(C_WARN + f"Error writing filtered file: {e}" + Style.RESET_ALL)
                log_fh.close()
                continue

            if mode_out == "1":
                os.replace(out_path, path)
                print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
            else:
                print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)
            log_fh.close()

        else:
            print("\nChoose selection semantics:")
            print("  1. Select rows TO DELETE")
            print("  2. Select rows TO KEEP (delete all other data rows)")
            choice = prompt_simple("> ")
            if choice not in ("1", "2"):
                print(C_WARN + "Invalid choice, skipping file." + Style.RESET_ALL)
                continue

            row_spec = prompt("Enter DATA row numbers (excluding header)", "1, 12-15, 25")
            selected_rows = parse_index_spec(row_spec, 10**12, what="row")
            if not selected_rows:
                print(C_WARN + "No valid rows, skipping file." + Style.RESET_ALL)
                continue
            selected_rows_set = set(i + 1 for i in selected_rows)

            if choice == "1":
                op_text = f"Delete rows: {sorted(selected_rows_set)}"
            else:
                op_text = f"Keep rows: {sorted(selected_rows_set)} (delete rest)"

            summary = [
                f"Tool: {H_SECTION}Row-based deletion{Style.RESET_ALL}",
                f"File: {C_INPUT}{path}{Style.RESET_ALL}",
                f"Operation: {C_INPUT}{op_text}{Style.RESET_ALL}",
                f"Output: {C_INPUT}{'Overwrite' if mode_out == '1' else 'New file'}{Style.RESET_ALL}",
            ]
            effect = "This operation will delete or keep the specified data rows as selected."
            if not confirm_operation(summary, effect):
                continue

            is_new_output = (mode_out == "2")
            dest_dir = dest_root if dest_root else os.path.dirname(path)
            log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)
            
            out_path = os.path.join(dest_dir, os.path.basename(path)) if is_new_output else path + ".frocsv_tmp"
            try:
                with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                    reader = csv.reader(in_fh)
                    writer = csv.writer(out_fh)
                    header_row = next(reader, [])
                    writer.writerow(header_row)
                    data_row_idx = 0
                    for row in tqdm(reader, desc="Writing filtered file", unit="row"):
                        data_row_idx += 1
                        if choice == "1":
                            if data_row_idx in selected_rows_set:
                                continue
                            writer.writerow(row)
                        else:
                            if data_row_idx in selected_rows_set:
                                writer.writerow(row)
            except Exception as e:
                print(C_WARN + f"Error writing file: {e}" + Style.RESET_ALL)
                log_fh.close()
                continue

            if mode_out == "1":
                os.replace(out_path, path)
                print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
            else:
                print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)
            log_fh.close()


# -------------------------
# Tool 8: Column rename
# -------------------------
def tool_column_rename():
    tool_name = "column_rename"
    files = discover_csv_files_from_sources()
    if not files:
        return

    print("\nColumn name changes are specified as index>NewName, separated by commas.")
    print("Example: 1>SampleID, 2>GeneID")
    first = files[0]
    try:
        with safe_open_csv_reader(first) as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
    except Exception as e:
        print(C_WARN + f"Could not read header from {first}: {e}" + Style.RESET_ALL)
        return
    if not header:
        print(C_WARN + "First file has no header." + Style.RESET_ALL)
        return

    print("\nColumns (first file):")
    for i, col in enumerate(header, 1):
        print(f"  {i}. {col}")
    spec = prompt("Enter rename mappings", "1>SampleID, 2>GeneID")
    mappings = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ">" not in part:
            print(C_WARN + f"Warning: cannot parse mapping '{part}', skipped." + Style.RESET_ALL)
            continue
        left, right = part.split(">", 1)
        left = left.strip()
        right = right.strip()
        if not right:
            continue
        try:
            idx = int(left)
        except ValueError:
            continue
        if not (1 <= idx <= len(header)):
            continue
        old_name = header[idx - 1]
        mappings[old_name] = right

    if not mappings:
        print(C_WARN + "No valid mappings specified." + Style.RESET_ALL)
        return

    print("\nApply changes:")
    print("  1. OVERWRITE existing files")
    print("  2. NEW files in a destination folder")
    mode_out = prompt_simple("> ")
    dest_root = None
    if mode_out == "2":
        dest_root_input = prompt("Enter destination folder for renamed files", r'/path/to/output_dir')
        dest_root = normalize_single_path(dest_root_input)
        os.makedirs(dest_root, exist_ok=True)

    summary = [
        f"Tool: {H_SECTION}Column name change{Style.RESET_ALL}",
        f"Files: {C_INPUT}{len(files)}{Style.RESET_ALL}",
        f"Mappings: {C_INPUT}{mappings}{Style.RESET_ALL}",
        f"Output: {C_INPUT}{'Overwrite' if mode_out == '1' else 'New files'}{Style.RESET_ALL}",
    ]
    effect = "For each file, modify only the first row (column names) per specified mappings."

    if not confirm_operation(summary, effect):
        print(C_WARN + "Operation cancelled." + Style.RESET_ALL)
        return

    for path in files:
        print("\n" + "-" * 72)
        print(H_SECTION + f"Renaming columns in: {path}" + Style.RESET_ALL)
        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.reader(fh)
                header_file = next(reader, [])
        except Exception as e:
            continue

        new_header = [mappings.get(col, col) for col in header_file]
        is_new_output = (mode_out == "2")
        dest_dir = dest_root if dest_root else os.path.dirname(path)
        log_path, log_fh, run_id = create_log_file(tool_name, path, is_new_output, dest_dir=dest_dir)

        out_path = os.path.join(dest_dir, os.path.basename(path)) if is_new_output else path + ".frocsv_tmp"
        try:
            with safe_open_csv_reader(path) as in_fh, safe_open_csv_writer(out_path) as out_fh:
                reader = csv.reader(in_fh)
                writer = csv.writer(out_fh)
                writer.writerow(new_header)
                for row in tqdm(reader, desc="Copying rows", unit="row"):
                    writer.writerow(row)
        except Exception as e:
            continue

        if mode_out == "1":
            os.replace(out_path, path)
            print(C_SUCCESS + f"File overwritten: {path}" + Style.RESET_ALL)
        else:
            print(C_SUCCESS + f"New file saved: {out_path}" + Style.RESET_ALL)


# -------------------------
# Tool 9: Search & Copy Module
# -------------------------
def tool_search_module():
    tool_name = "search_module"
    files = discover_csv_files_from_sources()
    if not files:
        return

    terms_input = prompt("Enter search values separated by commas", "STING, CGAMP, 100ns")
    # Parse terms similarly to allow commas inside quoted values if needed
    try:
        search_terms = [t.strip() for t in next(csv.reader([terms_input], skipinitialspace=True)) if t.strip()]
    except StopIteration:
        search_terms = []

    if not search_terms:
        print(C_WARN + "No valid search terms provided." + Style.RESET_ALL)
        return

    print("\n" + H_SECTION + "Searching files..." + Style.RESET_ALL)
    results = [] 
    found_terms = set()

    for path in files:
        try:
            with safe_open_csv_reader(path) as fh:
                reader = csv.DictReader(fh)
                row_idx = 1
                for row in tqdm(reader, desc=f"Scanning {os.path.basename(path)}", unit="row"):
                    cols_matched = []
                    terms_matched_in_row = []
                    
                    for col, val in row.items():
                        if val and col:
                            for term in search_terms:
                                # Case-insensitive partial match
                                if term.lower() in val.lower():
                                    cols_matched.append(col)
                                    terms_matched_in_row.append(term)
                                    found_terms.add(term)
                    
                    if cols_matched:
                        results.append({
                            "terms": list(set(terms_matched_in_row)),
                            "file": path,
                            "row_idx": row_idx,
                            "matched_cols": list(set(cols_matched)),
                            "row_data": row
                        })
                    row_idx += 1
        except Exception as e:
            print(C_WARN + f"Error scanning {path}: {e}" + Style.RESET_ALL)

    not_found = set(search_terms) - found_terms
    print("\n" + H_TITLE + "Search Results:" + Style.RESET_ALL)
    if not results:
        print(C_WARN + "No matches found for any terms." + Style.RESET_ALL)
        if not_found:
            print("\n" + C_WARN + "Terms not found:" + Style.RESET_ALL)
            for t in not_found:
                print(f"  - {t}")
        return

    for res in results:
        terms_str = ", ".join(res['terms'])
        cols_str = ", ".join(res['matched_cols'])
        print(f"{C_SUCCESS}Match Found!{Style.RESET_ALL} Term(s): '{C_INPUT}{terms_str}{Style.RESET_ALL}'")
        print(f"  File: {res['file']}")
        print(f"  Row (Data Index): {res['row_idx']} | Column(s): {cols_str}\n")

    if not_found:
        print(C_WARN + "Terms not found:" + Style.RESET_ALL)
        for t in not_found:
            print(f"  - {t}")

    print("\nSelect an action:")
    print("  1. Just search and list (Done)")
    print("  2. Search and copy")
    action = prompt_simple("> ")

    if action == "2":
        print("\nCopy mode:")
        print("  1. Copy entire ROWS containing matches")
        print("  2. Copy entire COLUMNS containing matches")
        copy_mode = prompt_simple("> ")

        if copy_mode not in ("1", "2"):
            print(C_WARN + "Invalid mode selected." + Style.RESET_ALL)
            return

        print("\nDestination:")
        print("  1. New CSV file")
        print("  2. Existing CSV file (append/merge)")
        dest_mode = prompt_simple("> ")

        dest_path = prompt("Enter destination file path", r"/path/to/output.csv")
        dest_path = normalize_single_path(dest_path)
        dest_dir = os.path.dirname(dest_path) or os.getcwd()
        os.makedirs(dest_dir, exist_ok=True)

        if copy_mode == "1":  # ROW COPY
            master_cols = []
            master_set = set()

            if dest_mode == "2" and os.path.exists(dest_path):
                try:
                    with safe_open_csv_reader(dest_path) as fh:
                        existing_header = next(csv.reader(fh), [])
                        for c in existing_header:
                            master_set.add(c)
                            master_cols.append(c)
                except Exception:
                    pass

            for res in results:
                for c in res['row_data'].keys():
                    if c not in master_set and c is not None:
                        master_set.add(c)
                        master_cols.append(c)

            fd, temp_path = tempfile.mkstemp(prefix="search_row_tmp_", suffix=".csv", dir=dest_dir, text=True)

            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as out_fh:
                    writer = csv.DictWriter(out_fh, fieldnames=master_cols)
                    writer.writeheader()

                    if dest_mode == "2" and os.path.exists(dest_path):
                        with safe_open_csv_reader(dest_path) as in_fh:
                            reader = csv.DictReader(in_fh)
                            for row in reader:
                                out_row = {col: row.get(col, "") for col in master_cols}
                                writer.writerow(out_row)

                    for res in tqdm(results, desc="Copying matched rows", unit="row"):
                        out_row = {col: res['row_data'].get(col, "") for col in master_cols}
                        writer.writerow(out_row)

                os.replace(temp_path, dest_path)
                print(C_SUCCESS + f"\nRows copied successfully to {dest_path}" + Style.RESET_ALL)
            except Exception as e:
                print(C_WARN + f"Error copying rows: {e}" + Style.RESET_ALL)

        elif copy_mode == "2":  # COLUMN COPY
            targets = {}
            for res in results:
                f = res['file']
                for c in res['matched_cols']:
                    if f not in targets: targets[f] = set()
                    targets[f].add(c)

            extracted_columns_data = {}
            max_len = 0

            for f, cols in targets.items():
                try:
                    with safe_open_csv_reader(f) as fh:
                        reader = csv.DictReader(fh)
                        base_f = os.path.basename(f).split('.')[0]
                        col_lists = {c: [] for c in cols}
                        for row in tqdm(reader, desc=f"Extracting columns from {base_f}", unit="row"):
                            for c in cols:
                                col_lists[c].append(row.get(c, ""))
                        for c in cols:
                            extracted_columns_data[f"{base_f}_{c}"] = col_lists[c]
                            if len(col_lists[c]) > max_len:
                                max_len = len(col_lists[c])
                except Exception as e:
                    print(C_WARN + f"Error extracting columns from {f}: {e}" + Style.RESET_ALL)

            out_headers = list(extracted_columns_data.keys())

            if dest_mode == "2" and os.path.exists(dest_path):
                existing_data = []
                existing_headers = []
                try:
                    with safe_open_csv_reader(dest_path) as fh:
                        reader = csv.DictReader(fh)
                        existing_headers = reader.fieldnames or []
                        for row in reader:
                            existing_data.append(row)
                except Exception:
                    pass

                final_headers = existing_headers + [h for h in out_headers if h not in existing_headers]
                out_len = max(len(existing_data), max_len)

                fd, temp_path = tempfile.mkstemp(prefix="search_col_tmp_", suffix=".csv", dir=dest_dir, text=True)

                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="") as out_fh:
                        writer = csv.DictWriter(out_fh, fieldnames=final_headers)
                        writer.writeheader()
                        for i in tqdm(range(out_len), desc="Merging column data", unit="row"):
                            row_dict = {}
                            if i < len(existing_data):
                                row_dict.update(existing_data[i])
                            for h in out_headers:
                                if i < len(extracted_columns_data[h]):
                                    row_dict[h] = extracted_columns_data[h][i]
                                else:
                                    row_dict[h] = ""
                            writer.writerow(row_dict)
                    os.replace(temp_path, dest_path)
                    print(C_SUCCESS + f"\nColumns copied and merged successfully to {dest_path}" + Style.RESET_ALL)
                except Exception as e:
                    print(C_WARN + f"Error merging columns: {e}" + Style.RESET_ALL)

            else:
                try:
                    with safe_open_csv_writer(dest_path) as out_fh:
                        writer = csv.DictWriter(out_fh, fieldnames=out_headers)
                        writer.writeheader()
                        for i in tqdm(range(max_len), desc="Writing isolated columns", unit="row"):
                            row_dict = {}
                            for h in out_headers:
                                if i < len(extracted_columns_data[h]):
                                    row_dict[h] = extracted_columns_data[h][i]
                                else:
                                    row_dict[h] = ""
                            writer.writerow(row_dict)
                    print(C_SUCCESS + f"\nColumns extracted successfully to {dest_path}" + Style.RESET_ALL)
                except Exception as e:
                    print(C_WARN + f"Error writing column file: {e}" + Style.RESET_ALL)


# -------------------------
# Main
# -------------------------
def main():
    while True:
        print_banner()
        print("Select a tool:")
        print(f"  {Fore.LIGHTGREEN_EX}1{Style.RESET_ALL}. CSV Details (summary of rows/columns)")
        print(f"  {Fore.LIGHTGREEN_EX}2{Style.RESET_ALL}. Merge CSV Files")
        print(f"  {Fore.LIGHTGREEN_EX}3{Style.RESET_ALL}. Duplicate checker")
        print(f"  {Fore.LIGHTGREEN_EX}4{Style.RESET_ALL}. Column aligner (shift/swap)")
        print(f"  {Fore.LIGHTGREEN_EX}5{Style.RESET_ALL}. Column merger")
        print(f"  {Fore.LIGHTGREEN_EX}6{Style.RESET_ALL}. CSV file splitter")
        print(f"  {Fore.LIGHTGREEN_EX}7{Style.RESET_ALL}. Data deletion tool")
        print(f"  {Fore.LIGHTGREEN_EX}8{Style.RESET_ALL}. Column name change")
        print(f"  {Fore.LIGHTGREEN_EX}9{Style.RESET_ALL}. Search & Copy Module")
        print(f"  {Fore.LIGHTRED_EX}0{Style.RESET_ALL}. Exit")

        choice = prompt_simple("> ")

        if choice == "1":
            tool_csv_details()
        elif choice == "2":
            tool_merge_csv()
        elif choice == "3":
            tool_duplicate_checker()
        elif choice == "4":
            tool_column_aligner()
        elif choice == "5":
            tool_column_merger()
        elif choice == "6":
            tool_csv_splitter()
        elif choice == "7":
            tool_data_deletion()
        elif choice == "8":
            tool_column_rename()
        elif choice == "9":
            tool_search_module()
        elif choice == "0":
            print(H_TITLE + "Bye from FroCSV v5.0!" + Style.RESET_ALL)
            break
        else:
            print(C_WARN + "Invalid choice, please try again." + Style.RESET_ALL)

        input(C_PROMPT + "\nPress Enter to return to main menu..." + Style.RESET_ALL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + H_TITLE + "Interrupted by user. Goodbye." + Style.RESET_ALL)