import sys
import sqlite3
import hashlib
import csv

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QFormLayout,
    QListWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QInputDialog, QLineEdit,
    QDateEdit, QMessageBox, QLabel, QFileDialog,
    QComboBox, QAbstractItemView
)

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QDoubleValidator

import shutil
from datetime import datetime

import os

APP_FOLDER = os.path.join(os.getenv("LOCALAPPDATA"), "ExpenseTracker")

if not os.path.exists(APP_FOLDER):
    os.makedirs(APP_FOLDER)

DB_FILE = os.path.join(APP_FOLDER, "expense_data.db")


class ExpenseTracker(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Expense Tracker")
        self.resize(1250, 720)

        self.current_category = None
        self.current_type = None
        self.current_month = QDate.currentDate().month()
        self.current_year = str(QDate.currentDate().year())

        self.dark_mode = False

        # DATABASE
        self.db = sqlite3.connect(DB_FILE)
        self.cursor = self.db.cursor()
        self.init_database()

        # UI
        self.build_ui()

        # LOAD
        self.load_categories()

    # =========================
    # DATABASE
    # =========================
    def init_database(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            name TEXT PRIMARY KEY,
            type TEXT,
            password TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            date TEXT,
            item TEXT,
            inward REAL,
            outward REAL
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            date TEXT,
            person TEXT,
            amount REAL,
            return_date TEXT,
            status TEXT
        )
        """)

        self.db.commit()

    # =========================
    # UI
    # =========================
    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # ---------------- LEFT PANEL ----------------
        left_layout = QVBoxLayout()

        self.category_list = QListWidget()

        add_cat_btn = QPushButton("Add Category")
        del_cat_btn = QPushButton("Delete Category")

        left_layout.addWidget(QLabel("Categories"))
        left_layout.addWidget(self.category_list)
        left_layout.addWidget(add_cat_btn)
        left_layout.addWidget(del_cat_btn)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        main_layout.addWidget(left_widget, 1)

        # ---------------- RIGHT PANEL ----------------
        right_layout = QVBoxLayout()

        # DASHBOARD CARDS
        cards = QHBoxLayout()

        self.balance_card = QLabel("Balance\n0")
        self.income_card = QLabel("Income\n0")
        self.expense_card = QLabel("Expense\n0")

        for c in [self.balance_card, self.income_card, self.expense_card]:
            c.setAlignment(Qt.AlignCenter)
            cards.addWidget(c)

        right_layout.addLayout(cards)

        # SEARCH
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search item...")
        right_layout.addWidget(self.search_box)

        # YEAR + THEME
        filter_layout = QHBoxLayout()

        self.year_box = QComboBox()
        for y in range(2020, 2036):
            self.year_box.addItem(str(y))

        self.year_box.setCurrentText(self.current_year)

        self.theme_btn = QPushButton("Switch Theme")

        filter_layout.addWidget(QLabel("Year"))
        filter_layout.addWidget(self.year_box)
        filter_layout.addWidget(self.theme_btn)

        right_layout.addLayout(filter_layout)

        # FORM
        form = QFormLayout()

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())

        self.item_input = QLineEdit()

        validator = QDoubleValidator(0, 999999999, 2)

        self.inward_input = QLineEdit()
        self.inward_input.setValidator(validator)

        self.outward_input = QLineEdit()
        self.outward_input.setValidator(validator)

        form.addRow("Date", self.date_input)
        form.addRow("Item / Person", self.item_input)

        money_row = QHBoxLayout()

        money_row.addWidget(QLabel("Inward / Amount"))
        money_row.addWidget(self.inward_input)
        money_row.addWidget(QLabel("Outward"))
        money_row.addWidget(self.outward_input)

        form.addRow(money_row)

        right_layout.addLayout(form)

        # BUTTONS
        btn_row = QHBoxLayout()

        self.add_btn = QPushButton("Add")
        self.del_btn = QPushButton("Delete")
        self.export_btn = QPushButton("Export")
        self.backup_btn = QPushButton("Backup")
        self.restore_btn = QPushButton("Restore")
        self.report_btn = QPushButton("Report")

        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.backup_btn)
        btn_row.addWidget(self.restore_btn)
        btn_row.addWidget(self.report_btn) 

        right_layout.addLayout(btn_row)

        # MONTH BUTTONS
        month_layout = QHBoxLayout()

        self.month_buttons = []

        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]

        for i, m in enumerate(months, start=1):
            btn = QPushButton(m)
            btn.setFixedWidth(40)
            btn.clicked.connect(lambda _, x=i: self.change_month(x))
            month_layout.addWidget(btn)
            self.month_buttons.append(btn)

        right_layout.addLayout(month_layout)

        # TABLE
        self.table = QTableWidget()
        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels(
            ["ID","Date","Item","Inward","Outward","Balance"]
        )

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        right_layout.addWidget(self.table)

        # SUMMARY PANEL
        summary = QHBoxLayout()

        self.opening = QLabel("Opening: 0")
        self.income = QLabel("Income: 0")
        self.expense = QLabel("Expense: 0")
        self.closing = QLabel("Closing: 0")
        self.forward = QLabel("Forward: 0")

        for w in [self.opening, self.income, self.expense, self.closing, self.forward]:
            w.setAlignment(Qt.AlignCenter)
            summary.addWidget(w)

        right_layout.addLayout(summary)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        main_layout.addWidget(right_widget, 4)

        # SIGNALS
        add_cat_btn.clicked.connect(self.add_category)
        del_cat_btn.clicked.connect(self.delete_category)

        self.category_list.currentTextChanged.connect(self.open_category)

        self.add_btn.clicked.connect(self.add_transaction)
        self.del_btn.clicked.connect(self.delete_transaction)
        self.export_btn.clicked.connect(self.export_csv)
        self.backup_btn.clicked.connect(self.backup_database)
        self.restore_btn.clicked.connect(self.restore_database)
        self.report_btn.clicked.connect(self.generate_financial_report)
        self.year_box.currentTextChanged.connect(self.change_year)

        self.search_box.textChanged.connect(self.search)

        self.theme_btn.clicked.connect(self.switch_theme)

        self.apply_theme()

    # =========================
    # THEME
    # =========================
    def apply_theme(self):

        self.setStyleSheet("""
        QWidget{background:#0F172A;color:#E2E8F0;}
        QPushButton{background:#6366F1;color:white;border-radius:6px;padding:6px;}
        QPushButton:hover{background:#4F46E5;}
        QLineEdit,QComboBox,QDateEdit{background:#334155;border-radius:6px;padding:5px;}
        QTableWidget{background:#1E293B;border-radius:8px;}
        """)

        self.balance_card.setStyleSheet(
            "background:#1E293B;padding:18px;border-radius:10px;font-size:18px;"
        )
        self.income_card.setStyleSheet(
            "background:#052e16;color:#22C55E;padding:18px;border-radius:10px;font-size:18px;"
        )
        self.expense_card.setStyleSheet(
            "background:#3b0a0a;color:#EF4444;padding:18px;border-radius:10px;font-size:18px;"
        )

    def switch_theme(self):

        if self.dark_mode:
            self.apply_theme()
            self.dark_mode = False
        else:
            self.setStyleSheet("""
            QWidget{background:#000;color:#EEE;}
            QPushButton{background:#222;color:white;border-radius:6px;padding:6px;}
            QPushButton:hover{background:#444;}
            QLineEdit,QComboBox,QDateEdit{background:#1a1a1a;border-radius:6px;padding:5px;}
            QTableWidget{background:#111;border-radius:8px;}
            """)
            self.dark_mode = True

    # =========================
    # CATEGORY
    # =========================
    def load_categories(self):

        self.category_list.clear()
    

        rows = self.cursor.execute("SELECT name FROM categories")

        for r in rows:
            self.category_list.addItem(r[0])

        if self.category_list.count() == 0:
            self.current_category = None    

    def add_category(self):

        name, ok = QInputDialog.getText(self, "Create Category", "Category Name:")

        if not ok or not name.strip():
            return

        category_type, ok = QInputDialog.getItem(
            self,
            "Category Type",
            "Choose category type:",
            ["Ledger (Income / Expense)", "Note (Money Lending)", "Hidden (Password Protected)"],
            0,
            False
        )

        if not ok:
            return

        if category_type.startswith("Ledger"):
            ctype = "ledger"
        elif category_type.startswith("Note"):
            ctype = "note"
        else:
            ctype = "hidden"

        password_hash = None

        if ctype == "hidden":

            pwd, ok = QInputDialog.getText(
                self,
                "Hidden Category Password",
                "Enter password:",
                QLineEdit.Password
            )

            if not ok or not pwd:
                QMessageBox.warning(self, "Error", "Password required")
                return

            password_hash = hashlib.sha256(pwd.encode()).hexdigest()

        try:

            self.cursor.execute(
                "INSERT INTO categories (name,type,password) VALUES (?,?,?)",
                (name, ctype, password_hash)
            )

            self.db.commit()

            self.category_list.addItem(name)

        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Duplicate", "Category already exists")

    def delete_category(self):

        item = self.category_list.currentItem()

        if not item:
            return

        name = item.text()

        self.cursor.execute("DELETE FROM categories WHERE name=?", (name,))
        self.cursor.execute("DELETE FROM transactions WHERE category=?", (name,))
        self.cursor.execute("DELETE FROM notes WHERE category=?", (name,))

        self.db.commit()

        self.load_categories()
        self.current_category = None
        self.table.setRowCount(0)

    # =========================
    # OPEN CATEGORY
    # =========================
    def open_category(self, name):

       
        row = self.cursor.execute(
            "SELECT type,password FROM categories WHERE name=?",
            (name,)
        ).fetchone()

        if not row:
            return

        typ, pwd = row

        if typ == "hidden":

            text, ok = QInputDialog.getText(
                self, "Password", "Enter password:", QLineEdit.Password
            )

            if not ok:
                return

            if hashlib.sha256(text.encode()).hexdigest() != pwd:
                QMessageBox.warning(self, "Error", "Wrong password")
                return

        self.current_category = name
        self.current_type = typ

        self.load_table()

    # =========================
    # MONTH
    # =========================
    def change_month(self, m):

        self.current_month = m
        self.load_table()

    # =========================
    # TABLE
    # =========================
    def load_table(self):

        self.table.setRowCount(0)

        if not self.current_category:
            return

        rows = self.cursor.execute("""
           SELECT id,date,item,inward,outward
           FROM transactions
           WHERE category=? 
           AND strftime('%m',date)=?
           AND strftime('%Y',date)=?
           """, (self.current_category, f"{self.current_month:02d}", self.current_year))

        balance = self.get_opening_balance()

        for r in rows:

            rid, date, item, inw, outw = r

            balance += inw - outw

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(rid)))
            self.table.setItem(row, 1, QTableWidgetItem(date))
            self.table.setItem(row, 2, QTableWidgetItem(item))
            self.table.setItem(row, 3, QTableWidgetItem(str(inw)))
            self.table.setItem(row, 4, QTableWidgetItem(str(outw)))
            self.table.setItem(row, 5, QTableWidgetItem(str(balance)))
    
        self.update_summary()

    # =========================
    # GET OPENING BALANCE
    # =========================
    def get_opening_balance(self):

        if not self.current_category:
            return 0

        rows = self.cursor.execute("""
         SELECT inward,outward,date
         FROM transactions
         WHERE category=?
         AND date < ?
        """, (self.current_category, f"{self.current_year}-{self.current_month:02d}-01"))

        opening = 0

        for r in rows:
         opening += r[0] - r[1]

        return opening
    # =========================
    # UPDATE SUMMARY
    # =========================
    def update_summary(self):

        if not self.current_category:
            return

        rows = self.cursor.execute("""
            SELECT inward,outward
            FROM transactions
            WHERE category=? 
            AND strftime('%m',date)=?
            AND strftime('%Y',date)=?
            """, (self.current_category, f"{self.current_month:02d}", self.current_year))

        income = 0
        expense = 0
        opening = self.get_opening_balance()

        for r in rows:
            income += r[0]
            expense += r[1]

        balance = opening + income - expense

        # Dashboard cards
        self.balance_card.setText(f"Balance\n{balance}")
        self.income_card.setText(f"Income\n{income}")
        self.expense_card.setText(f"Expense\n{expense}")

        # Bottom summary
        self.opening.setText(f"Opening: {opening}")
        self.income.setText(f"Income: {income}")
        self.expense.setText(f"Expense: {expense}")
        self.closing.setText(f"Closing: {balance}")
        self.forward.setText(f"Forward: {balance}")

    # =========================
    # ADD
    # =========================
    def add_transaction(self):

        if not self.current_category:
           QMessageBox.warning(self, "No Category", "Please select a category first.")
           return

        date = self.date_input.date().toString("yyyy-MM-dd")
        item = self.item_input.text()

        inward = float(self.inward_input.text() or 0)
        outward = float(self.outward_input.text() or 0)

        self.cursor.execute("""
        INSERT INTO transactions(category,date,item,inward,outward)
        VALUES(?,?,?,?,?)
        """, (self.current_category, date, item, inward, outward))

        self.db.commit()

        self.load_table()

        self.item_input.clear()
        self.inward_input.clear()
        self.outward_input.clear()

    # =========================
    # DELETE
    # =========================
    def delete_transaction(self):

        row = self.table.currentRow()

        if row < 0:
            return

        tid = int(self.table.item(row, 0).text())

        self.cursor.execute(
            "DELETE FROM transactions WHERE id=?", (tid,)
        )

        self.db.commit()

        self.load_table()

    # =========================
    # SEARCH
    # =========================
    def search(self, text):

        for row in range(self.table.rowCount()):

            item = self.table.item(row, 2)

            if item:
                self.table.setRowHidden(
                    row, text.lower() not in item.text().lower()
                )

    # =========================
    # EXPORT
    # =========================
    def export_csv(self):

        if not self.current_category:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save File", f"{self.current_category}.csv", "CSV Files (*.csv)"
        )

        if not path:
            return

        rows = self.cursor.execute("""
        SELECT date,item,inward,outward
        FROM transactions
        WHERE category=?
        """, (self.current_category,))

        with open(path, "w", newline="") as f:

            writer = csv.writer(f)

            writer.writerow(["Date", "Item", "Inward", "Outward"])

            for r in rows:
                writer.writerow(r)

        QMessageBox.information(self, "Export", "Export successful")


    # =========================
    # DATABASE BACKUP
    # =========================
    def backup_database(self):

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            backup_name = f"expense_backup_{timestamp}.db"

            backup_path = os.path.join(APP_FOLDER, backup_name)

            self.db.commit()

            shutil.copy(DB_FILE, backup_path)

            QMessageBox.information(
                self,
                "Backup Created",
                f"Backup saved successfully:\n{backup_path}"
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Backup Error",
                str(e)
            )
    # =========================
    # DATABASE RESTORE
    # =========================
    def restore_database(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            APP_FOLDER,
            "Database Files (*.db)"
        )

        if not file_path:
            return

        try:
            self.db.close()

            shutil.copy(file_path, DB_FILE)

            self.db = sqlite3.connect(DB_FILE)
            self.cursor = self.db.cursor()

            QMessageBox.information(
                self,
                "Restore Successful",
                "Database restored successfully.\nRestart recommended."
            )

            self.load_categories()
            self.load_table()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Restore Failed",
                str(e)
            )

    # =========================
    # CLEAN OLD BACKUPS
    # =========================
    def clean_old_backups(self):

        try:
            now = datetime.now()

            for file in os.listdir(APP_FOLDER):

                if file.startswith("auto_backup_") or file.startswith("expense_backup_"):

                    path = os.path.join(APP_FOLDER, file)

                    file_time = datetime.fromtimestamp(os.path.getmtime(path))

                    if (now - file_time).days > 30:
                        os.remove(path)

        except:
            pass

    # =========================
    # FINANCIAL REPORT
    # =========================
    def generate_financial_report(self):

        if not self.current_category:
            QMessageBox.warning(self, "Report", "Select category first")
            return

        try:

            rows = self.cursor.execute("""
            SELECT date,item,inward,outward
            FROM transactions
            WHERE category=?
            """, (self.current_category,))

            report_name = f"financial_report_{self.current_category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            report_path = os.path.join(APP_FOLDER, report_name)

            with open(report_path, "w", newline="") as f:

                writer = csv.writer(f)

                writer.writerow(["Date", "Item", "Inward", "Outward"])

                total_in = 0
                total_out = 0

                for r in rows:
                    writer.writerow(r)
                    total_in += r[2]
                    total_out += r[3]

                writer.writerow([])
                writer.writerow(["TOTAL INCOME", total_in])
                writer.writerow(["TOTAL EXPENSE", total_out])
                writer.writerow(["BALANCE", total_in - total_out])

            QMessageBox.information(
                self,
                "Report Generated",
                f"Report saved:\n{report_path}"
            )

        except Exception as e:

            QMessageBox.warning(self, "Report Error", str(e))

    def closeEvent(self, event):

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"auto_backup_{timestamp}.db"
            backup_path = os.path.join(APP_FOLDER, backup_name)

            self.db.commit()
            shutil.copy(DB_FILE, backup_path)

        except:
            pass

        self.clean_old_backups()
        self.db.close()
        event.accept()       

    # =========================
    # CHANGE YEAR
    # =========================
    def change_year(self, year):
    
        self.current_year = year
        self.load_table()    


app = QApplication(sys.argv)

window = ExpenseTracker()
window.show()

sys.exit(app.exec())