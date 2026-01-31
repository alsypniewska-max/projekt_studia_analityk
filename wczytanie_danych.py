import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QMenu

import pandas as pd

def import_csv():
    tabela = pd.read_csv("pomiary_cisnienia.csv")
    print(tabela)
    pass  # Dodaj tu kod importu CSV

def import_sql():
    """
    Pusta funkcja do importu z bazy SQL.
    Zaimplementuj np. sqlite3.connect() i pd.read_sql().
    """
    pass  # Dodaj tu kod importu SQL

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wczytaj dane")
        self.setFixedSize(300, 150)

        # Central widget i layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Przycisk z menu
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        menu = QMenu(self)
        menu.addAction("Import z CSV", import_csv)
        menu.addAction("Import z bazy SQL", import_sql)
        self.btn_wczytaj.setMenu(menu)
        layout.addWidget(self.btn_wczytaj)

# Uruchomienie aplikacji
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
