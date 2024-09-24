# Breeder Pair Selector

**Breeder Pair Selector © Software by Meghamsh Teja Konda**

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Usage Instructions](#usage-instructions)
    1. [Load Excel File](#1-load-excel-file)
    2. [Manage Genes and Classes (Optional)](#2-manage-genes-and-classes-optional)
    3. [Enter Desired Genotype](#3-enter-desired-genotype)
    4. [Find Breeder Pairs](#4-find-breeder-pairs)
    5. [Export Results (Optional)](#5-export-results-optional)
    6. [Mark Breeder Pairs in Excel (Optional)](#6-mark-breeder-pairs-in-excel-optional)
    7. [View Logs](#7-view-logs)
    8. [Settings](#8-settings)
    9. [View and Manage Existing Genes and Classes](#9-view-and-manage-existing-genes-and-classes)
- [Excel Sheet Formatting Guidelines](#excel-sheet-formatting-guidelines)
  1. [File Format](#file-format)
  2. [Sheet Naming](#sheet-naming)
  3. [Column Headers](#column-headers)
  4. [Breeder Data](#breeder-data)
  5. [Genotype Information](#genotype-information)
  6. [Colored Cells for Exclusion](#colored-cells-for-exclusion)
  7. [Additional Optional Columns](#additional-optional-columns)
  8. [Example Sheet Format](#example-sheet-format)
- [Clone the Repository](#clone-the-repository)
- [License](#license)
- [Contact](#contact)

## Overview

Breeder Pair Selector is a Python-based GUI application designed to assist in selecting optimal breeder pairs based on desired genotypes. Utilizing PyQt5 for the user interface and Pandas for data processing, this tool streamlines the breeder selection process, ensuring accurate and efficient pairing.

## Features

- **Gene and Class Management:** Easily add, view, and delete gene-class pairs.
- **Excel File Loading:** Import breeder data from Excel files with multiple sheets.
- **Genotype Input:** Support for various genotype input formats with real-time validation.
- **Breeder Pair Analysis:** Identify direct and indirect breeder pairs with probability and similarity scores.
- **Data Export:** Export results to CSV, Excel, or PDF formats.
- **Excel Marking:** Highlight suggested breeder pairs directly in your Excel files.
- **User Settings:** Customize application preferences, including language selection.
- **Comprehensive Logging:** Monitor application actions and debug effectively.

## Installation

### Prerequisites

- **Python:** Version 3.6 or higher
- **pip:** Python package installer

### Usage Instructions

#### 1. Load Excel File

- **Action:** Click the `Load Excel File` button.
- **Description:** Select and load your breeder data from an Excel file. The application will process the data, excluding any breeders marked in colored rows if applicable.

#### 2. Manage Genes and Classes (Optional)

- **Add Gene-Class Pairs:**
  - **Action:** Enter the gene name and its corresponding class in the provided fields.
  - **Button:** Click `Add Gene-Class Pair`.
  - **Description:** Adds the entered gene and class to the gene database for future reference.

- **Delete Gene-Class Pairs:**
  - **Action:** Click the `View Genes and Classes` button.
  - **Description:** View a list of all existing gene names and their corresponding classes.
  - **Delete:** Select the desired pairs and click `Delete Selected` to remove them from the database.

#### 3. Enter Desired Genotype

- **Action:** Input your desired genotype in the provided field.
- **Supported Formats:**
  - **Delimited Format:** `gene:allele`  
    *Example:* `cx:+/+ e22:f/+ ifnar:f/f`
  - **Space-Separated Format:** `gene allele`  
    *Example:* `cx +/+ e22 f/+ ifnar f/f`
  - **Mixed Delimiters:** Combination of both  
    *Example:* `cx:+/+ f/+ e22:f/+`
- **Description:** The application supports various input formats for flexibility. Real-time validation will indicate if the format is correct.

#### 4. Find Breeder Pairs

- **Action:** Click the `Find Breeder Pairs` button.
- **Description:** Analyze the loaded breeder data based on the desired genotype and generate suggestions for optimal breeder pairs. Results will be displayed in the direct and indirect breeder pairs tables.

#### 5. Export Results (Optional)

- **Action:** Use the export buttons located below the breeder pairs tables.
- **Options:**
  - **CSV:** Export the direct or indirect breeder pair suggestions to a CSV file.
  - **Excel:** Export the results to an Excel file.
  - **PDF:** Export the suggestions as a PDF document.

#### 6. Mark Breeder Pairs in Excel (Optional)

- **Action:** Click the `Mark Breeder Pairs in Excel` button.
- **Description:** Highlight the suggested breeder pairs directly in your Excel file by coloring the rows and assigning unique pair tags.

#### 7. View Logs

- **Location:** `Application Logs` section at the bottom of the application window.
- **Description:** Monitor real-time logs of application actions, errors, and other relevant information.

#### 8. Settings

- **Action:** Click the `Settings` button.
- **Description:** Access the settings dialog to customize application preferences such as language selection.

#### 9. View and Manage Existing Genes and Classes

- **Action:** Click the `View Genes and Classes` button.
- **Description:** Display a list of all existing gene names and their corresponding classes in a table format.

## Excel Sheet Formatting Guidelines

### 1. File Format
- **Excel Format:** The file must be in .xlsx format.
- **Sheet Structure:** The file can have multiple sheets, each representing a different set of breeders.

### 2. Sheet Naming
- **Naming Convention:** Sheet names should avoid special characters and use alphabetic characters, numbers, and underscores (e.g., `Breeder_Group_A`, `Batch1_September`).

### 3. Column Headers
- **Required Columns:** 
  - `breeder_name`: Unique identifier for the breeder.
  - `dob`: Date of birth of the breeder (in YYYY-MM-DD format).
  - `gender`: Gender of the breeder, typically Male or Female.
  - `strain`: (Optional) Strain of the breeder.
  - Specific gene columns (e.g., `cx (cre)`, `ifnar (flox)`).

### 4. Breeder Data
- **Age Calculation:** The application calculates breeder age using the `dob` column. Only breeders between 2 and 6 months old will be considered for pairing.

### 5. Genotype Information
- **Gene Data:** Each gene should have its own column in the format `gene_class` (e.g., `cx (cre)`, `ifnar (flox)`).
- **Alleles:** Use valid alleles such as +/-, f/+, or f/f.

### 6. Colored Cells for Exclusion
- **Exclusion by Color:** If you want to exclude breeders, color their row in a non-white color (e.g., yellow).

### 7. Additional Optional Columns
- `pair_tag`: After generating breeder pairs, the application can mark pairs directly in the Excel sheet.

### 8. Example Sheet Format

```plaintext
breeder_name  dob          gender  strain    cx (cre)  ifnar (flox)  rce (reporter)
Breeder_1     2023-03-01   Male    C57BL/6   +/-     f/+       -/-           
Breeder_2     2023-02-15   Female  C57BL/6   +/+     f/f       -/-           
Breeder_3     2023-04-10   Male    BALB/c    +/+     +/+       +/-           
Breeder_4     2023-05-05   Female  BALB/c    +/-     +/+       -/-           
