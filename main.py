import sys
import pandas as pd
import re
import random
import string
import json
import logging
import threading
from pathlib import Path
from itertools import product
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QLineEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QHBoxLayout, QHeaderView, QGroupBox, QProgressBar,
    QDialog, QFormLayout, QComboBox, QScrollArea, QMenu, QAction,
    QToolButton, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class GeneDatabase:
    def __init__(self, filename='gene_database.json'):
        self.filename = Path(filename).expanduser()
        self.transgene_db = {}
        self.transgene_to_category = {}
        self.wildtype_genotype = {}
        self.lock = threading.Lock()
        self.load_database()
        self.create_reverse_mapping()

    def load_database(self):
        try:
            with self.lock:
                with open(self.filename, 'r') as f:
                    self.transgene_db = json.load(f)
            logging.info(f"Gene database loaded from {self.filename}.")
        except FileNotFoundError:
            logging.info("No existing gene database found. Starting with empty database.")
            self.transgene_db = {}
        except Exception as e:
            logging.exception("Failed to load gene database.")
            # Avoid UI popups from worker threads; log only.

    def save_database(self):
        try:
            with self.lock:
                self.filename.parent.mkdir(parents=True, exist_ok=True)
                with open(self.filename, 'w') as f:
                    json.dump(self.transgene_db, f, indent=4)
            logging.info(f"Gene database saved to {self.filename}.")
        except Exception as e:
            logging.exception("Failed to save gene database.")
            # Avoid UI popups from worker threads; log only.

    def create_reverse_mapping(self):
        self.transgene_to_category = {}
        self.wildtype_genotype = {}
        for category, genes in self.transgene_db.items():
            for gene in genes:
                self.transgene_to_category[gene.lower()] = category
                gene_lower = gene.lower()
                if category in ['Cre', 'Reporter']:
                    self.wildtype_genotype[gene_lower] = '-/-'
                elif category == 'Flox':
                    self.wildtype_genotype[gene_lower] = '+/+'
                else:
                    self.wildtype_genotype[gene_lower] = '+/+'

    def add_gene_class_pair(self, gene, gene_class):
        gene = gene.strip().lower()
        gene_class = gene_class.strip().title()
        if not gene or not gene_class:
            raise ValueError("Gene name and class name cannot be empty.")
        with self.lock:
            if gene in self.transgene_to_category:
                raise ValueError(f"The gene '{gene}' already exists in the '{self.transgene_to_category[gene]}' class.")
            if gene_class not in self.transgene_db:
                self.transgene_db[gene_class] = []
            self.transgene_db[gene_class].append(gene)
            self.transgene_to_category[gene] = gene_class
            if gene_class in ['Cre', 'Reporter']:
                self.wildtype_genotype[gene] = '-/-'
            elif gene_class == 'Flox':
                self.wildtype_genotype[gene] = '+/+'
            else:
                self.wildtype_genotype[gene] = '+/+'
        self.save_database()
        logging.info(f"Added gene '{gene}' to class '{gene_class}'.")

    def delete_gene_class_pair(self, gene, gene_class):
        gene = gene.strip().lower()
        gene_class = gene_class.strip().title()
        if gene_class not in self.transgene_db:
            raise ValueError(f"The class '{gene_class}' does not exist.")
        with self.lock:
            if gene not in self.transgene_db.get(gene_class, []):
                raise ValueError(f"The gene '{gene}' does not exist in the '{gene_class}' class.")
            self.transgene_db[gene_class].remove(gene)
            if not self.transgene_db[gene_class]:
                del self.transgene_db[gene_class]
            del self.transgene_to_category[gene]
            del self.wildtype_genotype[gene]
        self.save_database()
        logging.info(f"Deleted gene '{gene}' from class '{gene_class}'.")


class FileLoaderThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(pd.DataFrame, list)
    error = pyqtSignal(str)

    def __init__(self, file_path, gene_db):
        super().__init__()
        self.file_path = file_path
        self.gene_db = gene_db

    def run(self):
        try:
            self.progress.emit(10)
            all_sheets = pd.read_excel(self.file_path, sheet_name=None, engine='openpyxl')
            self.progress.emit(30)
            wb = load_workbook(filename=self.file_path, data_only=True)
            excluded_breeders = []
            sheet_breeders_map = {}
            processed_sheets = {}
            for sheet_name, df in all_sheets.items():
                ws = wb[sheet_name]
                # Define known non-gene columns
                non_gene_columns = {'breeder_name', 'gender', 'dob', 'strain', 'sheet', 'age_months', 'age', 'notes'}
                standardized_headers = []
                gene_columns = []
                for header in df.columns:
                    header_str = str(header).strip()
                    header_std = header_str.lower().replace(' ', '_').replace('(', '').replace(')', '')
                    if header_std in non_gene_columns:
                        # Keep non-gene columns as is
                        standardized_headers.append(header_std)
                    else:
                        # Process as gene column
                        if '(' in header_str and ')' in header_str:
                            # Extract gene name and class
                            gene_name, gene_class = header_str.split('(')
                            gene_name = gene_name.strip().lower().replace(' ', '_').replace('(', '').replace(')', '')
                            gene_class = gene_class.strip(')').strip().title()
                        else:
                            # Gene column without '()' - assign default class 'Flox' or appropriate
                            gene_name = header_std
                            gene_class = 'Flox'  # Default class; adjust if needed
                        standardized_headers.append(gene_name)
                        gene_columns.append((gene_name, gene_class))
                        if gene_name not in self.gene_db.transgene_to_category:
                            self.gene_db.add_gene_class_pair(gene_name, gene_class)
                df.columns = standardized_headers  # Set standardized headers
                logging.debug(f"Standardized headers for sheet '{sheet_name}': {standardized_headers}")
                df['sheet'] = sheet_name
                # Rest of your code remains the same
                colored_rows = set()
                for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
                    for cell in row:
                        if cell.fill and cell.fill.start_color and cell.fill.start_color.type != 'indexed':
                            cell_color = cell.fill.start_color.rgb
                            if cell_color not in [None, '00000000', 'FFFFFFFF']:
                                colored_rows.add(idx)
                                break
                if 'breeder_name' in standardized_headers:
                    if colored_rows:
                        breeder_name_col = standardized_headers.index('breeder_name')
                        breeder_names = [row[breeder_name_col] for row_num, row in
                                         enumerate(df.itertuples(index=False), start=2) if row_num in colored_rows]
                        excluded_breeders.extend(breeder_names)
                        rows_to_exclude = [idx - 2 for idx in colored_rows if idx > 1]
                        df = df.drop(index=rows_to_exclude)
                    processed_sheets[sheet_name] = df
                else:
                    logging.warning(
                        f"'breeder_name' column not found in sheet '{sheet_name}'. Skipping exclusion based on color.")
                if 'breeder_name' in df.columns:
                    breeders_in_sheet = df['breeder_name'].dropna().tolist()
                    sheet_breeders_map[sheet_name] = breeders_in_sheet
                else:
                    sheet_breeders_map[sheet_name] = []
            if not processed_sheets:
                error_msg = "No valid data found in the Excel file. Please ensure that sheets contain the 'breeder_name' column."
                logging.error(error_msg)
                self.error.emit(error_msg)
                return
            combined_breeders = pd.concat(processed_sheets.values(), ignore_index=True)
            self.progress.emit(60)
            logging.info(
                f"Successfully loaded {len(processed_sheets)} sheet(s) with a total of {len(combined_breeders)} breeder(s) from the Excel file.")
            if excluded_breeders:
                logging.info(
                    f"Ignored {len(excluded_breeders)} breeder(s) due to colored rows: {excluded_breeders}")
            else:
                logging.info("No breeders were excluded based on row coloring.")
            if 'dob' in combined_breeders.columns:
                today = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
                combined_breeders['dob'] = pd.to_datetime(combined_breeders['dob'], errors='coerce')
                combined_breeders['age_months'] = ((today - combined_breeders['dob']).dt.days) / 30
                older_breeders = combined_breeders[combined_breeders['age_months'] > 6]
                self.progress.emit(80)
                filtered_breeders = combined_breeders[
                    (combined_breeders['age_months'] >= 2) &
                    (combined_breeders['age_months'] <= 6)
                    ]
                logging.info(f"Filtered breeders to {len(filtered_breeders)} within age range (2-6 months).")
            else:
                error_msg = "The Excel file does not contain a 'dob' (date of birth) column.\n" \
                            "Age-based filtering will be skipped, and all breeders will be considered."
                logging.warning(error_msg)
                self.error.emit(error_msg)
                return
            self.progress.emit(90)
            # Update gene database mapping after adding new genes
            self.gene_db.create_reverse_mapping()
            self.progress.emit(100)
            self.finished.emit(filtered_breeders, excluded_breeders)
        except Exception as e:
            logging.exception("An error occurred while loading the file.")
            self.error.emit(str(e))



class QTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        def append_log():
            self.text_edit.append(msg)
        QTimer.singleShot(0, append_log)


import csv
import io
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QMenu, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class GeneViewerDialog(QDialog):
    def __init__(self, gene_db, parent=None):
        super().__init__(parent)
        self.gene_db = gene_db
        self.setWindowTitle("View and Manage Genes and Classes")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.genes_table = QTableWidget()
        self.genes_table.setColumnCount(2)
        self.genes_table.setHorizontalHeaderLabels(["Gene Name", "Class"])
        self.genes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.genes_table.setRowCount(0)
        self.genes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.genes_table.setSelectionMode(QTableWidget.MultiSelection)
        layout.addWidget(self.genes_table)
        self.populate_table()

        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_genes)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setFixedWidth(100)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Set context menu for genes_table
        self.genes_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.genes_table.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        menu = QMenu()
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selected_cells)
        menu.addAction(copy_action)
        menu.exec_(self.genes_table.viewport().mapToGlobal(position))

    def copy_selected_cells(self):
        selection = self.genes_table.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            cols = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = cols[-1] - cols[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                col = index.column() - cols[0]
                table[row][col] = self.genes_table.item(index.row(), index.column()).text()
            stream = io.StringIO()
            csv.writer(stream, delimiter='\t').writerows(table)
            QApplication.clipboard().setText(stream.getvalue())
            QMessageBox.information(self, "Copied", "Selected cells have been copied to the clipboard.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select cells to copy.")

    def populate_table(self):
        self.genes_table.setRowCount(0)
        for category, genes in self.gene_db.transgene_db.items():
            for gene in genes:
                row_position = self.genes_table.rowCount()
                self.genes_table.insertRow(row_position)
                self.genes_table.setItem(row_position, 0, QTableWidgetItem(gene))
                self.genes_table.setItem(row_position, 1, QTableWidgetItem(category))

    def delete_selected_genes(self):
        selected_rows = set([index.row() for index in self.genes_table.selectedIndexes()])
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one gene-class pair to delete.")
            return
        confirmation = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the selected {len(selected_rows)} gene-class pair(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirmation == QMessageBox.Yes:
            try:
                genes_to_delete = []
                for row in selected_rows:
                    gene_item = self.genes_table.item(row, 0)
                    class_item = self.genes_table.item(row, 1)
                    if gene_item and class_item:
                        gene = gene_item.text()
                        gene_class = class_item.text()
                        genes_to_delete.append((gene, gene_class))
                for gene, gene_class in genes_to_delete:
                    self.gene_db.delete_gene_class_pair(gene, gene_class)
                self.populate_table()
                QMessageBox.information(self, "Deletion Successful", "Selected gene-class pair(s) have been deleted.")
                logging.info(f"Deleted gene-class pairs: {genes_to_delete}")
            except ValueError as ve:
                QMessageBox.warning(self, "Deletion Error", str(ve))
                logging.error(f"Deletion Error: {ve}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while deleting gene-class pair(s):\n{e}")
                logging.exception("Deletion Error:")



class DataProcessor:
    def __init__(self, gene_db):
        self.gene_db = gene_db

    def parse_genotype_input(self, input_str):
        genotype = {}
        missing_genes = []
        tokens = re.split(r'[,\s]+', input_str)
        if any(':' in token or '=' in token for token in tokens):
            for token in tokens:
                if ':' in token or '=' in token:
                    gene, allele = re.split(r'[:=]', token, maxsplit=1)
                    gene = gene.strip().lower()
                    allele = allele.strip().lower()
                    if re.match(r'^[+\-f]{1,2}/[+\-f]{1,2}$', allele):
                        genotype[gene] = allele
                    else:
                        logging.warning(f"Unrecognized allele format: '{allele}' for gene '{gene}'")
                else:
                    logging.warning(f"Unrecognized genotype token without delimiter: '{token}'")
        else:
            if len(tokens) % 2 != 0:
                logging.warning("Incomplete gene-allele pairs detected.")
            for i in range(0, len(tokens), 2):
                if i + 1 >= len(tokens):
                    logging.warning(f"Missing allele information for gene '{tokens[i]}'.")
                    break
                gene = tokens[i].strip().lower()
                allele = tokens[i + 1].strip().lower()
                if re.match(r'^[+\-f]{1,2}/[+\-f]{1,2}$', allele):
                    genotype[gene] = allele
                else:
                    logging.warning(f"Unrecognized allele format: '{allele}' for gene '{gene}'")
        logging.debug(f"Parsed genotype input: {genotype}")

        # Identify missing genes
        for gene in genotype.keys():
            if gene not in self.gene_db.transgene_to_category:
                missing_genes.append(gene)

        # Add wild type genotypes for unspecified genes
        for gene in self.gene_db.transgene_to_category.keys():
            if gene not in genotype:
                genotype[gene] = self.gene_db.wildtype_genotype.get(gene, '+/+')

        return genotype, missing_genes

    def normalize_genotype(self, geno_str):
        alleles = geno_str.split('/')
        sorted_alleles = sorted(alleles, key=lambda x: x)
        normalized = '/'.join(sorted_alleles)
        logging.debug(f"Normalized genotype: {normalized}")
        return normalized

    def get_alleles(self, allele_str):
        return allele_str.replace(' ', '').split('/')

    def compute_offspring_genotype(self, parent1, parent2):
        alleles1 = self.get_alleles(parent1)
        alleles2 = self.get_alleles(parent2)
        offspring = [self.normalize_genotype(a + '/' + b) for a in alleles1 for b in alleles2]
        logging.debug(f"Offspring genotypes from parents ({parent1}, {parent2}): {offspring}")
        return offspring

    def calculate_probability(self, offspring_genotypes, desired_geno):
        desired = self.normalize_genotype(desired_geno)
        total = len(offspring_genotypes)
        desired_count = offspring_genotypes.count(desired)
        probability = (desired_count / total) * 100
        logging.debug(f"Desired genotype '{desired}' probability: {probability}%")
        return probability

    def calculate_similarity_score(self, offspring_genos, desired_geno):
        desired = set(self.normalize_genotype(desired_geno).split('/'))
        similarity = 0
        for geno in offspring_genos:
            offspring_set = set(geno.split('/'))
            matches = desired.intersection(offspring_set)
            similarity += len(matches)
        average_similarity = similarity / len(offspring_genos) if offspring_genos else 0
        similarity_score = (average_similarity / 2) * 100
        logging.debug(f"Calculated similarity score: {similarity_score}%")
        return similarity_score

    def find_breeder_pairs(self, breeders_df, desired_genotype, specified_genes):
        # Define gene categories and gather all genes from the desired genotype
        gene_categories = ['Cre', 'Reporter', 'Flox']
        all_genes = []
        for category in gene_categories:
            genes_in_category = self.gene_db.transgene_db.get(category, [])
            all_genes.extend(genes_in_category)

        specified_genes = all_genes  # Use all genes from desired genotype
        direct_pairs = []
        indirect_pairs = []
        male_labels = {'male', 'm'}
        female_labels = {'female', 'f'}
        males = breeders_df[breeders_df['gender'].str.lower().isin(male_labels)]
        females = breeders_df[breeders_df['gender'].str.lower().isin(female_labels)]
        logging.info(f"Identified {len(males)} male breeder(s) and {len(females)} female breeder(s).")
        all_possible_pairs = product(males.iterrows(), females.iterrows())

        # Define non-gene columns to identify gene columns later
        non_gene_columns = {'breeder_name', 'gender', 'dob', 'strain', 'sheet', 'age_months', 'age', 'notes'}

        for pair in all_possible_pairs:
            male_info, female_info = pair
            m_idx, male = male_info
            f_idx, female = female_info

            # Identify gene columns present in male and female breeders
            male_genes_present = set(male.index) - non_gene_columns
            female_genes_present = set(female.index) - non_gene_columns

            # Check if breeders have only specified genes
            if not male_genes_present.issubset(specified_genes) or not female_genes_present.issubset(specified_genes):
                logging.debug(f"Skipping pair ({male['breeder_name']}, {female['breeder_name']}) due to extra genes.")
                continue  # Skip this pair as breeders have extra genes

            # Proceed with existing processing
            male_strain = str(male['strain']).strip().lower() if 'strain' in male else ""
            female_strain = str(female['strain']).strip().lower() if 'strain' in female else ""
            same_strain = male_strain == female_strain
            strain_warning = not same_strain
            probabilities = []
            breeder_genotypes = {'Male': {}, 'Female': {}}
            for gene in specified_genes:
                desired_allele = desired_genotype.get(gene, self.gene_db.wildtype_genotype.get(gene, '+/+'))
                category = self.gene_db.transgene_to_category.get(gene)
                if not category:
                    logging.warning(f"Gene '{gene}' is not recognized in the transgene database. Skipping.")
                    continue
                gene_class = category.lower()
                gene_col = gene.strip().lower()
                parent1_geno = male.get(gene_col, self.gene_db.wildtype_genotype.get(gene, '+/+'))
                parent2_geno = female.get(gene_col, self.gene_db.wildtype_genotype.get(gene, '+/+'))
                if pd.isna(parent1_geno):
                    parent1_geno = self.gene_db.wildtype_genotype.get(gene, '+/+')
                if pd.isna(parent2_geno):
                    parent2_geno = self.gene_db.wildtype_genotype.get(gene, '+/+')
                parent1_geno = str(parent1_geno).lower().replace(' ', '')
                parent2_geno = str(parent2_geno).lower().replace(' ', '')
                breeder_genotypes['Male'][gene] = parent1_geno
                breeder_genotypes['Female'][gene] = parent2_geno
                offspring_genos = self.compute_offspring_genotype(parent1_geno, parent2_geno)
                prob = self.calculate_probability(offspring_genos, desired_allele)
                probabilities.append(prob)
            if probabilities:
                overall_prob = 1
                for p in probabilities:
                    overall_prob *= (p / 100)
                overall_prob *= 100
            else:
                overall_prob = 0
            if overall_prob > 0:
                direct_pairs.append({
                    'Male': male['breeder_name'],
                    'Female': female['breeder_name'],
                    'Male Sheet': male['sheet'],
                    'Female Sheet': female['sheet'],
                    'Strain Warning': strain_warning,
                    'Probability (%)': round(overall_prob, 2),
                    'Breeder Genotypes': breeder_genotypes,
                    'Same Strain': "Yes" if same_strain else "No",
                    'Male Data': male,
                    'Female Data': female
                })
            else:
                similarity_scores = []
                for gene in specified_genes:
                    desired_allele = desired_genotype.get(gene, self.gene_db.wildtype_genotype.get(gene, '+/+'))
                    breeder_male_geno = breeder_genotypes['Male'].get(gene,
                                                                      self.gene_db.wildtype_genotype.get(gene, '+/+'))
                    breeder_female_geno = breeder_genotypes['Female'].get(gene, self.gene_db.wildtype_genotype.get(gene,
                                                                                                                   '+/+'))
                    offspring_genos = self.compute_offspring_genotype(breeder_male_geno, breeder_female_geno)
                    similarity = self.calculate_similarity_score(offspring_genos, desired_allele)
                    similarity_scores.append(similarity)
                average_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
                indirect_pairs.append({
                    'Male': male['breeder_name'],
                    'Female': female['breeder_name'],
                    'Male Sheet': male['sheet'],
                    'Female Sheet': female['sheet'],
                    'Strain Warning': strain_warning,
                    'Similarity Score (%)': round(average_similarity, 2),
                    'Breeder Genotypes': breeder_genotypes,
                    'Same Strain': "Yes" if same_strain else "No",
                    'Male Data': male,
                    'Female Data': female
                })
        direct_pairs_sorted = sorted(direct_pairs, key=lambda x: x['Probability (%)'], reverse=True)
        indirect_pairs_sorted = sorted(indirect_pairs, key=lambda x: x['Similarity Score (%)'], reverse=True)
        logging.info(
            f"Found {len(direct_pairs_sorted)} direct pair(s) and {len(indirect_pairs_sorted)} indirect pair(s).")
        return direct_pairs_sorted, indirect_pairs_sorted


class Exporter:
    @staticmethod
    def export_table_to_csv(table, default_filename):
        if table.rowCount() == 0:
            QMessageBox.information(None, "No Data", "There is no data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(None, "Save File", f"{default_filename}.csv",
                                              "CSV Files (*.csv);;All Files (*)")
        if path:
            try:
                headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                data = []
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                df = pd.DataFrame(data, columns=headers)
                df.to_csv(path, index=False)
                QMessageBox.information(None, "Success", f"Data exported successfully to {path}.")
                logging.info(f"Exported data to {path}.")
            except Exception as e:
                logging.exception("An error occurred while exporting data.")
                QMessageBox.critical(None, "Error", f"An error occurred while exporting data:\n{e}")

    @staticmethod
    def export_table_to_excel(table, default_filename):
        if table.rowCount() == 0:
            QMessageBox.information(None, "No Data", "There is no data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(None, "Save File", f"{default_filename}.xlsx",
                                              "Excel Files (*.xlsx);;All Files (*)")
        if path:
            try:
                headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                data = []
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                df = pd.DataFrame(data, columns=headers)
                df.to_excel(path, index=False)
                QMessageBox.information(None, "Success", f"Data exported successfully to {path}.")
                logging.info(f"Exported data to {path}.")
            except Exception as e:
                logging.exception("An error occurred while exporting data.")
                QMessageBox.critical(None, "Error", f"An error occurred while exporting data:\n{e}")

    @staticmethod
    def export_table_to_pdf(table, default_filename):
        try:
            from fpdf import FPDF
        except ImportError:
            QMessageBox.warning(None, "Dependency Missing", "Please install 'fpdf' to enable PDF export.\n\n"
                                                            "You can install it via pip:\n"
                                                            "pip install fpdf")
            return
        if table.rowCount() == 0:
            QMessageBox.information(None, "No Data", "There is no data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(None, "Save File", f"{default_filename}.pdf",
                                              "PDF Files (*.pdf);;All Files (*)")
        if path:
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                col_width = pdf.w / (len(table.horizontalHeader()) + 1)
                row_height = 10
                headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                for header in headers:
                    pdf.cell(col_width, row_height, header, border=1, align='C')
                pdf.ln(row_height)
                for row in range(table.rowCount()):
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        text = item.text() if item else ""
                        pdf.cell(col_width, row_height, text, border=1, align='C')
                    pdf.ln(row_height)
                pdf.output(path)
                QMessageBox.information(None, "Success", f"Data exported successfully to {path}.")
                logging.info(f"Exported data to {path}.")
            except Exception as e:
                logging.exception("An error occurred while exporting data.")
                QMessageBox.critical(None, "Error", f"An error occurred while exporting data:\n{e}")


import csv
import io
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class MiceDetailsDialog(QDialog):

    def copy_selected_cells(self):
        selection = self.mice_table.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            cols = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = cols[-1] - cols[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                col = index.column() - cols[0]
                table[row][col] = self.mice_table.item(index.row(), index.column()).text()
            stream = io.StringIO()
            csv.writer(stream, delimiter='\t').writerows(table)
            QApplication.clipboard().setText(stream.getvalue())
            QMessageBox.information(self, "Copied", "Selected cells have been copied to the clipboard.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select cells to copy.")

    def __init__(self, breeders_df, gene_db, parent=None):
        super().__init__(parent)
        self.breeders_df = breeders_df
        self.gene_db = gene_db
        self.setWindowTitle("Mice Details")
        self.setModal(True)
        self.resize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Select Age Range (months):"))
        self.min_age_spin = QSpinBox()
        self.min_age_spin.setRange(0, 120)
        self.min_age_spin.setValue(0)
        form_layout.addWidget(QLabel("Min:"))
        form_layout.addWidget(self.min_age_spin)
        self.max_age_spin = QSpinBox()
        self.max_age_spin.setRange(0, 120)
        self.max_age_spin.setValue(12)
        form_layout.addWidget(QLabel("Max:"))
        form_layout.addWidget(self.max_age_spin)
        layout.addLayout(form_layout)
        self.show_button = QPushButton("Show Mice")
        self.show_button.clicked.connect(self.show_mice)
        layout.addWidget(self.show_button)
        self.mice_table = QTableWidget()
        self.mice_table.setColumnCount(7)
        self.mice_table.setHorizontalHeaderLabels(
            ["Breeder Name", "Gender", "DOB", "Age (Months)", "Strain", "Sheet", "Genotype"])
        self.mice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.mice_table)
        export_button = QPushButton("Export Selected Mice")
        export_button.clicked.connect(self.export_selected_mice)
        layout.addWidget(export_button)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        self.setLayout(layout)

    def show_mice(self):
        min_age = self.min_age_spin.value()
        max_age = self.max_age_spin.value()
        filtered = self.breeders_df[
            (self.breeders_df['age_months'] >= min_age) &
            (self.breeders_df['age_months'] <= max_age)
            ]
        self.mice_table.setRowCount(0)
        gene_categories = self.gene_db.transgene_db  # category -> list of genes
        for index, row in filtered.iterrows():
            row_position = self.mice_table.rowCount()
            self.mice_table.insertRow(row_position)
            self.mice_table.setItem(row_position, 0, QTableWidgetItem(str(row.get('breeder_name', ''))))
            self.mice_table.setItem(row_position, 1, QTableWidgetItem(str(row.get('gender', ''))))
            dob = row.get('dob', '')
            if isinstance(dob, pd.Timestamp):
                dob_str = dob.strftime('%Y-%m-%d')
            else:
                dob_str = str(dob).split(' ')[0]
            self.mice_table.setItem(row_position, 2, QTableWidgetItem(dob_str))
            self.mice_table.setItem(row_position, 3, QTableWidgetItem(str(round(row.get('age_months', 0), 2))))
            self.mice_table.setItem(row_position, 4, QTableWidgetItem(str(row.get('strain', ''))))
            self.mice_table.setItem(row_position, 5, QTableWidgetItem(str(row.get('sheet', ''))))
            genotype_str = ""
            gene_columns = [col for col in row.index if
                            col not in ['breeder_name', 'gender', 'dob', 'age_months', 'age', 'notes', 'sheet',
                                        'strain']]
            for gene in gene_columns:
                allele = row.get(gene)
                if allele is None or pd.isna(allele):
                    continue  # Skip if allele is missing
                genotype_str += f"{gene} {allele} "
            self.mice_table.setItem(row_position, 6, QTableWidgetItem(genotype_str.strip()))

            # Remove duplicate setting of genotype
            # self.mice_table.setItem(row_position, 6, QTableWidgetItem(genotype_str.strip('; ')))
        self.mice_table.resizeColumnsToContents()
        self.mice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mice_table.resizeColumnsToContents()
        self.mice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def export_selected_mice(self):
        selected_rows = set([index.row() for index in self.mice_table.selectedIndexes()])
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one mouse to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "Mice_Details.csv",
                                              "CSV Files (*.csv);;All Files (*)")
        if path:
            try:
                headers = [self.mice_table.horizontalHeaderItem(i).text() for i in range(self.mice_table.columnCount())]
                data = []
                for row in selected_rows:
                    row_data = []
                    for col in range(self.mice_table.columnCount()):
                        item = self.mice_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                df = pd.DataFrame(data, columns=headers)

                # Extract genes from the 'Genotype' column
                genotype_series = df['Genotype'].str.strip().str.split(' ', expand=True)
                genotype_cols = {}
                for idx in genotype_series.index:
                    genotype_list = genotype_series.loc[idx].dropna().tolist()
                    for i in range(0, len(genotype_list), 2):
                        gene = genotype_list[i]
                        allele = genotype_list[i + 1] if i + 1 < len(genotype_list) else ''
                        if gene not in genotype_cols:
                            genotype_cols[gene] = [''] * len(df)
                        genotype_cols[gene][idx] = allele
                genotype_df = pd.DataFrame(genotype_cols)
                df = pd.concat([df.drop(columns=['Genotype']), genotype_df], axis=1)

                # Handle empty cells by filling with default values if necessary
                df.fillna('', inplace=True)
                df.to_csv(path, index=False)
                QMessageBox.information(self, "Success", f"Mice details exported successfully to {path}.")
                logging.info(f"Exported mice details to {path}.")
            except Exception as e:
                logging.exception("An error occurred while exporting mice details.")
                QMessageBox.critical(self, "Error", f"An error occurred while exporting mice details:\n{e}")


class BreederPairSelector(QWidget):
    def clear_results(self):
        self.direct_table.clearContents()
        self.direct_table.setRowCount(0)
        self.direct_table.setHorizontalHeaderLabels([])
        self.indirect_table.clearContents()
        self.indirect_table.setRowCount(0)
        self.indirect_table.setHorizontalHeaderLabels([])

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Breeder Pair Selector © Software by Meghamsh Teja Konda")
        self.setGeometry(100, 100, 1200, 800)
        self.gene_db = GeneDatabase()
        self.data_processor = DataProcessor(self.gene_db)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setup_logging()
        self.init_gene_management()
        self.init_file_loader()
        self.init_genotype_input()
        self.init_find_button()
        self.init_reminder()
        self.init_tables()
        self.init_export_buttons()
        self.init_modify_button()
        self.init_progress_bar()
        self.init_instructions_button()
        self.init_view_genes_button()
        self.init_show_mice_button()
        self.trademark_label = QLabel("© Software by Meghamsh Teja Konda")
        self.trademark_label.setAlignment(Qt.AlignCenter)
        self.trademark_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.layout.addWidget(self.trademark_label)
        self.breeders = pd.DataFrame()
        self.excel_file_path = ""
        self.sheet_breeders_map = {}
        self.max_age = 6

    def setup_logging(self):
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFont(QFont("Courier", 10))
        self.layout.addWidget(QLabel("Application Logs:"))
        self.layout.addWidget(self.log_text_edit)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        handler = QTextEditLogger(self.log_text_edit)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def init_gene_management(self):
        self.manage_gene_group = QGroupBox("Manage Genes and Classes (Optional)")
        self.manage_gene_layout = QHBoxLayout()
        self.manage_gene_group.setLayout(self.manage_gene_layout)

        self.gene_input = QLineEdit()
        self.gene_input.setPlaceholderText("Enter gene name (e.g., cat)")

        self.class_combo = QComboBox()
        self.class_combo.addItems(['Cre', 'Reporter', 'Flox'])

        self.add_gene_button = QPushButton("Add Gene-Class Pair")
        self.add_gene_button.clicked.connect(self.add_gene_class_pair)

        self.manage_gene_layout.addWidget(QLabel("Gene Name:"))
        self.manage_gene_layout.addWidget(self.gene_input)
        self.manage_gene_layout.addWidget(QLabel("Class:"))
        self.manage_gene_layout.addWidget(self.class_combo)
        self.manage_gene_layout.addWidget(self.add_gene_button)

        self.layout.addWidget(self.manage_gene_group)

    def init_instructions_button(self):
        self.instructions_button = QPushButton("Instructions")
        self.instructions_button.clicked.connect(self.show_instructions_popup)
        self.instructions_button.setToolTip("Click to view instructions on how to use the application.")
        self.layout.addWidget(self.instructions_button)

    def show_instructions_popup(self):
        instructions = (
            "## Instructions:\n\n"
            "1. **Load Excel File:**\n"
            "   - Click the 'Load Excel File' button to select and load your breeder data from an Excel file.\n\n"
            "2. **Manage Genes and Classes (Optional):**\n"
            "   - Add new gene-class pairs by entering the gene name and selecting its class from the dropdown, then clicking 'Add Gene-Class Pair'.\n"
            "   - To delete existing gene-class pairs, click the 'View Genes and Classes' button, select the desired pairs, and click 'Delete Selected'.\n\n"
            "3. **Enter Desired Genotype:**\n"
            "   - Input your desired genotype in the provided field. Supported formats include:\n"
            "     - **Delimited Format:** `gene:allele` (e.g., `cat:+/+ dog:f/+`)\n"
            "     - **Space-Separated Format:** `gene allele` (e.g., `cat +/+ dog f/+`)\n"
            "     - **Mixed Delimiters:** Combination of both (e.g., `cat:+/+ dog:f/+`)\n\n"
            "4. **Find Breeder Pairs:**\n"
            "   - Click the 'Find Breeder Pairs' button to analyze and generate suggestions based on the desired genotype.\n\n"
            "5. **Export Results (Optional):**\n"
            "   - Use the export buttons to save the direct and indirect breeder pair suggestions in CSV, Excel, or PDF formats.\n\n"
            "6. **Mark Breeder Pairs in Excel (Optional):\n"
            "   - Click the 'Mark Breeder Pairs in Excel' button to highlight suggested pairs in your Excel file and assign unique pair tags.\n\n"
            "7. **View Logs:**\n"
            "   - Monitor application logs in the 'Application Logs' section to track actions and debug if necessary.\n\n"
            "8. **View and Manage Existing Genes and Classes:**\n"
            "   - Click the 'View Genes and Classes' button to see a list of all existing gene names and their corresponding classes.\n"
            "   - To delete gene-class pairs, select the desired rows and click 'Delete Selected'.\n\n"
            "9. **View Mice Details:**\n"
            "    - Click the 'Show Mice Details' button to view mice within a specific age range and export their details.\n\n"
            "For further assistance, refer to the user manual or contact support."
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("Instructions")
        dialog.setModal(True)
        dialog.resize(600, 500)
        layout = QVBoxLayout()
        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setMarkdown(instructions)
        instructions_text.setFont(QFont("Arial", 12))
        layout.addWidget(instructions_text)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        close_button.setFixedWidth(100)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def init_file_loader(self):
        self.load_button = QPushButton("Load Excel File")
        self.load_button.clicked.connect(self.load_file)
        self.load_button.setToolTip("Click to load breeder data from an Excel file.")
        self.layout.addWidget(self.load_button)
        self.file_path_display = QLabel("No file loaded.")
        self.file_path_display.setWordWrap(True)
        self.layout.addWidget(self.file_path_display)

    def init_genotype_input(self):
        genotype_layout = QHBoxLayout()
        genotype_label = QLabel("Desired Genotype:")
        self.genotype_input = QLineEdit()
        self.genotype_input.setPlaceholderText("e.g., 'cat:+/+ dog:f/+' or 'cat +/+ dog f/+'")
        self.genotype_input.textChanged.connect(self.validate_genotype_input)
        genotype_layout.addWidget(genotype_label)
        genotype_layout.addWidget(self.genotype_input)
        self.layout.addLayout(genotype_layout)

    def validate_genotype_input(self):
        input_str = self.genotype_input.text().strip()
        parsed_genotype = self.data_processor.parse_genotype_input(input_str)
        self.clear_results()
        if parsed_genotype:
            self.genotype_input.setStyleSheet("border: 1px solid green;")
        else:
            self.genotype_input.setStyleSheet("border: 1px solid red;")

    def init_find_button(self):
        self.find_button = QPushButton("Find Breeder Pairs")
        self.find_button.clicked.connect(self.find_breeder_pairs_handler)
        self.find_button.setToolTip("Click to analyze and find suitable breeder pairs based on the desired genotype.")
        self.layout.addWidget(self.find_button)

    def init_reminder(self):
        self.reminder_text = QTextEdit()
        self.reminder_text.setReadOnly(True)
        self.layout.addWidget(self.reminder_text)

    def init_tables(self):
        direct_label = QLabel("Suggested Direct Breeder Pairs:")
        self.layout.addWidget(direct_label)
        direct_scroll = QScrollArea()
        direct_scroll.setWidgetResizable(True)
        self.direct_table = QTableWidget()
        self.direct_table.setSortingEnabled(True)
        direct_scroll.setWidget(self.direct_table)
        self.layout.addWidget(direct_scroll)
        indirect_label = QLabel("Suggested Indirect Breeder Pairs (Ranked by Similarity):")
        self.layout.addWidget(indirect_label)
        indirect_scroll = QScrollArea()
        indirect_scroll.setWidgetResizable(True)
        self.indirect_table = QTableWidget()
        self.indirect_table.setSortingEnabled(True)
        indirect_scroll.setWidget(self.indirect_table)
        self.layout.addWidget(indirect_scroll)

    def init_export_buttons(self):
        export_layout = QHBoxLayout()
        self.export_direct_button = QToolButton()
        self.export_direct_button.setText("Export Direct Pairs")
        self.export_direct_button.setToolTip("Export the direct breeder pairs in the selected format.")
        export_direct_menu = QMenu()
        export_direct_csv = QAction("Export to CSV", self)
        export_direct_csv.triggered.connect(lambda: Exporter.export_table_to_csv(self.direct_table, "Direct_Pairs"))
        export_direct_excel = QAction("Export to Excel", self)
        export_direct_excel.triggered.connect(lambda: Exporter.export_table_to_excel(self.direct_table, "Direct_Pairs"))
        export_direct_pdf = QAction("Export to PDF", self)
        export_direct_pdf.triggered.connect(lambda: Exporter.export_table_to_pdf(self.direct_table, "Direct_Pairs"))
        export_direct_menu.addAction(export_direct_csv)
        export_direct_menu.addAction(export_direct_excel)
        export_direct_menu.addAction(export_direct_pdf)
        self.export_direct_button.setMenu(export_direct_menu)
        self.export_direct_button.setPopupMode(QToolButton.InstantPopup)
        self.export_indirect_button = QToolButton()
        self.export_indirect_button.setText("Export Indirect Pairs")
        self.export_indirect_button.setToolTip("Export the indirect breeder pairs in the selected format.")
        export_indirect_menu = QMenu()
        export_indirect_csv = QAction("Export to CSV", self)
        export_indirect_csv.triggered.connect(
            lambda: Exporter.export_table_to_csv(self.indirect_table, "Indirect_Pairs"))
        export_indirect_excel = QAction("Export to Excel", self)
        export_indirect_excel.triggered.connect(
            lambda: Exporter.export_table_to_excel(self.indirect_table, "Indirect_Pairs"))
        export_indirect_pdf = QAction("Export to PDF", self)
        export_indirect_pdf.triggered.connect(
            lambda: Exporter.export_table_to_pdf(self.indirect_table, "Indirect_Pairs"))
        export_indirect_menu.addAction(export_indirect_csv)
        export_indirect_menu.addAction(export_indirect_excel)
        export_indirect_menu.addAction(export_indirect_pdf)
        self.export_indirect_button.setMenu(export_indirect_menu)
        self.export_indirect_button.setPopupMode(QToolButton.InstantPopup)
        export_layout.addWidget(self.export_direct_button)
        export_layout.addWidget(self.export_indirect_button)
        self.layout.addLayout(export_layout)

    def init_modify_button(self):
        self.modify_button = QPushButton("Mark Breeder Pairs in Excel")
        self.modify_button.clicked.connect(self.mark_breeder_pairs)
        self.modify_button.setToolTip(
            "Click to mark breeder pairs in the Excel file by highlighting them in yellow and adding unique pair tags.")
        self.layout.addWidget(self.modify_button)

    def init_progress_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

    def init_view_genes_button(self):
        self.view_genes_button = QPushButton("View Genes and Classes")
        self.view_genes_button.clicked.connect(self.view_genes_and_classes)
        self.view_genes_button.setToolTip("Click to view existing gene names and their classes.")
        self.layout.addWidget(self.view_genes_button)

    def init_show_mice_button(self):
        self.show_mice_button = QPushButton("Show Mice Details")
        self.show_mice_button.clicked.connect(self.show_mice_details)
        self.show_mice_button.setToolTip("Click to view mice details based on age criteria.")
        self.layout.addWidget(self.show_mice_button)

    def add_gene_class_pair(self):
        gene = self.gene_input.text().strip()
        gene_class = self.class_combo.currentText()
        try:
            self.gene_db.add_gene_class_pair(gene, gene_class)
            self.gene_input.clear()
            QMessageBox.information(self, "Success", f"Gene '{gene}' added to class '{gene_class}'.")
        except ValueError as ve:
            QMessageBox.warning(self, "Input Error", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{e}")

    def load_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Breeder Excel File", "",
                                                   "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_name:
            self.file_path_display.setText(f"Loaded File: {file_name}")
            self.excel_file_path = file_name
            self.file_loader_thread = FileLoaderThread(file_name, self.gene_db)
            self.file_loader_thread.progress.connect(self.update_progress)
            self.file_loader_thread.finished.connect(self.on_file_loaded)
            self.file_loader_thread.error.connect(self.on_load_error)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.file_loader_thread.start()
        else:
            QMessageBox.warning(self, "Warning", "No file selected.")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_file_loaded(self, breeders_df, excluded_breeders):
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.breeders = breeders_df
        if excluded_breeders:
            reminder = "Excluded Breeders:\n" + "\n".join(excluded_breeders)
            self.reminder_text.setText(reminder)
            logging.info(f"Excluded breeders: {excluded_breeders}")
        else:
            self.reminder_text.setText("No breeders were excluded based on row coloring.")
            logging.info("No breeders were excluded based on row coloring.")
        if not self.breeders.empty:
            older_breeders = self.breeders[self.breeders['age_months'] > self.max_age]
            if not older_breeders.empty:
                reminder = f"Mice older than {self.max_age} months:\n" + "\n".join(
                    older_breeders['breeder_name'].tolist())
                QMessageBox.information(self, "Reminder", reminder)
                logging.info(f"Mice older than {self.max_age} months: {older_breeders['breeder_name'].tolist()}")
        QMessageBox.information(self, "Success", "File loaded successfully.")
        logging.info("File loaded successfully.")

    def on_load_error(self, error_message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Load Error", f"An error occurred while loading the file:\n{error_message}")
        logging.error(f"Load Error: {error_message}")

    def find_breeder_pairs_handler(self):
        self.clear_results()
        genotype_input = self.genotype_input.text().strip()
        if not genotype_input:
            QMessageBox.warning(self, "Input Error", "Please enter the desired genotype.")
            return

        # Parse genotype and get missing genes
        desired_genotype, missing_genes = self.data_processor.parse_genotype_input(genotype_input)

        if missing_genes:
            missing_genes_str = ', '.join(missing_genes)
            QMessageBox.critical(
                self,
                "Missing Genes",
                f"The following gene(s) are not found in the gene database:\n{missing_genes_str}\n"
                "Please add them to the gene database before proceeding."
            )
            logging.error(f"Missing genes in gene database: {missing_genes}")
            return

        # Check if all desired genes exist in breeder data
        breeder_genes = set(self.breeders.columns.str.lower())
        desired_genes = set(desired_genotype.keys())
        missing_in_breeders = desired_genes - breeder_genes

        if missing_in_breeders:
            missing_breeders_str = ', '.join(missing_in_breeders)
            QMessageBox.critical(
                self,
                "Missing Genes in Breeder Data",
                f"The following gene(s) are not present in the breeder data columns:\n{missing_breeders_str}\n"
                "Please ensure all desired genes are included in the Excel sheets."
            )
            logging.error(f"Missing genes in breeder data: {missing_in_breeders}")
            return

        specified_genes = set(desired_genotype.keys())
        try:
            direct_pairs, indirect_pairs = self.data_processor.find_breeder_pairs(
                self.breeders, desired_genotype, specified_genes
            )
            if direct_pairs:
                self.display_direct_pairs(direct_pairs)
            else:
                QMessageBox.information(self, "No Direct Pairs", "No direct breeder pairs can produce the desired genotype.")
            if indirect_pairs:
                self.display_indirect_pairs(indirect_pairs)
            else:
                if not direct_pairs:
                    QMessageBox.information(self, "No Indirect Pairs",
                                            "No indirect breeder pairs found to improve the chances.")
        except Exception as e:
            logging.exception("An error occurred during breeder pair analysis.")
            QMessageBox.critical(self, "Error", f"An error occurred during breeder pair analysis:\n{e}")

    def display_direct_pairs(self, direct_pairs):
        self.direct_table.clear()
        headers = ["Pair ID", "Male ID", "Male Genotype", "Female ID", "Female Genotype", "Probability (%)",
                   "Same Strain", "Different Sheets"]
        self.direct_table.setColumnCount(len(headers))
        self.direct_table.setHorizontalHeaderLabels(headers)
        self.direct_table.setRowCount(len(direct_pairs))

        for row_idx, pair in enumerate(direct_pairs):
            self.direct_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            self.direct_table.setItem(row_idx, 1, QTableWidgetItem(pair['Male']))

            # Collect genes present in either male or female breeder columns
            male_genes = set(pair['Male Data'].dropna().index) - set(
                ['breeder_name', 'gender', 'dob', 'age_months', 'age', 'notes', 'sheet', 'strain'])
            female_genes = set(pair['Female Data'].dropna().index) - set(
                ['breeder_name', 'gender', 'dob', 'age_months', 'age', 'notes', 'sheet', 'strain'])
            all_genes = sorted(male_genes.union(female_genes))

            # Male Genotype
            male_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Male'].get(gene)
                if allele is None or pd.isna(allele):
                    # Assign default allele based on gene class
                    gene_class = self.gene_db.transgene_to_category.get(gene)
                    if gene_class == 'Flox':
                        allele = '+/+'
                    elif gene_class in ['Cre', 'Reporter']:
                        allele = '-/-'
                    else:
                        allele = '+/+'
                male_genotype += f"{gene} {allele} "
            self.direct_table.setItem(row_idx, 2, QTableWidgetItem(male_genotype.strip()))

            self.direct_table.setItem(row_idx, 3, QTableWidgetItem(pair['Female']))

            # Female Genotype
            female_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Female'].get(gene)
                if allele is None or pd.isna(allele):
                    # Assign default allele based on gene class
                    gene_class = self.gene_db.transgene_to_category.get(gene)
                    if gene_class == 'Flox':
                        allele = '+/+'
                    elif gene_class in ['Cre', 'Reporter']:
                        allele = '-/-'
                    else:
                        allele = '+/+'
                female_genotype += f"{gene} {allele} "
            self.direct_table.setItem(row_idx, 4, QTableWidgetItem(female_genotype.strip()))

            # Probability (%)
            self.direct_table.setItem(row_idx, 5, QTableWidgetItem(str(pair['Probability (%)'])))
            # Same Strain
            self.direct_table.setItem(row_idx, 6, QTableWidgetItem(pair['Same Strain']))
            # Different Sheets
            different_sheets = "Yes" if pair['Male Sheet'] != pair['Female Sheet'] else "No"
            self.direct_table.setItem(row_idx, 7, QTableWidgetItem(different_sheets))

        self.direct_table.resizeColumnsToContents()
        self.direct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def display_indirect_pairs(self, indirect_pairs):
        self.indirect_table.clear()
        headers = ["Pair ID", "Male ID", "Male Genotype", "Female ID", "Female Genotype", "Similarity Score (%)",
                   "Same Strain", "Different Sheets"]
        self.indirect_table.setColumnCount(len(headers))
        self.indirect_table.setHorizontalHeaderLabels(headers)
        self.indirect_table.setRowCount(len(indirect_pairs))

        for row_idx, pair in enumerate(indirect_pairs):
            self.indirect_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            self.indirect_table.setItem(row_idx, 1, QTableWidgetItem(pair['Male']))

            # Collect genes present in either male or female breeder columns
            male_genes = set(pair['Male Data'].dropna().index) - set(
                ['breeder_name', 'gender', 'dob', 'age_months', 'age', 'notes', 'sheet', 'strain'])
            female_genes = set(pair['Female Data'].dropna().index) - set(
                ['breeder_name', 'gender', 'dob', 'age_months', 'age', 'notes', 'sheet', 'strain'])
            all_genes = sorted(male_genes.union(female_genes))

            # Male Genotype
            male_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Male'].get(gene)
                if allele is None or pd.isna(allele):
                    # Assign default allele based on gene class
                    gene_class = self.gene_db.transgene_to_category.get(gene)
                    if gene_class == 'Flox':
                        allele = '+/+'
                    elif gene_class in ['Cre', 'Reporter']:
                        allele = '-/-'
                    else:
                        allele = '+/+'
                male_genotype += f"{gene} {allele} "
            self.indirect_table.setItem(row_idx, 2, QTableWidgetItem(male_genotype.strip()))

            self.indirect_table.setItem(row_idx, 3, QTableWidgetItem(pair['Female']))

            # Female Genotype
            female_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Female'].get(gene)
                if allele is None or pd.isna(allele):
                    # Assign default allele based on gene class
                    gene_class = self.gene_db.transgene_to_category.get(gene)
                    if gene_class == 'Flox':
                        allele = '+/+'
                    elif gene_class in ['Cre', 'Reporter']:
                        allele = '-/-'
                    else:
                        allele = '+/+'
                female_genotype += f"{gene} {allele} "
            self.indirect_table.setItem(row_idx, 4, QTableWidgetItem(female_genotype.strip()))

            # Similarity Score (%)
            self.indirect_table.setItem(row_idx, 5, QTableWidgetItem(str(pair['Similarity Score (%)'])))
            # Same Strain
            self.indirect_table.setItem(row_idx, 6, QTableWidgetItem(pair['Same Strain']))
            # Different Sheets
            different_sheets = "Yes" if pair['Male Sheet'] != pair['Female Sheet'] else "No"
            self.indirect_table.setItem(row_idx, 7, QTableWidgetItem(different_sheets))

        self.indirect_table.resizeColumnsToContents()
        self.indirect_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def mark_breeder_pairs(self):
        if not self.excel_file_path:
            QMessageBox.warning(self, "No Excel File", "Please load an Excel file first.")
            return
        breeder_names = set()
        for table in [self.direct_table, self.indirect_table]:
            for row in range(table.rowCount()):
                male = table.item(row, 1).text()
                female = table.item(row, 3).text()
                breeder_names.add(male)
                breeder_names.add(female)
        if not breeder_names:
            QMessageBox.information(self, "No Breeder Pairs", "No breeder pairs found to mark.")
            return
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            wb = load_workbook(filename=self.excel_file_path)
            self.progress_bar.setValue(30)
            yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                headers = [cell.value for cell in ws[1]]
                header_map = {header.strip().lower().replace(' ', '_').replace('(', '').replace(')', ''): idx for
                              idx, header in enumerate(headers, start=1)}
                if 'pair_tag' not in header_map:
                    ws.cell(row=1, column=len(headers) + 1, value='pair_tag')
                    header_map['pair_tag'] = len(headers) + 1
                for row in ws.iter_rows(min_row=2):
                    breeder_name_cell = row[header_map.get('breeder_name', 1) - 1]
                    breeder_name = breeder_name_cell.value
                    if breeder_name in breeder_names:
                        for cell in row:
                            cell.fill = yellow_fill
                        pair_tag_cell = row[header_map['pair_tag'] - 1]
                        if not pair_tag_cell.value:
                            pair_tag = self.generate_unique_tag()
                            pair_tag_cell.value = pair_tag
                self.progress_bar.setValue(70)
            wb.save(self.excel_file_path)
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Success", "Breeder pairs have been marked in the Excel file.")
            logging.info("Breeder pairs have been marked in the Excel file.")
        except Exception as e:
            logging.exception("An error occurred while marking breeder pairs.")
            QMessageBox.critical(self, "Error", f"An error occurred while marking breeder pairs:\n{e}")
            self.progress_bar.setVisible(False)

    def generate_unique_tag(self):
        word = ''.join(random.choices(string.ascii_uppercase, k=5))
        number = ''.join(random.choices(string.digits, k=5))
        return f"{word}{number}"

    def view_genes_and_classes(self):
        gene_viewer = GeneViewerDialog(self.gene_db, self)
        gene_viewer.exec_()

    def show_mice_details(self):
        if self.breeders.empty:
            QMessageBox.information(self, "No Data", "Please load an Excel file first.")
            return
        dialog = MiceDetailsDialog(self.breeders, self.gene_db, self)
        dialog.exec_()

    def display_direct_pairs(self, direct_pairs):
        self.direct_table.clear()
        headers = ["Pair ID", "Male ID", "Male Genotype", "Female ID", "Female Genotype", "Probability (%)",
                   "Same Strain", "Different Sheets"]
        self.direct_table.setColumnCount(len(headers))
        self.direct_table.setHorizontalHeaderLabels(headers)
        self.direct_table.setRowCount(len(direct_pairs))

        # Collect all genes present in any breeder
        all_genes = set()
        for pair in direct_pairs:
            all_genes.update(pair['Breeder Genotypes']['Male'].keys())
            all_genes.update(pair['Breeder Genotypes']['Female'].keys())
        # Optionally, sort the genes for consistent ordering
        all_genes = sorted(all_genes)

        for row_idx, pair in enumerate(direct_pairs):
            self.direct_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            self.direct_table.setItem(row_idx, 1, QTableWidgetItem(pair['Male']))

            # Male Genotype
            male_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Male'].get(gene)
                if allele is None or pd.isna(allele):
                    allele = self.gene_db.wildtype_genotype.get(gene, '+/+')
                male_genotype += f"{gene} {allele} "
            self.direct_table.setItem(row_idx, 2, QTableWidgetItem(male_genotype.strip()))

            self.direct_table.setItem(row_idx, 3, QTableWidgetItem(pair['Female']))

            # Female Genotype
            female_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Female'].get(gene)
                if allele is None or pd.isna(allele):
                    allele = self.gene_db.wildtype_genotype.get(gene, '+/+')
                female_genotype += f"{gene} {allele} "
            self.direct_table.setItem(row_idx, 4, QTableWidgetItem(female_genotype.strip()))

            # Probability (%)
            self.direct_table.setItem(row_idx, 5, QTableWidgetItem(str(pair['Probability (%)'])))
            # Same Strain
            self.direct_table.setItem(row_idx, 6, QTableWidgetItem(pair['Same Strain']))
            # Different Sheets
            different_sheets = "Yes" if pair['Male Sheet'] != pair['Female Sheet'] else "No"
            self.direct_table.setItem(row_idx, 7, QTableWidgetItem(different_sheets))

        self.direct_table.resizeColumnsToContents()
        self.direct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def display_indirect_pairs(self, indirect_pairs):
        self.indirect_table.clear()
        headers = ["Pair ID", "Male ID", "Male Genotype", "Female ID", "Female Genotype", "Similarity Score (%)",
                   "Same Strain", "Different Sheets"]
        self.indirect_table.setColumnCount(len(headers))
        self.indirect_table.setHorizontalHeaderLabels(headers)
        self.indirect_table.setRowCount(len(indirect_pairs))

        # Collect all genes present in any breeder
        all_genes = set()
        for pair in indirect_pairs:
            all_genes.update(pair['Breeder Genotypes']['Male'].keys())
            all_genes.update(pair['Breeder Genotypes']['Female'].keys())
        # Optionally, sort the genes for consistent ordering
        all_genes = sorted(all_genes)

        for row_idx, pair in enumerate(indirect_pairs):
            self.indirect_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            self.indirect_table.setItem(row_idx, 1, QTableWidgetItem(pair['Male']))

            # Male Genotype
            male_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Male'].get(gene)
                if allele is None or pd.isna(allele):
                    allele = self.gene_db.wildtype_genotype.get(gene, '+/+')
                male_genotype += f"{gene} {allele} "
            self.indirect_table.setItem(row_idx, 2, QTableWidgetItem(male_genotype.strip()))

            self.indirect_table.setItem(row_idx, 3, QTableWidgetItem(pair['Female']))

            # Female Genotype
            female_genotype = ""
            for gene in all_genes:
                allele = pair['Breeder Genotypes']['Female'].get(gene)
                if allele is None or pd.isna(allele):
                    allele = self.gene_db.wildtype_genotype.get(gene, '+/+')
                female_genotype += f"{gene} {allele} "
            self.indirect_table.setItem(row_idx, 4, QTableWidgetItem(female_genotype.strip()))

            # Similarity Score (%)
            self.indirect_table.setItem(row_idx, 5, QTableWidgetItem(str(pair['Similarity Score (%)'])))
            # Same Strain
            self.indirect_table.setItem(row_idx, 6, QTableWidgetItem(pair['Same Strain']))
            # Different Sheets
            different_sheets = "Yes" if pair['Male Sheet'] != pair['Female Sheet'] else "No"
            self.indirect_table.setItem(row_idx, 7, QTableWidgetItem(different_sheets))

        self.indirect_table.resizeColumnsToContents()
        self.indirect_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


def main():
    try:
        app = QApplication(sys.argv)
        window = BreederPairSelector()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.exception("An unexpected error occurred:")
        QMessageBox.critical(None, "Fatal Error", f"An unexpected error occurred:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
