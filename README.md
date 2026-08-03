# FroCSV v5.0

A multipurpose python tool to make handling, manipulating, and cleaning massive CSV files simple and time-saving.

## Usage

* Download and extract `FroCSV-main.zip` from your repository.
* Open `Terminal` in the extracted directory.
* Run: `python "FroCSV6.py"`

## Prerequisites & Installation

### 1. Minimum Requirements

* **Python:** Version 3.8 or higher.
* **Dependencies:** The script requires a few standard external libraries (`colorama` and `tqdm`).

### 2. Downloading the Tool

* Download and extract the tool's `.zip` file to your local machine.
* Alternatively, clone the repository directly from GitHub using your terminal or command prompt:

```bash
# Clone the repository
git clone https://github.com/karthxk0/FroCSV.git

```

*(Note: Replace with your actual repository URL if different).*

* Install the required dependencies:

```bash
pip install colorama tqdm

```

## Running FroCSV

* Navigate into the extracted/cloned directory:

```bash
cd FroCSV

```

* Run the script from the terminal using python:

```bash
python "FroCSV6.py"

```

## Functioning

* Upon launching, the interactive main menu offers 9 primary modules of operation to process your CSVs:

```text
Main Menu/
├── 1. CSV Details (summary of rows/columns)
├── 2. Merge CSV Files
├── 3. Duplicate checker
├── 4. Column aligner (shift/swap)
├── 5. Column merger
├── 6. CSV file splitter
├── 7. Data deletion tool
├── 8. Column name change
└── 9. Search & Copy Module

```

## Core Modules

### Step 1: `CSV Details`

* **Task:** Scans your selected files to instantly report file size, number of columns, column names, and total data rows.
* **Use Case:** Great for quickly auditing a massive dataset before deciding how to process it.

### Step 2: `Merge CSV Files`

* **Task:** Combines multiple CSV files into a single master file (either a new file or appending to an existing one).
* **Feature:** Intelligently aligns columns by their header names, automatically creating new columns if data structures differ between files.

### Step 3: `Duplicate Checker`

* **Task:** Scans specific columns for duplicate entries.
* **Modes:**
* *List:* Displays duplicates without modifying the file.
* *Delete:* Keeps only the best row per unique value (prioritizing the row with the most non-empty fields) and deletes the rest.



### Step 4: `Column Aligner`

* **Task:** Reorders columns across all selected CSV files based on the order defined from the first file.
* **Modes:** Allows you to *Shift* a column to a specific index (e.g., `1>2`) or *Swap* two columns directly (e.g., `1<>2`).

### Step 5: `Column Merger`

* **Task:** Condenses scattered data. If exactly one selected column has a value per row, it moves that value into a designated target column.
* **Use Case:** Perfect for consolidating data when multiple columns represent the same type of information but are sparsely populated.

### Step 6: `CSV File Splitter`

* **Task:** Breaks down massive files into smaller chunks.
* **Modes:**
* *Row-based:* Splits files after a specified number of data rows.
* *Column-based:* Slices out a specific subset of columns into a brand-new file.



### Step 7: `Data Deletion Tool`

* **Task:** Cleans out unwanted or empty data.
* **Modes:** Delete rows based on empty cells, delete specific columns completely, or hard-delete data rows by their exact row number.

### Step 8: `Column Name Change`

* **Task:** Quickly renames column headers using a simple mapping format (e.g., `1>SampleID`).

### Step 9: `Search & Copy Module`

* **Task:** A powerful grep-like search tool. You input specific terms, and it scans the dataset for partial matches.
* **Use Case:** You can extract either the entire *Rows* or the specific *Columns* that contain the matching terms and seamlessly save them into a new dataset.

---

## Step-by-Step Usage Guide

FroCSV uses an interactive prompt system. You do not need to memorize complex command-line flags. Just answer the prompts on the screen:

1. **Select a Tool:** Type the number (1-9) corresponding to the module you want to use from the main menu.
2. **Provide File Paths:** You will be prompted to enter the path to your source CSV file(s) or folder. You can easily drag and drop files into the terminal (the script automatically strips quotes and handles formatting).
3. **Answer Tool Prompts:** Depending on the tool chosen, input the required indices or mappings (e.g., entering `1, 3-5` to select specific columns).
4. **Choose Output Mode:** Decide whether you want to OVERWRITE the existing file or save the changes as a NEW file in a specified destination folder.
5. **Confirm & Run:** The tool will print a comprehensive summary of your configuration and the planned operation. Type `y` to confirm, and the pipeline will execute while displaying a progress bar.

---

## Understanding the Outputs

FroCSV ensures data safety and keeps your workspace highly organized. It never overwrites data without confirmation and utilizes temporary files during processing to prevent corruption during unexpected interruptions.

**Example Output Structure:**

```text
Your_Output_Folder/
├── Cleaned_Dataset.csv                      <-- Your processed output file
└── FroCSVLog_search_module_20260803-1430.log  <-- Detailed operation log

```

* **Intelligent Logging:** Every operation generates a timestamped `.log` file (e.g., `FroCSVLog_[tool_name]_[timestamp].log`). This master log records your input summary, planned operations, exact terminal outputs, rows deleted/merged, and any CSV parsing errors.
* **Audit Trail:** These logs make it incredibly easy to troubleshoot your workflow, confirm exactly what data was dropped, and reproduce your data-cleaning steps later.

---

**Author:** Built by karthxk ([https://karthxk0.github.io/](https://www.google.com/search?q=https://karthxk0.github.io/))
*Disclaimer: AI was utilized to assist in the debugging, restructuring, and refinement of the code and this documentation.*
