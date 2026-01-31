import sys
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMenu, QFileDialog,
                             QTableWidget, QTableWidgetItem, QDialog, QLabel, QSpinBox, QCheckBox, QDoubleSpinBox,
                             QGroupBox, QFormLayout, QScrollArea, QComboBox)
from PyQt6.QtCore import Qt
import pandas as pd
import numpy as np


current_file_path = None
current_df = None

def parse_pressure(value):
    """Parsuje ciśnienie np. '100/40' -> (100, 40), None jeśli brak."""
    if pd.isna(value):
        return None, None
    match = re.match(r'(\d+)/(\d+)', str(value))
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)

def import_csv():
    """
    Wybór pliku CSV i załadowanie (np. pandas).
    """
    global current_file_path, current_df
    file_path, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Wybierz plik CSV",
        directory="/Users/ola/Documents/GitHub/projekt_studia_analityk",  # Aktualny katalog
        filter="CSV files (*.csv);;All files (*)"
    )

    if file_path:  # Jeśli użytkownik wybrał plik
        current_file_path = file_path
        current_df = pd.read_csv(file_path)
        print(f"Wybrano plik CSV: {current_df.shape}")  # Tymczasowy print
    else:
        print("Anulowano wybór pliku")

def import_sql():
    """
    Pusta funkcja do importu z bazy SQL.
    Zaimplementuj np. sqlite3.connect() i pd.read_sql().
    """
    pass  # Dodaj tu kod importu SQL


def zastosuj_filtry(df, widgets):  # NOWOŚĆ: parametr widgets=self
    filtered_df = df.copy()

    # Filtr wieku
    if widgets.chk_wiek.isChecked():
        min_wiek = widgets.spin_wiek_min.value()
        max_wiek = widgets.spin_wiek_max.value()
        filtered_df = filtered_df[(filtered_df.get('Wiek', pd.Series([0])) >= min_wiek) &
                                  (filtered_df.get('Wiek', pd.Series([0])) <= max_wiek)]

    # Filtr płeć
    if widgets.chk_plc.isChecked() and widgets.combo_plc.currentText():
        filtered_df = filtered_df[filtered_df.get('Płeć', pd.Series([""])) == widgets.combo_plc.currentText()]

    # Filtr ciśnienie + TWOJA parse_pressure
    if widgets.chk_cisn.isChecked():
        # Użyj parse_pressure na kolumnie ciśnienia jeśli masz 'Ciśnienie' jako string '100/60'
        if 'Ciśnienie' in df.columns:
            df['skur'], df['rozk'] = zip(*df['Ciśnienie'].apply(parse_pressure))
            filtered_df = filtered_df[
                (filtered_df['skur'].fillna(0) >= widgets.spin_skur_min.value()) &
                (filtered_df['skur'].fillna(999) <= widgets.spin_skur_max.value()) &
                (filtered_df['rozk'].fillna(0) >= widgets.spin_rozk_min.value()) &
                (filtered_df['rozk'].fillna(999) <= widgets.spin_rozk_max.value())
                ]
        else:
            # Zakładając osobne kolumny
            filtered_df = filtered_df[
                (filtered_df.get('Ciśnienie skurczowe', pd.Series([0])) >= widgets.spin_skur_min.value()) &
                (filtered_df.get('Ciśnienie skurczowe', pd.Series([0])) <= widgets.spin_skur_max.value()) &
                (filtered_df.get('Ciśnienie rozkurczowe', pd.Series([0])) >= widgets.spin_rozk_min.value()) &
                (filtered_df.get('Ciśnienie rozkurczowe', pd.Series([0])) <= widgets.spin_rozk_max.value())
                ]
    return filtered_df


def podglad_danych():
    if current_df is None:
        print("Najpierw wczytaj plik")
        return

    dialog = QDialog()
    dialog.setWindowTitle("Podgląd danych")
    dialog.resize(900, 600)

    layout = QVBoxLayout(dialog)

    # Zastosuj filtry jeśli włączone
    display_df = zastosuj_filtry(current_df)

    info_label = QLabel(f"Plik: {current_file_path} | Wiersze: {len(display_df)}")
    layout.addWidget(info_label)

    table = QTableWidget()
    nrows = min(50, len(display_df))
    table.setRowCount(nrows)
    table.setColumnCount(len(display_df.columns))
    table.setHorizontalHeaderLabels(display_df.columns.tolist())

    for row in range(nrows):
        for col in range(len(display_df.columns)):
            value = str(display_df.iloc[row, col])
            item = QTableWidgetItem(value)
            table.setItem(row, col, item)

    table.resizeColumnsToContents()
    table.setAlternatingRowColors(True)
    layout.addWidget(table)
    dialog.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wczytaj dane - Filtry i podgląd")
        self.setMinimumSize(1400, 800)  # NOWOŚĆ: Duże okno

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # NOWOŚĆ: Główny HLayout lewo-prawo

        # NOWOŚĆ: LEWA KOLUMNA - PRZYCISKI pionowo
        left_layout = QVBoxLayout()
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        menu = QMenu(self)
        menu.addAction("Import z CSV", import_csv)
        menu.addAction("Import z bazy SQL", import_sql)
        self.btn_wczytaj.setMenu(menu)
        left_layout.addWidget(self.btn_wczytaj)

        self.btn_podglad = QPushButton("Podgląd danych")  # TWOJ
        self.btn_podglad.clicked.connect(self.update_table)  # NOWOŚĆ: connect do self.update_table
        left_layout.addWidget(self.btn_podglad)
        left_layout.addStretch()
        main_layout.addLayout(left_layout, stretch=1)  # NOWOŚĆ: Lewy panel wąski

        # NOWOŚĆ: PRAWY PANEL - FILTROWANIE + TABELA
        right_layout = QVBoxLayout()

        # NOWOŚĆ: Filtrowanie w ScrollArea (widoczne!)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)

        # NOWOŚĆ: Widgety filtrów jako self.atrybuty
        group_filter = QGroupBox("Dynamiczne filtry")
        form_layout = QFormLayout(group_filter)

        # NOWOŚĆ: Filtr Wiek
        h_wiek = QHBoxLayout()
        self.chk_wiek = QCheckBox("Filtr wieku")
        self.spin_wiek_min = QSpinBox();
        self.spin_wiek_min.setRange(0, 150);
        self.spin_wiek_min.setValue(18)
        self.spin_wiek_max = QSpinBox();
        self.spin_wiek_max.setRange(0, 150);
        self.spin_wiek_max.setValue(100)
        h_wiek.addWidget(self.chk_wiek)
        h_wiek.addWidget(QLabel("od:"))
        h_wiek.addWidget(self.spin_wiek_min)
        h_wiek.addWidget(QLabel("do:"))
        h_wiek.addWidget(self.spin_wiek_max)
        form_layout.addRow(h_wiek)

        # NOWOŚĆ: Filtr Płeć
        h_plc = QHBoxLayout()
        self.chk_plc = QCheckBox("Filtr płci")
        self.combo_plc = QComboBox()
        self.combo_plc.addItems(["", "Kobieta", "Mężczyzna"])
        h_plc.addWidget(self.chk_plc)
        h_plc.addWidget(self.combo_plc)
        form_layout.addRow(h_plc)

        # NOWOŚĆ: Filtr Ciśnienie
        h_cisn = QHBoxLayout()
        self.chk_cisn = QCheckBox("Filtr ciśnienia")
        self.spin_skur_min = QSpinBox();
        self.spin_skur_min.setRange(50, 250);
        self.spin_skur_min.setValue(90)
        self.spin_skur_max = QSpinBox();
        self.spin_skur_max.setRange(50, 250);
        self.spin_skur_max.setValue(180)
        self.spin_rozk_min = QSpinBox();
        self.spin_rozk_min.setRange(30, 150);
        self.spin_rozk_min.setValue(60)
        self.spin_rozk_max = QSpinBox();
        self.spin_rozk_max.setRange(30, 150);
        self.spin_rozk_max.setValue(100)
        h_cisn.addWidget(self.chk_cisn)
        h_cisn.addWidget(QLabel("Skurczowe od/do:"))
        h_cisn.addWidget(self.spin_skur_min);
        h_cisn.addWidget(self.spin_skur_max)
        h_cisn.addWidget(QLabel("Rozkurczowe od/do:"))
        h_cisn.addWidget(self.spin_rozk_min);
        h_cisn.addWidget(self.spin_rozk_max)
        form_layout.addRow(h_cisn)

        filter_layout.addWidget(group_filter)
        scroll.setWidget(filter_widget)
        right_layout.addWidget(QLabel("FILTROWANIE (przewiń ↓):"))  # NOWOŚĆ: Wskazówka
        right_layout.addWidget(scroll)

        # NOWOŚĆ: Tabela w głównym oknie (zamiast dialog)
        self.table = QTableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        right_layout.addWidget(self.table)

        main_layout.addLayout(right_layout, stretch=4)

    # NOWOŚĆ: Metoda aktualizująca tabelę w głównym oknie
    def update_table(self):
        global current_df
        if current_df is None:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Brak danych"])
            self.table.setItem(0, 0, QTableWidgetItem("Najpierw wczytaj CSV"))
            return

        # NOWOŚĆ: Użyj self.widgety w filtrach
        display_df = zastosuj_filtry(current_df, self)

        nrows = min(50, len(display_df))  # TWOJA logika
        self.table.setRowCount(nrows)
        self.table.setColumnCount(len(display_df.columns))
        self.table.setHorizontalHeaderLabels(display_df.columns.tolist())

        for row in range(nrows):
            for col in range(len(display_df.columns)):
                item = QTableWidgetItem(str(display_df.iloc[row, col]))
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()
        self.table.setAlternatingRowColors(True)
        print(f"📊 Pokazano {nrows}/{len(display_df)} wierszy")

    # Uruchomienie aplikacji
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
