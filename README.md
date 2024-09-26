# Breeder Pair Selector

**Breeder Pair Selector** is a comprehensive desktop application designed to assist researchers and breeders in selecting optimal breeder pairs based on genetic genotypes. Utilizing an intuitive graphical user interface (GUI), the application facilitates the management of gene databases, loading and processing breeder data from Excel files, and exporting actionable breeder pair suggestions.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Installation Files](#installation-files)
- [Usage](#usage)
  - [1. Load Excel File](#1-load-excel-file)
  - [2. Manage Genes and Classes](#2-manage-genes-and-classes)
  - [3. Enter Desired Genotype](#3-enter-desired-genotype)
  - [4. Find Breeder Pairs](#4-find-breeder-pairs)
  - [5. Export Results](#5-export-results)
  - [6. Mark Breeder Pairs in Excel](#6-mark-breeder-pairs-in-excel)
  - [7. View Logs](#7-view-logs)
  - [8. View Mice Details](#8-view-mice-details)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **Gene Database Management:** Add, view, and delete gene-class pairs to customize your genetic analysis.
- **Excel File Loading:** Import breeder data from Excel files with support for multiple sheets and automated data cleaning.
- **Genotype Parsing:** Input desired genotypes in flexible formats with real-time validation.
- **Breeder Pair Analysis:** Generate direct and indirect breeder pair suggestions based on genetic compatibility and similarity scores.
- **Export Functionality:** Save results in CSV, Excel, or PDF formats for further analysis or reporting.
- **Excel Integration:** Highlight recommended breeder pairs directly in your Excel files with unique pair tags.
- **Mice Details Viewer:** Filter and export mice details based on age criteria.
- **Comprehensive Logging:** Monitor application activities and debug processes through an integrated log viewer.
- **User-Friendly Interface:** Intuitive GUI built with PyQt5 for seamless user experience.

## Installation

### Installation Files

Download the appropriate installer for your operating system:

- **Windows:** [Download Installer](https://drive.google.com/file/d/1eExExXXUFelkjGuwfKPPkG5oy_41kBgZ/view?usp=drive_link)
- **Mac:** Not available yet

**Note:** This application is currently available for Windows only. Mac support will be provided in future releases.

## Usage

### 1. Load Excel File

- **Step 1:** Click the **"Load Excel File"** button.
- **Step 2:** Select your breeder data Excel file (`.xlsx` format).
- **Step 3:** The application will process the file, excluding any breeders based on row coloring and filtering by age.

### 2. Manage Genes and Classes

- **Adding a Gene-Class Pair:**
  - Enter the gene name in the **"Gene Name"** field.
  - Select the gene class (e.g., Cre, Reporter, Flox) from the dropdown.
  - Click **"Add Gene-Class Pair"** to save.

- **Viewing and Deleting Gene-Class Pairs:**
  - Click the **"View Genes and Classes"** button.
  - In the dialog, select one or more gene-class pairs.
  - Click **"Delete Selected"** to remove them from the database.

### 3. Enter Desired Genotype

- **Input Formats Supported:**
  - **Delimited Format:** `gene:allele` (e.g., `cat:+/+ dog:f/+`)
  - **Space-Separated Format:** `gene allele` (e.g., `cat +/+ dog f/+`)
  - **Mixed Delimiters:** Combination of both (e.g., `cat:+/+ dog:f/+`)

- **Real-Time Validation:** The input field provides immediate feedback on the validity of the entered genotype.

### 4. Find Breeder Pairs

- After loading the Excel file and entering the desired genotype, click the **"Find Breeder Pairs"** button.
- The application will analyze the data and display suggested direct and indirect breeder pairs based on genetic compatibility.

### 5. Export Results

- **Direct Breeder Pairs:** Click **"Export Direct Pairs"** and choose your preferred format (CSV, Excel, PDF).
- **Indirect Breeder Pairs:** Click **"Export Indirect Pairs"** and select the desired export format.

### 6. Mark Breeder Pairs in Excel

- Click the **"Mark Breeder Pairs in Excel"** button to highlight suggested pairs in your loaded Excel file.
- The application will color the relevant rows and assign unique pair tags for easy identification.

### 7. View Logs

- Monitor application activities in the **"Application Logs"** section located at the bottom of the interface.
- Logs include informational messages, warnings, and error details to help with debugging and tracking actions.

### 8. View Mice Details

- Click the **"Show Mice Details"** button to open a dialog where you can filter mice based on age range.
- Export the filtered mice details as needed.

## Screenshots

![image](https://github.com/user-attachments/assets/030e091e-4c27-42be-a818-404d2f60fe27)


![image](https://github.com/user-attachments/assets/b5944dbe-0dc8-43cf-a2c9-a3d7b7fb7e7b)


![image](https://github.com/user-attachments/assets/f447186f-7dac-4473-a953-46de64bacb12)


## Requirements

- **Operating System:** Windows 10 or higher
- **Hardware:** Minimum 2GB RAM, 100MB free disk space
- **Dependencies:** All necessary dependencies are bundled within the installer. No additional installation is required.

## Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the Repository**
2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/YourFeature
   ```

3. **Commit Your Changes**

   ```bash
   git commit -m "Add Your Feature"
   ```

4. **Push to the Branch**

   ```bash
   git push origin feature/YourFeature
   ```

5. **Open a Pull Request**

Please ensure your code follows the project's coding standards and includes relevant documentation and tests.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For any inquiries or support, please contact:

**Meghamsh Teja Konda**  
Email: [meghamshteja555@gmail.com)
Twitter(X): https://x.com/MeghamshTeja


---

*Happy Breeding!*
