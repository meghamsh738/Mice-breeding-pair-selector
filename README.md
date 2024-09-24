Download the setup.exe from here : https://drive.google.com/file/d/14JcqLGHsASBI6K_-xVbnJxQ-_cp__JVC/view?usp=sharing

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
- [Clone the Repository](#clone-the-repository)
- [License](#license)
- [Contact](#contact)

## Overview

Breeder Pair Selector is a Python-based GUI application built using chatgpt-o1 assistance, designed to assist in selecting optimal breeder pairs based on desired genotypes. Utilizing PyQt5 for the user interface and Pandas for data processing, this tool streamlines the breeder selection process, ensuring accurate and efficient pairing.

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

**Add Gene-Class Pairs:**

- **Action:** Enter the gene name and its corresponding class in the provided fields.
- **Button:** Click `Add Gene-Class Pair`.
- **Description:** Adds the entered gene and class to the gene database for future reference.

**Delete Gene-Class Pairs:**

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
- **Description:** Save the breeder pair suggestions in your preferred format for further analysis or record-keeping.

#### 6. Mark Breeder Pairs in Excel (Optional)

- **Action:** Click the `Mark Breeder Pairs in Excel` button.
- **Description:** Highlight the suggested breeder pairs directly in your Excel file by coloring the rows in yellow and assigning unique pair tags. This helps in easily identifying and managing the recommended pairs within your dataset.

#### 7. View Logs

- **Location:** `Application Logs` section at the bottom of the application window.
- **Description:** Monitor real-time logs of application actions, errors, and other relevant information. Useful for tracking operations and debugging purposes.

#### 8. Settings

- **Action:** Click the `Settings` button.
- **Description:** Access the settings dialog to customize application preferences such as language selection and other user-specific configurations.

#### 9. View and Manage Existing Genes and Classes

- **Action:** Click the `View Genes and Classes` button.
- **Description:** Display a list of all existing gene names and their corresponding classes in a table format.

**Delete Gene-Class Pairs:**

- **Action:** Select the desired rows in the table.
- **Button:** Click `Delete Selected` to remove the selected gene-class pairs from the database.

## Clone the Repository

To clone the repository to your local machine, use the following commands:

```bash
git clone https://github.com/yourusername/BreederPairSelector.git
cd BreederPairSelector
```
Sure! Below is an updated and well-formatted `README.md` for your **Breeder Pair Selector** project, optimized for GitHub. It includes a table of contents for easy navigation and ensures all sections are clearly structured.

---

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

**Add Gene-Class Pairs:**

- **Action:** Enter the gene name and its corresponding class in the provided fields.
- **Button:** Click `Add Gene-Class Pair`.
- **Description:** Adds the entered gene and class to the gene database for future reference.

**Delete Gene-Class Pairs:**

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
- **Description:** Save the breeder pair suggestions in your preferred format for further analysis or record-keeping.

#### 6. Mark Breeder Pairs in Excel (Optional)

- **Action:** Click the `Mark Breeder Pairs in Excel` button.
- **Description:** Highlight the suggested breeder pairs directly in your Excel file by coloring the rows in yellow and assigning unique pair tags. This helps in easily identifying and managing the recommended pairs within your dataset.

#### 7. View Logs

- **Location:** `Application Logs` section at the bottom of the application window.
- **Description:** Monitor real-time logs of application actions, errors, and other relevant information. Useful for tracking operations and debugging purposes.

#### 8. Settings

- **Action:** Click the `Settings` button.
- **Description:** Access the settings dialog to customize application preferences such as language selection and other user-specific configurations.

#### 9. View and Manage Existing Genes and Classes

- **Action:** Click the `View Genes and Classes` button.
- **Description:** Display a list of all existing gene names and their corresponding classes in a table format.

**Delete Gene-Class Pairs:**

- **Action:** Select the desired rows in the table.
- **Button:** Click `Delete Selected` to remove the selected gene-class pairs from the database.

## Clone the Repository

To clone the repository to your local machine, use the following commands:

```bash
git clone https://github.com/yourusername/BreederPairSelector.git
cd BreederPairSelector
```

## License

[MIT License](LICENSE)

## Contact

For any questions or feedback, please contact **Meghamsh Teja Konda** at [meghamshteja555@gmail.com]

---
