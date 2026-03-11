import sys
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QMenu, QScrollArea, QTableWidget, QTableWidgetItem,
    QLabel, QCheckBox, QComboBox, QSpinBox, QStackedWidget, QFileDialog,
    QDoubleSpinBox, QLineEdit, QPlainTextEdit, QSplitter, QDialog
)
from PyQt6.QtCore import  Qt
from PyQt6.QtGui import QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages #esporty pdf
from datetime import datetime
import pandas as pd

current_file_path = None
current_df = None

def parse_pressure(value):
    """Parsuje ciśnienie np. '100/40' -> (100, 40), None jeśli brak."""
    #nie uzywam tej funckji nigdzie, ale zostawiam ja. nie uzywam bo zaczelam robic inne dane.
    if pd.isna(value):
        return None, None
    match = re.match(r'(\d+)/(\d+)', str(value))
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)

def import_csv():
    global current_file_path, current_df

    file_path, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Wybierz plik CSV",
        directory="/Users/ola/Documents/GitHub/projekt_studia_analityk",
        filter="CSV files (*.csv);;All files (*)"
    )
    if not file_path:
        print("Anulowano wybór pliku")
        return

    current_file_path = file_path
    current_df = pd.read_csv(file_path)

    print(f"Wybrano plik CSV: {current_df.shape}")

    # Filtry odświeżymy z poziomu MainWindow

def import_sql():
    """
    Pusta funkcja do importu z bazy SQL.
    Zaimplementuj np. sqlite3.connect() i pd.read_sql().
    """
    pass  # Tu kiedyś będzie kod importu

def zastosuj_filtry(df, widgets):
    filtered_df = df.copy()

    # Jeśli filtry jeszcze nie wygenerowane
    if not hasattr(widgets, "filter_widgets") or not widgets.filter_widgets:
        return filtered_df

    for col, controls in widgets.filter_widgets.items():
        if not controls["chk"].isChecked():
            continue

        # Liczbowe: min/max
        if "min" in controls and "max" in controls:
            # bierz dane z filtered_df (po wcześniejszych filtrach) i konwertuj do liczb
            col_data = pd.to_numeric(filtered_df[col], errors="coerce")

            vmin = controls["min"].value()
            vmax = controls["max"].value()

            mask = col_data.between(vmin, vmax, inclusive="both")
            filtered_df = filtered_df[mask]

            print(f"Filtr '{col}': {vmin} - {vmax}")

        # Tekstowe: == wybrana wartość
        elif "combo" in controls:
            val = controls["combo"].currentText()
            if val == "":
                continue

            # porównanie jako string - stabilizacja
            mask = filtered_df[col].astype(str) == str(val)
            filtered_df = filtered_df[mask]

            print(f"Filtr '{col}': = '{val}'")

    # Filtr NORMY
    if widgets.chk_norma.isChecked():
        min_norm = widgets.spin_norma_min.value()
        max_norm = widgets.spin_norma_max.value()

        cols_norm = []
        # Bierz obie kolumny jeśli wybrane (nawet tę samą)
        if widgets.cmb_norma_kol1.currentText():
            cols_norm.append(widgets.cmb_norma_kol1.currentText())
        if widgets.cmb_norma_kol2.currentText():
            cols_norm.append(widgets.cmb_norma_kol2.currentText())

        if cols_norm:
            # "w normie": WSZYSTKIE wybrane kolumny muszą być w zakresie
            mask_norm = pd.Series(True, index=filtered_df.index)
            for col in cols_norm:
                col_data = pd.to_numeric(filtered_df[col], errors='coerce')
                mask_norm &= col_data.between(min_norm, max_norm, inclusive="both")

            # "poniżej": WSZYSTKIE wybrane kolumny muszą być PONIŻEJ
            mask_below = pd.Series(True, index=filtered_df.index)
            for col in cols_norm:
                col_data = pd.to_numeric(filtered_df[col], errors='coerce')
                mask_below &= (col_data < min_norm)

            # "powyżej": WSZYSTKIE wybrane kolumny muszą być POWYŻEJ
            mask_above = pd.Series(True, index=filtered_df.index)
            for col in cols_norm:
                col_data = pd.to_numeric(filtered_df[col], errors='coerce')
                mask_above &= (col_data > max_norm)

            # Zastosuj wybrane kategorie normy
            final_mask = pd.Series(False, index=filtered_df.index)
            if widgets.chk_norma_ok.isChecked():
                final_mask |= mask_norm
            if widgets.chk_norma_nizej.isChecked():
                final_mask |= mask_below
            if widgets.chk_norma_wyzej.isChecked():
                final_mask |= mask_above

            filtered_df = filtered_df[final_mask]
            print(f"NORMA [{min_norm}-{max_norm}] na {cols_norm}: {len(final_mask[final_mask])} wierszy")

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
        self.statusBar().deleteLater()

        # LOG WIDGET
        self.log_widget = QPlainTextEdit(self)
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(120)
        self.log_widget.setStyleSheet("font-family: 'Courier New', Consolas, monospace; font-size: 10pt;")
        self.log_widget.appendPlainText("[START] Aplikacja uruchomiona")

        self.setWindowTitle("VetStats")
        self.setMinimumSize(1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Główny VBOX z splitterem
        main_layout = QVBoxLayout(central_widget)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEWA KOLUMNA 350px
        left_widget = QWidget()
        left_widget.setFixedWidth(350)
        left_layout = QVBoxLayout(left_widget)

        # Przyciski górne
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        menu = QMenu(self)

        action_csv = menu.addAction("Import z CSV")
        action_csv.triggered.connect(self.import_csv_and_refresh)

        # teraz specjalnie odwołanie to tej smiesznej funkcji :)
        action_sql = menu.addAction("Import z bazy SQL")
        action_sql.triggered.connect(self.show_sql_unavailable_dialog)

        self.btn_wczytaj.setMenu(menu)
        self.btn_wczytaj.clicked.connect(lambda: self.log("Kliknięto Wczytaj – wybierz menu"))
        left_layout.addWidget(self.btn_wczytaj)

        self.btn_podglad = QPushButton("Podgląd danych")
        self.btn_podglad.clicked.connect(lambda: [self.log("Odświeżam podgląd tabeli"), self.update_table()])

        left_layout.addWidget(self.btn_podglad)

        # ScrollArea na dynamiczne filtry
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        filter_widget = QWidget()
        self.scroll_layout = QVBoxLayout(filter_widget)
        scroll.setWidget(filter_widget)
        left_layout.addWidget(scroll)

        # Miejsce na kontrolki filtrów
        self.filter_widgets = {}

        # Przycisk Filtruj i wyświetl
        self.btn_filtruj = QPushButton("Filtruj i wyświetl")
        self.btn_filtruj.clicked.connect(lambda: [self.log("Zastosowano filtry"), self.update_table()])
        self.btn_filtruj.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;"
        )
        left_layout.addWidget(self.btn_filtruj)

        # Widget NORMY
        self.norma_widget = QWidget()
        norma_layout = QVBoxLayout(self.norma_widget)  # ZMIANA: QVBoxLayout zamiast QHBoxLayout - inny układ widgetów vertical/horizontal
        norma_layout.setContentsMargins(5, 5, 5, 5)
        norma_layout.setSpacing(4)

        # WIERSZ 1: Checkbox NORMA
        row1 = QHBoxLayout()
        self.chk_norma = QCheckBox("NORMA")
        self.chk_norma.stateChanged.connect(self.toggle_norma_filter)
        row1.addWidget(self.chk_norma)
        row1.addStretch(1)
        norma_layout.addLayout(row1)

        # WIERSZ 2: Wybór kolumn
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QLabel("Kolumna 1:"))
        self.cmb_norma_kol1 = QComboBox()
        self.cmb_norma_kol1.setMaximumWidth(120)
        row2.addWidget(self.cmb_norma_kol1)

        row2.addWidget(QLabel("Kolumna 2:"))
        self.cmb_norma_kol2 = QComboBox()
        self.cmb_norma_kol2.setMaximumWidth(120)
        row2.addWidget(self.cmb_norma_kol2)
        row2.addStretch(1)
        norma_layout.addLayout(row2)

        # WIERSZ 3: Zakres normy
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.addWidget(QLabel("Zakres:"))
        self.spin_norma_min = QDoubleSpinBox()
        self.spin_norma_min.setDecimals(2)
        self.spin_norma_min.setMaximumWidth(80)
        row3.addWidget(self.spin_norma_min)

        row3.addWidget(QLabel("do"))
        self.spin_norma_max = QDoubleSpinBox()
        self.spin_norma_max.setDecimals(2)
        self.spin_norma_max.setMaximumWidth(80)
        row3.addWidget(self.spin_norma_max)

        row3.addStretch(1)
        norma_layout.addLayout(row3)

        left_layout.addWidget(self.norma_widget)

        # Widget WIZUALIZACJA
        self.wizualizacja_widget = QWidget()
        wiz_layout = QVBoxLayout(self.wizualizacja_widget)
        wiz_layout.setContentsMargins(5, 5, 5, 5)
        wiz_layout.setSpacing(4)

        # WIERSZ 1: etykieta + Narysuj
        wiz_row1 = QHBoxLayout()

        lbl_wiz = QLabel("WIZUALIZACJA")
        lbl_wiz.setStyleSheet("font-weight: bold;")
        wiz_row1.addWidget(lbl_wiz)

        wiz_row1.addStretch(1)

        self.btn_wizualizuj = QPushButton("Narysuj")
        self.btn_wizualizuj.clicked.connect(
            lambda: [self.log("Uruchamiam wizualizację"), self.run_visualization()]
        )
        wiz_row1.addWidget(self.btn_wizualizuj)

        wiz_layout.addLayout(wiz_row1)

        # WIERSZ 2: Typ wykresu
        wiz_row2 = QHBoxLayout()
        wiz_row2.addWidget(QLabel("Typ:"))
        self.cmb_wiz_type = QComboBox()
        self.cmb_wiz_type.clear()
        self.cmb_wiz_type.addItems(["Histogram", "Słupkowy"])

        wiz_row2.addWidget(self.cmb_wiz_type)
        wiz_row2.addStretch(1)
        wiz_layout.addLayout(wiz_row2)

        # WIERSZ 3: Kolumny X/Y
        wiz_row3 = QHBoxLayout()
        wiz_row3.addWidget(QLabel("X:"))
        self.cmb_wiz_x = QComboBox()
        wiz_row3.addWidget(self.cmb_wiz_x)
        wiz_row3.addWidget(QLabel("Y:"))
        self.cmb_wiz_y = QComboBox()
        wiz_row3.addWidget(self.cmb_wiz_y)
        wiz_row3.addStretch(1)
        wiz_layout.addLayout(wiz_row3)

        # WIERSZ 4: Grupowanie
        wiz_row4 = QHBoxLayout()
        wiz_row4.addWidget(QLabel("Grupuj po:"))
        self.cmb_wiz_group = QComboBox()
        wiz_row4.addWidget(self.cmb_wiz_group)
        wiz_row4.addStretch(1)
        wiz_layout.addLayout(wiz_row4)

        # WIERSZ: Porównanie oczu
        eyes_row = QHBoxLayout()
        eyes_row.addWidget(QLabel("Lewe oko:"))
        self.cmb_eye_left = QComboBox()
        eyes_row.addWidget(self.cmb_eye_left)
        eyes_row.addWidget(QLabel("Prawe oko:"))
        self.cmb_eye_right = QComboBox()
        eyes_row.addWidget(self.cmb_eye_right)
        eyes_row.addStretch(1)
        wiz_layout.addLayout(eyes_row)
        self.chk_compare_eyes = QCheckBox("Porównaj lewe/prawe oko")
        self.chk_compare_eyes.setChecked(False)
        # pokaż checkbox pod wyborem oczu
        wiz_layout.addWidget(self.chk_compare_eyes)

        # opcjonalnie: domyślnie zablokuj comboboksy oczu, dopóki checkbox OFF
        self.cmb_eye_left.setEnabled(False)
        self.cmb_eye_right.setEnabled(False)
        self.chk_compare_eyes.toggled.connect(self.cmb_eye_left.setEnabled)
        self.chk_compare_eyes.toggled.connect(self.cmb_eye_right.setEnabled)

        # opcje do wykresów
        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Agregacja:"))
        self.cmb_wiz_agg = QComboBox()
        self.cmb_wiz_agg.addItems(["mean", "median", "count", "sum"])
        opt_row.addWidget(self.cmb_wiz_agg)

        opt_row.addWidget(QLabel("Top N:"))
        self.spin_wiz_topn = QSpinBox()
        self.spin_wiz_topn.setRange(1, 200)
        self.spin_wiz_topn.setValue(30)
        self.spin_wiz_topn.setMaximumWidth(70)
        opt_row.addWidget(self.spin_wiz_topn)

        opt_row.addWidget(QLabel("Sortuj:"))
        self.cmb_wiz_sort = QComboBox()
        self.cmb_wiz_sort.addItems(["brak", "rosnąco", "malejąco"])
        opt_row.addWidget(self.cmb_wiz_sort)

        opt_row.addStretch(1)
        wiz_layout.addLayout(opt_row)

        # WIERSZ 4.5: Norma na wykresie
        wiz_row_norma = QHBoxLayout()
        self.chk_wiz_norma = QCheckBox("Pokaż normę na wykresie")
        wiz_row_norma.addWidget(self.chk_wiz_norma)
        wiz_row_norma.addStretch(1)
        wiz_layout.addLayout(wiz_row_norma)

        # WIERSZ 5: Tytuł
        wiz_row5 = QHBoxLayout()
        wiz_row5.addWidget(QLabel("Tytuł:"))
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Wpisz tytuł...")
        wiz_row5.addWidget(self.txt_title)
        wiz_layout.addLayout(wiz_row5)

        # WIERSZ 6: Etykiety X/Y
        wiz_row6 = QHBoxLayout()
        wiz_row6.addWidget(QLabel("X label:"))
        self.txt_xlabel = QLineEdit()
        self.txt_xlabel.setPlaceholderText("Nazwa osi X...")
        wiz_row6.addWidget(self.txt_xlabel)
        wiz_row6.addWidget(QLabel("Y label:"))
        self.txt_ylabel = QLineEdit()
        self.txt_ylabel.setPlaceholderText("Nazwa osi Y...")
        wiz_row6.addWidget(self.txt_ylabel)
        wiz_layout.addLayout(wiz_row6)

        left_layout.addWidget(self.wizualizacja_widget)

        # ScrollArea na filtry - filtr NORMY
        self.norma_filter_widget = QWidget()
        self.norma_filter_layout = QHBoxLayout(self.norma_filter_widget)
        self.chk_norma_ok = QCheckBox("w normie")
        self.chk_norma_nizej = QCheckBox("poniżej normy")
        self.chk_norma_wyzej = QCheckBox("powyżej normy")
        self.norma_filter_layout.addWidget(self.chk_norma_ok)
        self.norma_filter_layout.addWidget(self.chk_norma_nizej)
        self.norma_filter_layout.addWidget(self.chk_norma_wyzej)
        self.norma_filter_widget.setVisible(False)
        self.scroll_layout.addWidget(self.norma_filter_widget)

        # Przycisk Statystyka (toggle: on/off)
        self.btn_statystyka = QPushButton("Statystyka")
        self.btn_statystyka.setCheckable(True)
        self.btn_statystyka.toggled.connect(self.toggle_stats_mode)
        self.btn_statystyka.setStyleSheet("""
            QPushButton { padding: 6px; }
            QPushButton:checked { background-color: #2196F3; color: white; font-weight: bold; }
        """)
        left_layout.addWidget(self.btn_statystyka)

        # Przyciski eksportu RAPORTU (pod Statystyką)
        export_layout = QHBoxLayout()
        export_layout.setSpacing(6)

        self.btn_export_csv = QPushButton("📊 CSV")
        self.btn_export_csv.clicked.connect(self.export_stats_to_csv)
        self.btn_export_csv.setMaximumWidth(80)
        export_layout.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("📄 PDF")
        self.btn_export_pdf.clicked.connect(self.export_report_to_pdf)
        self.btn_export_pdf.setMaximumWidth(80)
        export_layout.addWidget(self.btn_export_pdf)

        left_layout.addLayout(export_layout)

        # dokończenie layoutu lewej kolumny
        left_layout.addStretch()
        self.splitter.addWidget(left_widget)  # lewa do splittera

        # PRAWY: Kontener (pasek statystyk nad tabelą + stos widoków)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Pasek statystyk (na start ukryty)
        self.stats_bar = QWidget()
        stats_bar_layout = QVBoxLayout(self.stats_bar)
        stats_bar_layout.setContentsMargins(0, 0, 0, 0)
        stats_bar_layout.setSpacing(4)

        # Rząd 1: akcje + wybór statystyk
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)

        self.btn_analizuj = QPushButton("Analizuj")
        self.btn_analizuj.clicked.connect(self.run_analysis)
        row1.addWidget(self.btn_analizuj)

        self.btn_dane = QPushButton("Dane")
        self.btn_dane.clicked.connect(lambda: [
            self.view_stack.setVisible(True),
            self.chart_widget.setVisible(False),
            self.view_stack.setCurrentIndex(0)
        ])
        row1.addWidget(self.btn_dane)

        self.chk_mean = QCheckBox("Średnia")
        self.chk_median = QCheckBox("Mediana")
        self.chk_min = QCheckBox("Minimum")
        self.chk_max = QCheckBox("Maximum")
        for w in (self.chk_mean, self.chk_median, self.chk_min, self.chk_max):
            w.stateChanged.connect(self.update_stats_view)

        row1.addWidget(self.chk_mean)
        row1.addWidget(self.chk_median)
        row1.addWidget(self.chk_min)
        row1.addWidget(self.chk_max)
        row1.addStretch(1)
        stats_bar_layout.addLayout(row1)

        # Rząd 2: dynamiczne checkboxy kategorii + wybór kolumny liczbowej
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)

        row2.addWidget(QLabel("Grupuj po:"))

        self.stats_scroll = QScrollArea()
        self.stats_scroll.setWidgetResizable(True)
        self.stats_scroll.setFixedHeight(55)

        self.stats_cat_widget = QWidget()
        self.stats_scroll_layout = QHBoxLayout(self.stats_cat_widget)
        self.stats_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_scroll_layout.setSpacing(6)
        self.stats_scroll.setWidget(self.stats_cat_widget)

        row2.addWidget(self.stats_scroll, stretch=1)

        row2.addWidget(QLabel("Wartość:"))
        self.cmb_value = QComboBox()
        self.cmb_value.currentIndexChanged.connect(self.update_stats_view)
        row2.addWidget(self.cmb_value)

        stats_bar_layout.addLayout(row2)

        self.stats_bar.setVisible(False)

        # Tabele + stos widoków
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)

        self.stats_table = QTableWidget()

        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.table)  # index 0: dane
        self.view_stack.setCurrentIndex(0)  #  start z tabelą
        self.view_stack.addWidget(self.stats_table)  # index 1: statystyka

        self.view_stack.setCurrentIndex(0)

        # Dynamiczne checkboxy kategorii
        self.stats_cat_widgets = {}

        right_layout.addWidget(self.stats_bar)
        right_layout.addWidget(self.view_stack, stretch=1)
        # Miejsce na wykres (ukryte na start)

        self.chart_widget = QWidget()

        # główny layout widoku wykresu
        self.chart_layout = QVBoxLayout(self.chart_widget)

        # pasek przycisków nad wykresem (NIGDY nie czyścimy tego layoutu)
        self.chart_toolbar = QHBoxLayout()
        self.chart_layout.addLayout(self.chart_toolbar)

        self.btn_back_from_chart = QPushButton("Wróć do danych")
        self.btn_back_from_chart.clicked.connect(self.close_chart_view)
        self.chart_toolbar.addWidget(self.btn_back_from_chart)

        self.btn_save_png = QPushButton("Zapisz PNG")
        self.btn_save_pdf = QPushButton("Zapisz PDF")

        self.btn_save_png.clicked.connect(self.export_chart_png)
        self.btn_save_pdf.clicked.connect(self.export_chart_pdf)

        self.chart_toolbar.addWidget(self.btn_save_png)
        self.chart_toolbar.addWidget(self.btn_save_pdf)
        self.chart_toolbar.addStretch(1)

        # kontener na canvas (TU będzie FigureCanvas, tylko to będziemy czyścić)
        self.chart_canvas_container = QWidget()
        self.chart_canvas_layout = QVBoxLayout(self.chart_canvas_container)
        self.chart_layout.addWidget(self.chart_canvas_container)

        # startowo ukryte przyciski
        self.btn_back_from_chart.setVisible(False)
        self.btn_save_png.setVisible(False)
        self.btn_save_pdf.setVisible(False)

        self.chart_widget.setVisible(False)
        right_layout.addWidget(self.chart_widget, stretch=0)

        # obie kolumny do splittera + log na dole (jedyny blok!)
        self.splitter.addWidget(right_widget)
        main_layout.addWidget(self.splitter)
        main_layout.addWidget(self.log_widget)
        self.splitter.setSizes([350, 1000])  # lewa mała, prawa duża
        self.splitter.setStretchFactor(1, 1)

    def import_csv_and_refresh(self):
        global current_df, current_file_path
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik CSV", ".",
            "CSV files (*.csv);;All files (*)"
        )
        if not file_path:
            self.log("Anulowano wybór pliku")
            return

        try:
            self.log(f"Wczytuję: {file_path}")
            current_df = pd.read_csv(file_path)
            current_file_path = file_path
            self.log(f"✓ CSV wczytany: {current_df.shape[0]} wierszy, {current_df.shape[1]} kolumn")
            self.log(f"Kolumny: {list(current_df.columns)}")
            self.create_dynamic_filters()
            self.update_norma_controls()
            # Uzupełnij comboboksy wizualizacji/oczu kolumnami z DF
            cols_all = [""] + [str(c) for c in current_df.columns]

            for cb in (self.cmb_wiz_x, self.cmb_wiz_y, self.cmb_wiz_group, self.cmb_eye_left, self.cmb_eye_right):
                cb.blockSignals(True)
                cb.clear()
                cb.addItems(cols_all)
                cb.blockSignals(False)

            self.update_table()  # odśwież tabelę + filtry
            self.log("Gotowe – dane załadowane")
        except Exception as e:
            self.log(f"✗ BŁĄD CSV: {e}")

    def create_dynamic_filters(self):
        global current_df
        if current_df is None:
            return

        # Wyczyść stare filtry (usuń layouty i widgety)
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            layout = item.layout()
            widget = item.widget()

            if layout is not None:
                while layout.count():
                    sub = layout.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
                layout.deleteLater()

            if widget is not None:
                widget.deleteLater()

        self.filter_widgets = {}

        for col in current_df.columns:
            chk = QCheckBox(str(col))
            chk.setChecked(False)
            chk.setMaximumWidth(140)
            chk.setMinimumWidth(140)
            chk.setToolTip(str(col))

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addWidget(chk)

            if pd.api.types.is_numeric_dtype(current_df[col]):
                s = pd.to_numeric(current_df[col], errors="coerce")
                vmin = s.min()
                vmax = s.max()
                if pd.isna(vmin): vmin = 0
                if pd.isna(vmax): vmax = 0

                spin_min = QSpinBox()
                spin_max = QSpinBox()
                spin_min.setMaximumWidth(60)
                spin_max.setMaximumWidth(60)

                spin_min.setRange(int(vmin) - 1, int(vmax) + 1)
                spin_max.setRange(int(vmin) - 1, int(vmax) + 1)
                spin_min.setValue(int(vmin))
                spin_max.setValue(int(vmax))

                row.addWidget(QLabel("od"))
                row.addWidget(spin_min)
                row.addWidget(QLabel("do"))
                row.addWidget(spin_max)

                self.filter_widgets[col] = {"chk": chk, "min": spin_min, "max": spin_max}
            else:
                combo = QComboBox()
                combo.setMinimumWidth(140)
                combo.setMaximumWidth(160)
                combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                combo.setMinimumContentsLength(8)
                combo.setToolTip(str(col))

                values = (
                    current_df[col]
                    .dropna()
                    .astype(str)
                    .value_counts()
                    .index[:20]
                    .tolist()
                )
                combo.addItem("")
                combo.addItems(values)

                row.addWidget(combo)
                self.filter_widgets[col] = {"chk": chk, "combo": combo}

            self.scroll_layout.addLayout(row)
        self.scroll_layout.addStretch(1)

    def update_table(self):
        global current_df
        if current_df is None:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Brak danych"])
            self.table.setItem(0, 0, QTableWidgetItem("Najpierw wczytaj CSV"))
            return

        try:
            display_df = zastosuj_filtry(current_df, self)
        except Exception as e:
            print(f"Błąd filtra: {e} - pokazuję surowe dane")
            display_df = current_df

        nrows = min(50, len(display_df))
        self.table.setRowCount(nrows)
        self.table.setColumnCount(len(display_df.columns))
        self.table.setHorizontalHeaderLabels(display_df.columns.tolist())

        for r in range(nrows):
            for c in range(len(display_df.columns)):
                self.table.setItem(r, c, QTableWidgetItem(str(display_df.iloc[r, c])))

        self.table.resizeColumnsToContents()
        self.table.setAlternatingRowColors(True)

        if self.stats_bar.isVisible():
            self.refresh_stats_controls()
            self.update_stats_view()

        if self.btn_statystyka.isChecked():
            self.refresh_stats_controls()

        # NOWE: Upewnij się tabela widoczna
        self.view_stack.setCurrentIndex(0)
        self.view_stack.setVisible(True)
        self.chart_widget.setVisible(False)
        self.splitter.setSizes([350, 1000])
        self.log("✓ Tabela odświeżona")

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            l = item.layout()
            if l is not None:
                self.clear_layout(l)
                l.deleteLater()
            if w is not None:
                w.deleteLater()

    def toggle_stats_bar(self):
        visible = not self.stats_bar.isVisible()
        self.stats_bar.setVisible(visible)  # pokaż/ukryj pasek opcji
        if visible:
            self.refresh_stats_controls()

    def refresh_stats_controls(self):
        global current_df
        if current_df is None:
            self.cmb_value.clear()
            self.clear_layout(self.stats_scroll_layout)
            self.stats_cat_widgets = {}
            return

        # Odśwież listę kolumn liczbowych do obliczeń
        self.cmb_value.blockSignals(True)
        self.cmb_value.clear()
        num_cols = [c for c in current_df.columns if pd.api.types.is_numeric_dtype(current_df[c])]
        self.cmb_value.addItems([str(c) for c in num_cols])
        self.cmb_value.blockSignals(False)

        # Odśwież checkboxy kategorii (kolumny do grupowania)
        self.clear_layout(self.stats_scroll_layout)
        self.stats_cat_widgets = {}

        cat_cols = [c for c in current_df.columns if not pd.api.types.is_numeric_dtype(current_df[c])]
        for col in cat_cols:
            chk = QCheckBox(str(col))
            chk.setChecked(False)
            chk.stateChanged.connect(self.update_stats_view)
            self.stats_scroll_layout.addWidget(chk)
            self.stats_cat_widgets[col] = chk

        self.stats_scroll_layout.addStretch(1)

    def get_selected_group_col(self):
        selected = [col for col, chk in self.stats_cat_widgets.items() if chk.isChecked()]
        return selected[0] if selected else None

    def get_filters_description(self) -> str:
        """Opis filtrów na podstawie różnic między current_df a df_po_filtrach (działa dla dowolnych kolumn)."""
        global current_df
        if current_df is None:
            return "Brak (current_df = None)"

        try:
            df_filt = zastosuj_filtry(current_df, self)
        except Exception:
            return "Nie udało się odczytać filtrów"

        if len(df_filt) == 0:
            return "Filtry: wynik pusty (0 wierszy)"

        if len(df_filt) == len(current_df):
            return "Brak (wszystkie dane)"

        desc = []

        for col in current_df.columns:
            s_all = current_df[col]
            s_filt = df_filt[col]

            # pomijamy kolumny kompletnie puste
            if s_all.notna().sum() == 0:
                continue

            # jeśli liczba unikalnych wartości się nie zmieniła, filtr raczej nie działa po tej kolumnie
            uniq_all = set(map(str, s_all.dropna().unique()))
            uniq_filt = set(map(str, s_filt.dropna().unique()))
            if uniq_all == uniq_filt:
                continue

            # NUMERYCZNE kolumny: opisz zakresem
            try:
                s_all_num = pd.to_numeric(s_all, errors="coerce")
                s_filt_num = pd.to_numeric(s_filt, errors="coerce")
                if s_filt_num.notna().sum() > 0 and s_all_num.notna().sum() > 0:
                    min_all, max_all = float(s_all_num.min()), float(s_all_num.max())
                    min_f, max_f = float(s_filt_num.min()), float(s_filt_num.max())
                    # jeśli zakres się zawęził
                    if (min_f > min_all) or (max_f < max_all):
                        desc.append(f"{col} w zakresie [{min_f:g}–{max_f:g}]")
                        continue  # nie rób już opisu po wartościach tekstowych
            except Exception:
                pass

            # KATEGORYCZNE / tekstowe: opisz zbiorem wartości
            if len(uniq_filt) == 1:
                val = next(iter(uniq_filt))
                desc.append(f"{col} = {val}")
            elif 1 < len(uniq_filt) <= 5:
                vals = ", ".join(sorted(uniq_filt))
                desc.append(f"{col} ∈ {{{vals}}}")
            else:
                desc.append(f"{col}: ograniczony zbiór wartości ({len(uniq_filt)} z {len(uniq_all)})")

        if not desc:
            return "Filtry aktywne (zmieniona liczba wierszy), ale niejednoznaczne po wartościach"

        return "; ".join(desc)

    def get_filtered_df(self):
        """Zwraca current_df po zastosowaniu filtrów, z zabezpieczeniem."""
        global current_df
        if current_df is None:
            return None
        try:
            return zastosuj_filtry(current_df, self).copy()
        except Exception:
            return current_df.copy()

    def render_df_to_table(self, df, table):
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for r in range(len(df)):
            for c in range(len(df.columns)):
                table.setItem(r, c, QTableWidgetItem(str(df.iat[r, c])))
        table.resizeColumnsToContents()

    def update_stats_view(self):
        global current_df
        if current_df is None:
            return

        group_col = self.get_selected_group_col()
        value_col = self.cmb_value.currentText()
        if not group_col or not value_col:
            self.stats_table.setRowCount(0)
            self.stats_table.setColumnCount(0)
            return

        aggs = []
        if self.chk_mean.isChecked(): aggs.append("mean")
        if self.chk_median.isChecked(): aggs.append("median")
        if self.chk_min.isChecked(): aggs.append("min")
        if self.chk_max.isChecked(): aggs.append("max")
        if not aggs:
            self.stats_table.setRowCount(0)
            self.stats_table.setColumnCount(0)
            return

        # 1) bierzemy dane przefiltrowane (to co w tabeli) [web:130]
        try:
            display_df = zastosuj_filtry(current_df, self).copy()
        except Exception:
            display_df = current_df.copy()

        # 2) groupby + agg na przefiltrowanych danych, reset_index żeby mieć normalny DF [web:141]
        df = display_df[[group_col, value_col]].copy()
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

        result = (
            df.groupby(group_col, dropna=False)[value_col]
            .agg(aggs)
            .reset_index()
        )

        self.render_df_to_table(result, self.stats_table)

    def run_analysis(self):
        # Najpierw policz wynik statystyk (na przefiltrowanych danych)
        self.update_stats_view()

        # Przełącz widok na tabelę statystyk
        self.view_stack.setCurrentIndex(1)  # pokaż statystykę

    def export_stats_to_csv(self):
        """Eksport statystyk z metadanymi (Parametr/Wartość w wierszach)"""
        global current_df

        if current_df is None:
            self.log("✗ Brak danych do eksportu")
            return

        if not self.btn_statystyka.isChecked():
            self.log("✗ Włącz tryb Statystyka przed eksportem")
            return

        rows = self.stats_table.rowCount()
        if rows == 0:
            self.log("✗ Brak statystyk do eksportu - kliknij Analizuj")
            return

        group_col = self.get_selected_group_col()
        value_col = self.cmb_value.currentText()

        # 1. Metadane jako wiersze: Parametr, Wartość
        agg_names = []
        if self.chk_mean.isChecked():
            agg_names.append("Średnia")
        if self.chk_median.isChecked():
            agg_names.append("Mediana")
        if self.chk_min.isChecked():
            agg_names.append("Minimum")
        if self.chk_max.isChecked():
            agg_names.append("Maximum")
        agg_text = ", ".join(agg_names) if agg_names else "Brak"

        meta_rows = [
            ("RAPORT", "STATYSTYKA"),
            ("Data", pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')),
            ("Plik", current_file_path.split('/')[-1]),
            ("Kolumna GRUPA", group_col or "brak"),
            ("Kolumna WARTOŚĆ", value_col or "brak"),
            ("Wierszy po filtrach", str(len(zastosuj_filtry(current_df, self)))),
            ("Wybrane agregacje", agg_text),
        ]

        # dodaj osobne wiersze dla każdego filtra
        filters_text = self.get_filters_description()
        if filters_text.startswith("Brak"):
            meta_rows.append(("Zastosowane filtry", "Brak (wszystkie dane)"))
        else:
            # rozbij po średnikach na osobne filtry
            for i, part in enumerate(filters_text.split("; ")):
                if i == 0:
                    meta_rows.append(("Zastosowane filtry", part))
                else:
                    meta_rows.append(("", part))

        # 2. Dane statystyczne z tabeli → DataFrame
        headers = [self.stats_table.horizontalHeaderItem(c).text()
                   for c in range(self.stats_table.columnCount())]
        data = []
        for r in range(rows):
            row_data = []
            for c in range(self.stats_table.columnCount()):
                item = self.stats_table.item(r, c)
                text = item.text() if item else ""
                # próbujemy zaokrąglić liczby
                try:
                    val = float(text.replace(",", "."))
                    text = f"{val:.2f}"
                except:
                    pass
                row_data.append(text)
            data.append(row_data)

        df_stats = pd.DataFrame(data, columns=headers)

        # 3. Zapis: metadane (2 kolumny), pusta linia, nagłówki + statystyki
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz raport statystyk",
            f"raport_{group_col}_{value_col}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            "CSV files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                # Metadane
                f.write("Parametr,Wartość\n")
                for param, value in meta_rows:
                    # Jeśli w wartości są przecinki, otocz w cudzysłów
                    if "," in value:
                        value = f'"{value}"'
                    f.write(f"{param},{value}\n")

                # separator (pusta linia, potem nagłówek sekcji)
                f.write("\n")
                f.write("STATYSTYKI\n")

                # Tabela statystyk (z własnymi nagłówkami i separacją)
                df_stats.to_csv(f, index=False, sep=',', lineterminator='\n')

            self.log(f"✓ Raport CSV zapisany: {file_path}")
        except Exception as e:
            self.log(f"✗ Błąd zapisu: {e}")

    def export_report_to_pdf(self):
        """Eksport raportu: metadane + statystyki + ostatni wykres do PDF"""
        global current_df

        if current_df is None:
            self.log("✗ Brak danych do eksportu")
            return

        if not self.btn_statystyka.isChecked():
            self.log("✗ Włącz tryb Statystyka przed eksportem")
            return

        # sprawdź, czy są statystyki
        rows = self.stats_table.rowCount()
        if rows == 0:
            self.log("✗ Brak statystyk do eksportu - kliknij Analizuj")
            return

        # dialog zapisu
        group_col = self.get_selected_group_col()
        value_col = self.cmb_value.currentText()

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz raport PDF",
            f"raport_{group_col}_{value_col}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.pdf",
            "PDF files (*.pdf)"
        )
        if not file_path:
            return

        try:
            with PdfPages(file_path) as pdf:
                # STRONA 1: opis + metadane + filtry (BEZ TABELI)
                fig1 = self._create_stats_report_figure()
                pdf.savefig(fig1, bbox_inches='tight')
                plt.close(fig1)

                # STRONA 2: sama tabela statystyk (NOWA)
                fig_table = self._create_stats_table_figure()
                pdf.savefig(fig_table, bbox_inches='tight')
                plt.close(fig_table)

                # STRONA 3: aktualny wykres z GUI (jeśli jest)
                fig_chart = getattr(self, "current_figure", None)
                if fig_chart is not None:
                    pdf.savefig(fig_chart, bbox_inches='tight')

                # STRONA 4: histogram WARTOŚĆ (jeśli możliwy)
                fig_hist = self._create_hist_figure()
                if fig_hist is not None:
                    pdf.savefig(fig_hist, bbox_inches='tight')
                    plt.close(fig_hist)

                # STRONA 5: słupkowy GRUPA vs WARTOŚĆ (średnia)
                fig_bar = self._create_bar_figure()
                if fig_bar is not None:
                    pdf.savefig(fig_bar, bbox_inches='tight')
                    plt.close(fig_bar)

                # metadane PDF
                info = pdf.infodict()
                info["Title"] = "Raport statystyczny"
                info["Author"] = "Aplikacja analityczna"
                info["Subject"] = "Statystyki i wizualizacje"
                info["CreationDate"] = pd.Timestamp.now()

            self.log(f"✓ Raport PDF zapisany: {file_path}")
        except Exception as e:
            self.log(f"✗ Błąd zapisu PDF: {e}")

    def _create_stats_report_figure(self):
        """Tworzy figurę z metadanymi i opisem (BEZ TABELI)"""
        import textwrap

        group_col = self.get_selected_group_col()
        value_col = self.cmb_value.currentText()

        agg_names = []
        if self.chk_mean.isChecked():
            agg_names.append("średnia")
        if self.chk_median.isChecked():
            agg_names.append("mediana")
        if self.chk_min.isChecked():
            agg_names.append("minimum")
        if self.chk_max.isChecked():
            agg_names.append("maksimum")
        agg_text = ", ".join(agg_names) if agg_names else "brak"

        filters_text = self.get_filters_description()
        filtered_df = zastosuj_filtry(current_df, self)
        n_records = len(filtered_df)

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")

        title = "RAPORT STATYSTYCZNY"
        desc = self._build_report_description_text(
            n_records=n_records,
            group_col=group_col,
            value_col=value_col,
            agg_text=agg_text,
            filters_text=filters_text
        )

        desc_lines = textwrap.wrap(desc, width=85)

        filter_lines = []
        if filters_text.startswith("Brak"):
            filter_lines.append("Filtry: brak (użyto wszystkich danych).")
        else:
            filter_lines.append("Filtry:")
            parts = filters_text.split("; ")
            for p in parts:  # ZMIANA: wszystkie filtry, nie [:4]
                filter_lines.append(f"  - {p}")

        meta_lines = [
            f"Data: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
            f"Plik: {current_file_path.split('/')[-1]}",
            f"Grupa: {group_col or 'brak'}",
            f"Wartość: {value_col or 'brak'}",
            f"Wierszy po filtrach: {n_records}",
            f"Agregacje: {agg_text}",
        ]

        y = 0.97
        ax.text(
            0.5, y, title,
            transform=ax.transAxes,
            fontsize=16,
            fontweight="bold",
            ha="center",
            va="top"
        )
        y -= 0.05

        ax.text(
            0.05, y, "Opis raportu",
            transform=ax.transAxes,
            fontsize=11,
            fontweight="bold",
            ha="left",
            va="top"
        )
        y -= 0.03

        for line in desc_lines:
            ax.text(
                0.05, y, line,
                transform=ax.transAxes,
                fontsize=9.5,
                ha="left",
                va="top"
            )
            y -= 0.022

        y -= 0.015

        for line in meta_lines:
            ax.text(
                0.05, y, line,
                transform=ax.transAxes,
                fontsize=9,
                ha="left",
                va="top"
            )
            y -= 0.022

        y -= 0.01

        for line in filter_lines:
            ax.text(
                0.05, y, line,
                transform=ax.transAxes,
                fontsize=9,
                ha="left",
                va="top"
            )
            y -= 0.022


        return fig

    def _create_stats_table_figure(self):
        """Tworzy osobną stronę PDF tylko z tabelą statystyk"""
        rows = self.stats_table.rowCount()
        cols = self.stats_table.columnCount()
        headers = [self.stats_table.horizontalHeaderItem(c).text() for c in range(cols)]

        data = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self.stats_table.item(r, c)
                text = item.text() if item else ""
                try:
                    val = float(text.replace(",", "."))
                    text = f"{val:.2f}"
                except:
                    pass
                row_data.append(text)
            data.append(row_data)

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")

        ax.text(
            0.5, 0.97, "TABELA STATYSTYK",
            transform=ax.transAxes,
            fontsize=16,
            fontweight="bold",
            ha="center",
            va="top"
        )

        table = ax.table(
            cellText=data,
            colLabels=headers,
            cellLoc="center",
            bbox=[0.02, 0.05, 0.96, 0.88],
            colWidths=[0.40, 0.15, 0.15, 0.15, 0.15]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.2)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_text_props(weight="bold")
            if col == 0:
                cell.get_text().set_ha("left")

        return fig

    def _build_report_description_text(self, n_records, group_col, value_col, agg_text, filters_text):
        if filters_text.startswith("Brak"):
            filters_sentence = "Nie zastosowano dodatkowych filtrów, więc analiza obejmuje wszystkie dostępne dane."
        else:
            filters_sentence = f"Do analizy zastosowano następujące filtry: {filters_text}."

        text = (
            f"Raport przedstawia wyniki analizy {n_records} rekordów danych. "
            f"Dane zostały pogrupowane według kolumny '{group_col or 'brak'}', "
            f"a analizowaną zmienną jest '{value_col or 'brak'}'. "
            f"Obliczone statystyki obejmują: {agg_text}. "
            f"{filters_sentence} "
            f"Na kolejnych stronach raportu znajdują się wykres główny oraz dodatkowe wizualizacje danych."
        )
        return text

    def _create_hist_figure(self):
        """Histogram dla kolumny WARTOŚĆ (cmb_value) na danych po filtrach."""
        df = self.get_filtered_df()
        if df is None or df.empty:
            return None

        value_col = self.cmb_value.currentText()
        if not value_col or value_col not in df.columns:
            return None

        s = pd.to_numeric(df[value_col], errors="coerce").dropna()
        if s.empty:
            return None

        fig, ax = plt.subplots(figsize=(11.69, 8.27))  # A4 poziomo
        ax.hist(s, bins=20, alpha=0.75, edgecolor="black")
        ax.set_title(f"Histogram: {value_col}", fontsize=14, weight="bold")
        ax.set_xlabel(value_col)
        ax.set_ylabel("Częstość")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        return fig

    def _create_bar_figure(self):
        """Słupkowy: GRUPA (get_selected_group_col) vs WARTOŚĆ."""
        df = self.get_filtered_df()
        if df is None or df.empty:
            return None

        group_col = self.get_selected_group_col()
        value_col = self.cmb_value.currentText()

        if not group_col or not value_col:
            return None
        if group_col not in df.columns or value_col not in df.columns:
            return None

        s_val = pd.to_numeric(df[value_col], errors="coerce")
        if s_val.notna().sum() == 0:
            return None

        grp = df.groupby(group_col, dropna=False)[value_col].mean().sort_values(ascending=False)
        if grp.empty:
            return None

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        grp.plot(kind="bar", ax=ax)
        ax.set_title(f"{value_col} wg {group_col} (średnia)", fontsize=14, weight="bold")
        ax.set_xlabel(group_col)
        ax.set_ylabel(value_col)
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        return fig

    def toggle_stats_mode(self, active: bool):
        # aktywny tryb: pokaż pasek, odśwież kontrolki, przełącz widok na statystyki
        self.stats_bar.setVisible(active)  # show/hide przez setVisible
        if active:
            self.refresh_stats_controls()
            # nie licz od razu; dopiero po kliknięciu "Analizuj"
            self.view_stack.setCurrentIndex(1)
        else:
            self.view_stack.setCurrentIndex(0)

    def toggle_norma_filter(self, state):
        """Bezpieczna wersja z ochroną przed usuniętym layoutem"""

        # Zabezpieczenie: sprawdź czy scroll_layout istnieje i nie jest pusty
        if not hasattr(self, 'scroll_layout') or self.scroll_layout.count() == 0:
            return  # czekaj na załadowanie danych

        visible = bool(state)

        # Zawsze odtwarzaj widget - nigdy nie ufaj staremu
        if visible:
            # Usuń stary jeśli istnieje
            try:
                if hasattr(self, 'norma_filter_widget') and self.norma_filter_widget:
                    self.scroll_layout.removeWidget(self.norma_filter_widget)
                    self.norma_filter_widget.deleteLater()
            except:
                pass

            # Stwórz nowy
            self.norma_filter_widget = QWidget()
            self.norma_filter_layout = QHBoxLayout(self.norma_filter_widget)
            self.chk_norma_ok = QCheckBox("w normie")
            self.chk_norma_nizej = QCheckBox("poniżej normy")
            self.chk_norma_wyzej = QCheckBox("powyżej normy")
            self.norma_filter_layout.addWidget(self.chk_norma_ok)
            self.norma_filter_layout.addWidget(self.chk_norma_nizej)
            self.norma_filter_layout.addWidget(self.chk_norma_wyzej)

            self.scroll_layout.insertWidget(0, self.norma_filter_widget)  # DODAJ na początku scrolla
            self.spin_norma_min.setValue(0.0)
            self.spin_norma_max.setValue(100.0)
        else:
            # Ukryj bezpiecznie
            try:
                if hasattr(self, 'norma_filter_widget') and self.norma_filter_widget:
                    self.norma_filter_widget.setVisible(False)
            except:
                pass

    def update_norma_controls(self):
        global current_df
        if current_df is None:
            self.cmb_norma_kol1.clear()
            self.cmb_norma_kol2.clear()
            return

        num_cols = []
        for c in current_df.columns:
            s = current_df[c]
            # szybka próba konwersji: przecinek->kropka, wywal spacje, zamień na liczby
            s2 = pd.to_numeric(
                s.astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False),
                errors="coerce"
            )
            # uznaj kolumnę za "liczbową", jeśli choć np. 60% wierszy da się zrzutować
            if s2.notna().mean() >= 0.60:
                num_cols.append(str(c))

        self.cmb_norma_kol1.blockSignals(True)
        self.cmb_norma_kol2.blockSignals(True)
        self.cmb_norma_kol1.clear()
        self.cmb_norma_kol2.clear()
        self.cmb_norma_kol1.addItems([""] + num_cols)
        self.cmb_norma_kol2.addItems([""] + num_cols)
        self.cmb_norma_kol1.blockSignals(False)
        self.cmb_norma_kol2.blockSignals(False)

    def update_wizualizacja_controls(self):
        global current_df
        if current_df is None:
            self.cmb_wiz_x.clear()
            self.cmb_wiz_y.clear()
            self.cmb_wiz_group.clear()
            return

        num_cols = [c for c in current_df.columns if pd.api.types.is_numeric_dtype(current_df[c])]
        all_cols = list(current_df.columns)

        # X: dowolna kolumna (kategorie/numery)
        self.cmb_wiz_x.blockSignals(True)
        self.cmb_wiz_x.clear()
        self.cmb_wiz_x.addItems(all_cols)
        self.cmb_wiz_x.blockSignals(False)

        # Y: tylko liczbowe
        self.cmb_wiz_y.blockSignals(True)
        self.cmb_wiz_y.clear()
        self.cmb_wiz_y.addItems(num_cols)
        self.cmb_wiz_y.blockSignals(False)

        # Grupuj po: dowolna kolumna lub pusto
        self.cmb_wiz_group.blockSignals(True)
        self.cmb_wiz_group.clear()
        self.cmb_wiz_group.addItem("")
        self.cmb_wiz_group.addItems(all_cols)
        self.cmb_wiz_group.blockSignals(False)

        # DODAJ NA KOŃCU update_wizualizacja_controls()
        self.cmb_eye_left.blockSignals(True)
        self.cmb_eye_left.clear()
        self.cmb_eye_left.addItems(num_cols)
        self.cmb_eye_left.blockSignals(False)

        self.cmb_eye_right.blockSignals(True)
        self.cmb_eye_right.clear()
        self.cmb_eye_right.addItems(num_cols)
        self.cmb_eye_right.blockSignals(False)

    def run_visualization(self):
        global current_df
        if current_df is None:
            self.log("Brak danych – najpierw wczytaj CSV")
            return

        self.log("Rozpoczynam wizualizację...")
        dfp = zastosuj_filtry(current_df, self)
        if dfp.empty:
            self.log("Brak danych po filtrach")
            return

        # 1) ZAWSZE bierzemy dane po filtrach (koty/psy/itd.)
        dfp = zastosuj_filtry(current_df, self)
        # --- NAPRAWA: usuń zdublowane nazwy kolumn (pivot/groupby tego nie znosi) ---
        if dfp.columns.duplicated().any():
            dup = dfp.columns[dfp.columns.duplicated()].tolist()
            print("UWAGA: zdublowane kolumny w dfp:", dup)
            dfp = dfp.loc[:, ~dfp.columns.duplicated()].copy()

        if dfp.empty:
            return

        wiz_type = self.cmb_wiz_type.currentText()
        x_col = self.cmb_wiz_x.currentText().strip()
        y_col = self.cmb_wiz_y.currentText().strip()
        g_col = self.cmb_wiz_group.currentText().strip()  # może być ""
        print("WIZ:", wiz_type, "X=", repr(x_col), "Y=", repr(y_col), "G=", repr(g_col))
        print("dfp shape:", dfp.shape)
        print("duplikaty kolumn:", dfp.columns[dfp.columns.duplicated()].tolist())
        print("czy X jest w dfp:", x_col in dfp.columns, "czy Y:", y_col in dfp.columns, "czy G:",
              (g_col in dfp.columns if g_col else None))

        agg = self.cmb_wiz_agg.currentText()
        topn = int(self.spin_wiz_topn.value())
        sort_mode = self.cmb_wiz_sort.currentText()

        title = self.txt_title.text().strip()
        xlabel = self.txt_xlabel.text().strip()
        ylabel = self.txt_ylabel.text().strip()

        plt.ioff()
        fig, ax = plt.subplots(figsize=(10, 6))
        chart_done = False

        # helper: sortowanie i topN (po sumie/średniej po kolumnach)
        def _apply_topn_and_sort(pvt: pd.DataFrame) -> pd.DataFrame:
            out = pvt.copy()
            if out.shape[0] > topn:
                # wybierz topN po "łącznej wielkości" w wierszu
                score = out.sum(axis=1, numeric_only=True)
                out = out.loc[score.sort_values(ascending=False).index[:topn]]
            if sort_mode != "brak":
                score = out.sum(axis=1, numeric_only=True)
                out = out.loc[score.sort_values(ascending=(sort_mode == "rosnąco")).index]
            return out

        if wiz_type == "Histogram":
            # Histogram: używamy tylko Y (X niepotrzebne)
            s = pd.to_numeric(dfp[y_col], errors="coerce").dropna()
            if s.empty:
                return

            if g_col:
                # histogram per grupa (nakładany)
                for name, sub in dfp.groupby(g_col, dropna=False):
                    ss = pd.to_numeric(sub[y_col], errors="coerce").dropna()
                    if not ss.empty:
                        ax.hist(ss, bins=20, alpha=0.45, label=str(name), edgecolor="black")
                ax.legend(title=g_col)
            else:
                ax.hist(s, bins=20, alpha=0.75, edgecolor="black")

            ax.set_title(title or f"Histogram: {y_col}")
            ax.set_xlabel(xlabel or y_col)
            ax.set_ylabel(ylabel or "Częstość")

        elif wiz_type == "Słupkowy":
            # Słupkowy: X = kategoria, Y = liczba; opcjonalnie druga kategoria w "Grupuj po"
            if not x_col or not y_col:
                return
            # --- PORÓWNANIE OCZU (DODAJ TUTAJ, przed if g_col:) ---
            left_col = self.cmb_eye_left.currentText().strip()
            right_col = self.cmb_eye_right.currentText().strip()

            if self.chk_compare_eyes.isChecked() and left_col and right_col and left_col != right_col:
                grp2 = dfp.groupby(x_col, dropna=False)[[left_col, right_col]].agg(agg)

                # TopN + sortowanie po sumie obu oczu
                if grp2.shape[0] > topn:
                    score = grp2.sum(axis=1, numeric_only=True).sort_values(ascending=False)
                    grp2 = grp2.loc[score.index[:topn]]

                if sort_mode != "brak":
                    score = grp2.sum(axis=1, numeric_only=True).sort_values(
                        ascending=(sort_mode == "rosnąco")
                    )
                    grp2 = grp2.loc[score.index]

                self.last_export_df = grp2.reset_index()
                grp2.plot(kind="bar", ax=ax)  # grouped bars dla 2 kolumn [web:489]
                ax.set_title(title or f"Słupkowy ({agg}): porównanie oczu wg {x_col}")
                ax.set_xlabel(xlabel or x_col)
                ax.set_ylabel(ylabel or f"{agg}({left_col}/{right_col})")
                ax.legend(["Lewe", "Prawe"])
                # ważne: kończymy blok słupkowy tutaj
                ax.grid(True, alpha=0.25)
                plt.tight_layout()

                # kończymy logikę słupkowego tutaj – reszta (wstawienie do UI) zrobi się na końcu funkcji
                chart_done = True

            # --- KONIEC PORÓWNANIA OCZU ---
            if not chart_done:
                if g_col == x_col:
                    print("Grupuj po nie może być takie samo jak X:", g_col)
                    return

            # pivot_table daje automatyczne grupy i agregację [web:465]
                if g_col:
                    try:
                        dfp[y_col] = pd.to_numeric(dfp[y_col], errors="coerce")
                        pvt = pd.pivot_table(dfp, values=y_col, index=x_col, columns=g_col, aggfunc=agg)
                        print("pivot_table OK, shape:", pvt.shape)
                        print(pvt.head(3))
                    except Exception as e:
                        print("BŁĄD pivot_table:", type(e).__name__, e)
                        return

                    if pvt.empty:
                        print("pivot_table puste (brak danych po agregacji)")
                        return

                    pvt = _apply_topn_and_sort(pvt)
                    self.last_export_df = pvt.reset_index()
                    pvt.plot(kind="bar", ax=ax)
                    ax.legend(title=g_col)

                else:
                    grp = dfp.groupby(x_col, dropna=False)[y_col].agg(agg)
                    grp = grp.sort_values(ascending=False)
                    grp = grp.head(topn)
                    self.last_export_df = grp.reset_index(name=y_col)
                    grp.plot(kind="bar", ax=ax)

                ax.set_title(title or f"Słupkowy ({agg}): {y_col} wg {x_col}")
                ax.set_xlabel(xlabel or x_col)
                ax.set_ylabel(ylabel or f"{agg}({y_col})")

        # NORMA jako pas (tylko gdy Y jest na osi Y)
        if self.chk_wiz_norma.isChecked() and y_col:
            min_norm = self.spin_norma_min.value()
            max_norm = self.spin_norma_max.value()
            ax.axhspan(min_norm, max_norm, alpha=0.15, color="green", label=f"Norma [{min_norm}-{max_norm}]")
            ax.axhline(min_norm, color="green", linestyle="--", linewidth=1.5)
            ax.axhline(max_norm, color="green", linestyle="--", linewidth=1.5)

        ax.grid(True, alpha=0.25)
        plt.tight_layout()

        # zapamiętaj wykres do eksportu PDF (zamknij poprzedni żeby nie marnować pamięci)
        old_fig = getattr(self, 'current_figure', None)
        if old_fig is not None:
            plt.close(old_fig)
        self.current_figure = fig

        # wyczyść poprzedni canvas (NIE ruszamy paska przycisków)
        while self.chart_canvas_layout.count():
            item = self.chart_canvas_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        canvas = FigureCanvas(fig)
        self.chart_canvas_layout.addWidget(canvas)

        self.view_stack.setVisible(False)
        self.chart_widget.setVisible(True)
        self.splitter.setSizes([350, 1000])
        self.log("✓ Wykres narysowany – użyj przycisków eksportu")

        self.btn_back_from_chart.setVisible(True)
        self.btn_save_png.setVisible(True)
        self.btn_save_pdf.setVisible(True)

    def close_chart_view(self):
        # usuń tylko canvasy z kontenera (toolbar z przyciskami zostaje)
        while self.chart_canvas_layout.count():
            item = self.chart_canvas_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self.chart_widget.setVisible(False)
        self.view_stack.setVisible(True)
        self.view_stack.setCurrentIndex(0)  # NOWE: zawsze wracaj do tabeli

        self.btn_back_from_chart.setVisible(False)
        self.btn_save_png.setVisible(False)
        self.btn_save_pdf.setVisible(False)

    def export_chart_png(self):
        fig = getattr(self, "last_fig", None)
        if fig is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz wykres jako PNG", "", "PNG (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        fig.savefig(path, dpi=200, bbox_inches="tight")

    def export_chart_pdf(self):
        fig = getattr(self, "last_fig", None)
        if fig is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz wykres jako PDF", "", "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        fig.savefig(path, bbox_inches="tight")

    def export_data_csv(self):
        df = getattr(self, "last_export_df", None)
        if df is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz dane jako CSV", "", "CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")

    def log(self, message: str):
        """Log systemowy z timestamp"""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        self.log_widget.appendPlainText(line)
        self.log_widget.verticalScrollBar().setValue(self.log_widget.verticalScrollBar().maximum())

        self.statusBar().showMessage(message, 3000)

    def show_sql_unavailable_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Import z bazy SQL")
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl = QLabel("Opcja tymczasowo niedostępna. Przepraszamy za utrudnienia.")
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        import os
        img_path = os.path.join(os.path.dirname(__file__), "importsql.jpg")
        pix = QPixmap(img_path)

        if not pix.isNull():
            pix = pix.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(pix)
        else:
            img_label.setText(f"(Nie znaleziono obrazka: {img_path})")

        layout.addWidget(img_label)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        dlg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
