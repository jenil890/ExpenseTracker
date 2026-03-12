import sys
import sqlite3
import csv

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QFormLayout,
    QListWidget, QTableWidget, QTableWidgetItem,
    QPushButton, QInputDialog, QLineEdit,
    QDateEdit, QMessageBox, QLabel, QFileDialog,
    QComboBox, QAbstractItemView,QTextEdit,QSizePolicy
)

from PySide6.QtWidgets import QProgressBar
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtGui import QKeySequence, QTextListFormat, QTextCharFormat, QFont, QAction
from PySide6.QtWidgets import QToolBar
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
            subtype TEXT
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

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            person TEXT,
            loan_amount REAL,
            interest REAL,
            installments INTEGER,
            emi REAL,
            start_date TEXT,
            remaining REAL,
            status TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            payment_date TEXT,
            amount REAL
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
        self.cards_layout = QHBoxLayout()

        self.balance_card = QLabel("Balance\n0")
        self.income_card = QLabel("Income\n0")
        self.expense_card = QLabel("Expense\n0")

        

        for c in [self.balance_card, self.income_card, self.expense_card]:
            c.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(c)

        right_layout.addLayout(self.cards_layout)

        # SEARCH
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search item...")
        right_layout.addWidget(self.search_box)

        # NOte FORMAT TOOLBAR
        self.note_toolbar = QToolBar()
        self.note_toolbar.setMovable(False)

        bold_action = QAction("B", self)
        bold_action.setShortcut(QKeySequence("Ctrl+B"))
        bold_action.triggered.connect(self.toggle_bold)

        italic_action = QAction("I", self)
        italic_action.setShortcut(QKeySequence("Ctrl+I"))
        italic_action.triggered.connect(self.toggle_italic)

        bullet_action = QAction("• List", self)
        bullet_action.triggered.connect(self.toggle_bullet_list)

        self.note_toolbar.addAction(bold_action)
        self.note_toolbar.addAction(italic_action)
        self.note_toolbar.addAction(bullet_action)

        right_layout.addWidget(self.note_toolbar)

        # DATE INPUT (create first)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setFixedWidth(200)

        # YEAR + DATE + THEME (Single Row)
        top_row = QHBoxLayout()

        self.year_box = QComboBox()
        for y in range(2020, 2036):
            self.year_box.addItem(str(y))

        self.year_box.setCurrentText(self.current_year)
        self.year_box.setFixedWidth(120)

        self.theme_btn = QPushButton("Switch Theme")
        self.theme_btn.setFixedWidth(180)

        top_row.addWidget(QLabel("Year"))
        top_row.addWidget(self.year_box)

        top_row.addWidget(QLabel("Date"))
        top_row.addWidget(self.date_input)

        top_row.addWidget(self.theme_btn)

        right_layout.addLayout(top_row)

        # FORM
        self.form = QFormLayout()

        self.item_input = QLineEdit()
        self.note_input = QTextEdit()
        self.note_input.setMinimumHeight(120)
        self.note_input.setSizePolicy(self.note_input.sizePolicy().horizontalPolicy(), QSizePolicy.Expanding)

        # LOAN INPUT FIELDS
        self.loan_amount_input = QLineEdit()
        self.loan_amount_input.setValidator(QDoubleValidator(0, 999999999, 2))

        self.interest_input = QLineEdit()
        self.interest_input.setValidator(QDoubleValidator(0, 100, 2))

        self.installment_input = QLineEdit()
        self.installment_input.setValidator(QDoubleValidator(0, 9999, 0))

        self.loan_start_date = QDateEdit()
        self.loan_start_date.setCalendarPopup(True)
        self.loan_start_date.setDate(QDate.currentDate())

        validator = QDoubleValidator(0, 999999999, 2)

        self.inward_input = QLineEdit()
        self.inward_input.setValidator(validator)

        self.outward_input = QLineEdit()
        self.outward_input.setValidator(validator)


        self.item_row_label = QLabel("Item / Person")
        self.note_row_label = QLabel("Note")

        self.form.addRow(self.item_row_label, self.item_input)
        self.form.addRow(self.note_row_label, self.note_input)

        # LOAN FORM ROWS
        self.loan_amount_label = QLabel("Loan Amount")
        self.interest_label = QLabel("Interest %")
        self.installment_label = QLabel("Installments")
        self.start_date_label = QLabel("Start Date")

        self.form.addRow(self.loan_amount_label, self.loan_amount_input)
        self.form.addRow(self.interest_label, self.interest_input)
        self.form.addRow(self.installment_label, self.installment_input)
        self.form.addRow(self.start_date_label, self.loan_start_date)

        self.note_row = self.form.rowCount() - 1

        self.money_row = QHBoxLayout()

        self.money_row.addWidget(QLabel("Inward / Amount"))
        self.money_row.addWidget(self.inward_input)
        self.money_row.addWidget(QLabel("Outward"))
        self.money_row.addWidget(self.outward_input)

        self.form.addRow(self.money_row)

        right_layout.addLayout(self.form)

        # BUTTONS
        btn_row = QHBoxLayout()

        self.add_btn = QPushButton("Add")
        self.pay_btn = QPushButton("Pay Installment")
        self.del_btn = QPushButton("Delete")
        self.export_btn = QPushButton("Export")
        self.backup_btn = QPushButton("Backup")
        self.restore_btn = QPushButton("Restore")
        self.report_btn = QPushButton("Report")

        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.pay_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.backup_btn)
        btn_row.addWidget(self.restore_btn)
        btn_row.addWidget(self.report_btn) 

        right_layout.addLayout(btn_row)

        #MONTH INDICATOR
        months = ["Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]

        self.month_label = QLabel(f"Month: {months[self.current_month-1]}")
        self.month_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.month_label)


        self.month_label.setAlignment(Qt.AlignCenter)
    
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
        self.summary_layout = QHBoxLayout()

        self.opening = QLabel("Opening: 0")
        self.income = QLabel("Income: 0")
        self.expense = QLabel("Expense: 0")
        self.closing = QLabel("Closing: 0")
        self.forward = QLabel("Forward: 0")

        for w in [self.opening, self.income, self.expense, self.closing, self.forward]:
            w.setAlignment(Qt.AlignCenter)
            self.summary_layout.addWidget(w)

        right_layout.addLayout(self.summary_layout)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        main_layout.addWidget(right_widget, 4)

        self.form.setRowVisible(self.loan_amount_label, False)
        self.form.setRowVisible(self.interest_label, False)
        self.form.setRowVisible(self.installment_label, False)
        self.form.setRowVisible(self.start_date_label, False)

        # SIGNALS
        add_cat_btn.clicked.connect(self.add_category)
        del_cat_btn.clicked.connect(self.delete_category)

        self.category_list.itemClicked.connect(self.open_category)
        self.category_list.itemDoubleClicked.connect(self.deselect_category)

        self.add_btn.clicked.connect(self.add_transaction)
        self.pay_btn.clicked.connect(self.pay_installment)
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
   
    def toggle_bullet_list(self):
        cursor = self.note_input.textCursor()

        if cursor.currentList():
            cursor.createList(QTextListFormat.ListDisc)
        else:
            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.ListDisc)
            cursor.createList(fmt)
   
    def toggle_italic(self):
        cursor = self.note_input.textCursor()
        fmt = QTextCharFormat()

        fmt.setFontItalic(not cursor.charFormat().fontItalic())
        cursor.mergeCharFormat(fmt)
    
    
    def toggle_bold(self):
        cursor = self.note_input.textCursor()
        fmt = QTextCharFormat()

        if cursor.charFormat().fontWeight() == QFont.Bold:
            fmt.setFontWeight(QFont.Normal)
        else:
            fmt.setFontWeight(QFont.Bold)

        cursor.mergeCharFormat(fmt)
    # =========================
    # CATEGORY
    # =========================
    def load_categories(self):

        self.category_list.clear()

        rows = self.cursor.execute(
            "SELECT name, type, subtype FROM categories"
        )

        for name, typ, subtype in rows:

            if typ.lower() == "ledger":
                display = f"{name} (Ledger)"

            elif typ.lower() == "note":
                display = f"{name} ({subtype})"

            else:
                display = name

            self.category_list.addItem(display)

    def add_category(self):

        name, ok = QInputDialog.getText(self, "Create Category", "Category Name:")

        if not ok or not name.strip():
            return

        category_type, ok = QInputDialog.getItem(
            self,
            "Category Type",
            "Choose category type:",
            ["Ledger (Income / Expense)", "Note (Money Lending)"],
            0,
            False
        )

        if not ok:
            return

        if category_type.startswith("Ledger"):
            ctype = "ledger"
        else:
            ctype = "note"

        note_subtype = None

        if ctype == "note":

            note_subtype, ok = QInputDialog.getItem(
                self,
                "Note Category Type",
                "Select note category type:",
                [
                    "Simple Note",
                    "Loan",
                    "Lended Money",
                    "Borrowed Money"
                ],
                0,
                False
            )

            if not ok:
                return    

       
        try:

            self.cursor.execute(
                "INSERT INTO categories (name,type,subtype) VALUES (?,?,?)",
                (name, ctype, note_subtype)
            )

            self.db.commit()

            if ctype == "ledger":
               display = f"{name} (Ledger)"
            elif ctype == "note":
               display = f"{name} ({note_subtype})"
            else:
               display = name

            self.category_list.addItem(display)
        

            # auto select the newly created category
            self.category_list.setCurrentRow(self.category_list.count() - 1)

        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Duplicate", "Category already exists")

    def delete_category(self):

        item = self.category_list.currentItem()

        if not item:
            return

        name = item.text().split(" (")[0]

        self.cursor.execute("DELETE FROM categories WHERE name=?", (name,))
        self.cursor.execute("DELETE FROM transactions WHERE category=?", (name,))
        self.cursor.execute("DELETE FROM notes WHERE category=?", (name,))

        self.db.commit()

        self.load_categories()

        # reset UI state
        self.current_category = None
        self.table.setRowCount(0)

        # reset dashboard cards
        self.balance_card.setText("Balance\n0")
        self.income_card.setText("Income\n0")
        self.expense_card.setText("Expense\n0")

        # reset summary panel
        self.opening.setText("Opening: 0")
        self.income.setText("Income: 0")
        self.expense.setText("Expense: 0")
        self.closing.setText("Closing: 0")
        self.forward.setText("Forward: 0")

    # =========================
    # OPEN CATEGORY
    # =========================
    def open_category(self, item):

        name = item.text().split(" (")[0]

        row = self.cursor.execute(
            "SELECT type,subtype FROM categories WHERE name=?",
            (name,)
        ).fetchone()

        if not row:
            return

        typ, subtype = row


        self.current_subtype = subtype
        self.current_category = name
        self.current_type = typ

        # UI SWITCHING SYSTEM
        if self.current_type == "ledger":
            self.load_ledger_ui()

        elif self.current_subtype == "Simple Note":
            self.load_simple_note_ui()

        elif self.current_subtype == "Loan":
            self.load_loan_ui()

        elif self.current_subtype == "Lended Money":
            self.load_lended_ui()

        elif self.current_subtype == "Borrowed Money":
            self.load_borrowed_ui()

        if self.current_subtype == "Loan":
            self.load_loans()

        elif self.current_subtype == "Simple Note":
            self.load_notes()

        else:
            self.load_table()

    # =========================
    # LEDGER UI
    # =========================     

    def load_ledger_ui(self):

        self.month_label.show()

        for btn in self.month_buttons:
            btn.show()

        self.item_row_label.setText("Item / Person")
        self.pay_btn.hide()
        self.note_toolbar.hide()
        self.form.setRowVisible(self.loan_amount_label, False)
        self.form.setRowVisible(self.interest_label, False)
        self.form.setRowVisible(self.installment_label, False)
        self.form.setRowVisible(self.start_date_label, False)

        # show item row
        self.form.setRowVisible(self.item_row_label, True)

        # hide note row
        self.form.setRowVisible(self.note_row_label, False)

        self.inward_input.show()
        self.outward_input.show()

        for i in range(self.money_row.count()):
            widget = self.money_row.itemAt(i).widget()
            if widget:
                widget.show()

        for i in range(self.cards_layout.count()):
            self.cards_layout.itemAt(i).widget().show()

        for i in range(self.summary_layout.count()):
            self.summary_layout.itemAt(i).widget().show()

        self.setup_ledger_table()
    # =========================
    # SIMPLE NOTe UI
    # =========================  
    def load_simple_note_ui(self):

        self.month_label.hide()

        for btn in self.month_buttons:
            btn.hide()

        self.pay_btn.hide()
        self.note_toolbar.show()
        self.form.setRowVisible(self.loan_amount_label, False)
        self.form.setRowVisible(self.interest_label, False)
        self.form.setRowVisible(self.installment_label, False)
        self.form.setRowVisible(self.start_date_label, False)

        # hide item row
        self.form.setRowVisible(self.item_row_label, False)

        # show note row
        self.form.setRowVisible(self.note_row_label, True)

        self.inward_input.hide()
        self.outward_input.hide()

        for i in range(self.money_row.count()):
            widget = self.money_row.itemAt(i).widget()
            if widget:
                widget.hide()

        for i in range(self.cards_layout.count()):
            self.cards_layout.itemAt(i).widget().hide()

        for i in range(self.summary_layout.count()):
            self.summary_layout.itemAt(i).widget().hide()

        self.setup_simple_note_table()

    

    # =========================
    # LOAN UI
    # ========================= 
    def load_loan_ui(self):

        self.month_label.hide()

        for btn in self.month_buttons:
            btn.hide()
        self.pay_btn.show()

        # show cards
        for i in range(self.cards_layout.count()):
            self.cards_layout.itemAt(i).widget().show()

        # rename cards for loan
        self.balance_card.setText("Total Loan\n0")
        self.income_card.setText("Cleared\n0")
        self.expense_card.setText("Remaining\n0")

        # hide note editor and toolbar
        self.note_input.hide()
        self.note_toolbar.hide()

        # show person field
        self.form.setRowVisible(self.item_row_label, True)
        self.item_row_label.setText("Loan Name")

        # show loan fields
        self.form.setRowVisible(self.loan_amount_label, True)
        self.form.setRowVisible(self.interest_label, True)
        self.form.setRowVisible(self.installment_label, True)
        self.form.setRowVisible(self.start_date_label, True)

        # hide note row
        self.form.setRowVisible(self.note_row_label, False)

        # hide ledger money fields
        for i in range(self.money_row.count()):
            widget = self.money_row.itemAt(i).widget()
            if widget:
                widget.hide()

        # hide ledger summary panel
        for i in range(self.summary_layout.count()):
            self.summary_layout.itemAt(i).widget().hide()

        # configure loan table
        self.setup_loan_table()

        # load loans from database
        self.load_loans()   

    def calculate_emi(self, principal, interest, months):

        if months == 0:
            return 0

        r = (interest / 100) / 12

        if r == 0:
            return round(principal / months, 2)

        emi = principal * r * (1 + r) ** months
        emi = emi / ((1 + r) ** months - 1)

        return round(emi, 2)    
    
    # =========================
    # LENDED MONEY UI
    # =========================
    def load_lended_ui(self):

        for i in range(self.cards_layout.count()):
            self.cards_layout.itemAt(i).widget().hide()

        for i in range(self.summary_layout.count()):
            self.summary_layout.itemAt(i).widget().hide()

        self.setup_lended_table()
    # =========================
    # BORROWED UI
    # =========================
    def load_borrowed_ui(self):

        for i in range(self.cards_layout.count()):
            self.cards_layout.itemAt(i).widget().hide()

        for i in range(self.summary_layout.count()):
            self.summary_layout.itemAt(i).widget().hide()

        self.setup_borrowed_table()
    # =========================
    # TABEL SETUP
    # =========================

    def setup_ledger_table(self):

        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels(
            ["ID","Date","Item","Inward","Outward","Balance"]
        )

        self.table.setColumnHidden(0, True)
    
    def setup_simple_note_table(self):

        self.table.setColumnCount(3)

        self.table.setHorizontalHeaderLabels(
            ["ID","Date","Note"]
        )

        self.table.setColumnHidden(0, True)       

    def setup_loan_table(self):

        self.table.setColumnCount(9)

        self.table.setHorizontalHeaderLabels(
            ["ID","Date","Loan Name","Loan Amount","EMI","Cleared","Remaining","Next Installment","Progress"]
        )

        self.table.setColumnHidden(0, True)

    def setup_lended_table(self):

        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels(
            ["ID","Date","Person","Amount Given","Return Date","Status"]
        )

        self.table.setColumnHidden(0, True)

    def setup_borrowed_table(self):

        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels(
            ["ID","Date","Person","Amount Borrowed","Return Date","Status"]
        )

        self.table.setColumnHidden(0, True)
    # =========================
    # DISSELECT CATEGORY
    # ========================= 
    def deselect_category(self):

        self.category_list.clearSelection()

        self.current_category = None

        # clear table
        self.table.setRowCount(0)

        # reset dashboard
        self.balance_card.setText("Balance\n0")
        self.income_card.setText("Income\n0")
        self.expense_card.setText("Expense\n0")

        # reset summary
        self.opening.setText("Opening: 0")
        self.income.setText("Income: 0")
        self.expense.setText("Expense: 0")
        self.closing.setText("Closing: 0")
        self.forward.setText("Forward: 0")     

    # =========================
    # CHANGE MONTH
    # =========================
    def change_month(self, m):

        self.current_month = m

        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]

        # update month label
        self.month_label.setText(f"Month: {months[m-1]}")

        # get current date from date picker
        current_date = self.date_input.date()

        # change only the month (keep day and year)
        new_date = QDate(current_date.year(), m, current_date.day())

        # update the date picker
        self.date_input.setDate(new_date)

        # reload table
        self.load_table()

    # =========================
    # opning balace
    # =========================

    def get_opening_balance(self):

        if not self.current_category:
            return 0

        rows = self.cursor.execute("""
            SELECT inward, outward
            FROM transactions
            WHERE category=? AND date < ?
        """, (self.current_category,
              f"{self.current_year}-{self.current_month:02d}-01"))

        opening = 0

        for r in rows:
            opening += r[0] - r[1]

        return opening


    # =========================
    # TABLE
    # =========================
    def load_table(self):

        self.table.setRowCount(0)

        if not self.current_category:
            return

        rows = list(self.cursor.execute("""
           SELECT id,date,item,inward,outward
           FROM transactions
           WHERE category=? 
           AND strftime('%m',date)=?
           AND strftime('%Y',date)=?
           ORDER BY date ASC, id ASC                             
           """, (self.current_category, f"{self.current_month:02d}", self.current_year)))

        balance = self.get_opening_balance()

        for r in rows:

            rid, date, item, inw, outw = r

            balance += inw - outw

            row = self.table.rowCount()
            self.table.insertRow(row)

            id_item = QTableWidgetItem(str(rid))
            date_item = QTableWidgetItem(date)
            item_item = QTableWidgetItem(item)
            inw_item = QTableWidgetItem(str(inw))
            outw_item = QTableWidgetItem(str(outw))
            bal_item = QTableWidgetItem(str(balance))

            id_item.setTextAlignment(Qt.AlignCenter)
            date_item.setTextAlignment(Qt.AlignCenter)
            item_item.setTextAlignment(Qt.AlignCenter)
            inw_item.setTextAlignment(Qt.AlignCenter)
            outw_item.setTextAlignment(Qt.AlignCenter)
            bal_item.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, date_item)
            self.table.setItem(row, 2, item_item)
            self.table.setItem(row, 3, inw_item)
            self.table.setItem(row, 4, outw_item)
            self.table.setItem(row, 5, bal_item)
    
        self.update_summary()


    def load_loans(self):

        self.table.setRowCount(0)

        total_loan = 0
        total_cleared = 0
        total_remaining = 0


        rows = self.cursor.execute("""
        SELECT id,start_date,person,loan_amount,interest,installments,emi,remaining,status
        FROM loans
        WHERE category=?
        """,(self.current_category,))

        for loan in rows:

            loan_id, date, person, loan_amount, interest, installments, emi, remaining, status = loan
            paid_count = self.cursor.execute(
                "SELECT COUNT(*) FROM loan_payments WHERE loan_id=?",
                (loan_id,)
            ).fetchone()[0]
            
            cleared = loan_amount - remaining

            total_loan += loan_amount
            total_cleared += cleared
            total_remaining += remaining

            if remaining <= 0:
                status = "Completed"
            elif cleared > 0:
                status = "Running"
            else:
                status = "Active"

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row,0,QTableWidgetItem(str(loan_id)))
            self.table.setItem(row,1,QTableWidgetItem(date))
            self.table.setItem(row,2,QTableWidgetItem(person))
            self.table.setItem(row,3,QTableWidgetItem(str(loan_amount)))
            self.table.setItem(row,4,QTableWidgetItem(str(emi)))
            self.table.setItem(row,5,QTableWidgetItem(str(cleared)))
            self.table.setItem(row,6,QTableWidgetItem(str(remaining)))
            
            start_qdate = QDate.fromString(date, "yyyy-MM-dd")
            next_date = start_qdate.addMonths(paid_count + 1)

            if remaining <= 0:
                next_installment = "Completed"
            else:
                next_installment = next_date.toString("dd MMM yyyy")

            self.table.setItem(row,7,QTableWidgetItem(next_installment))
            progress = 0
            if loan_amount > 0:
                progress = int((cleared / loan_amount) * 100)

            bar = QProgressBar()
            bar.setValue(progress)

            self.table.setCellWidget(row,8,bar)

        self.balance_card.setText(f"Total Loan\n{total_loan}")
        self.income_card.setText(f"Cleared\n{total_cleared}")
        self.expense_card.setText(f"Remaining\n{total_remaining}")

    def load_notes(self):

        self.table.setRowCount(0)

        rows = self.cursor.execute("""
        SELECT id,date,person
        FROM notes
        WHERE category=?
        ORDER BY date DESC
        """,(self.current_category,))

        for rid, date, note in rows:

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row,0,QTableWidgetItem(str(rid)))
            self.table.setItem(row,1,QTableWidgetItem(date))
            self.table.setItem(row,2,QTableWidgetItem(note))    


    def pay_installment(self):

        row = self.table.currentRow()

        if row < 0:
            return

        loan_id = int(self.table.item(row,0).text())

        amount, ok = QInputDialog.getDouble(self,"Installment","Payment amount")

        if not ok:
            return

        today = QDate.currentDate().toString("yyyy-MM-dd")

        self.cursor.execute("""
        INSERT INTO loan_payments(loan_id,payment_date,amount)
        VALUES(?,?,?)
        """,(loan_id,today,amount))

        self.cursor.execute("""
        UPDATE loans
        SET remaining = CASE 
            WHEN remaining - ? < 0 THEN 0
            ELSE remaining - ?
        END        
        WHERE id=?
        """,(amount,amount,loan_id))
        self.db.commit()

        self.load_loans()     


    
    # =========================
    # UPDATE SUMMARY
    # =========================
    def update_summary(self):

        if self.current_subtype == "Loan":
            return

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

        for r in rows:
            income += r[0]
            expense += r[1]

        opening = self.get_opening_balance()
        balance = opening + income - expense

        # Dashboard cards
        self.balance_card.setText(f"Balance\n{balance}")
        self.income_card.setText(f"Income\n{income}")
        self.expense_card.setText(f"Expense\n{expense}")

        # Bottom summary
        opening = self.get_opening_balance()
        self.opening.setText(f"Opening: {opening}")
        self.income.setText(f"Income: {income}")
        self.expense.setText(f"Expense: {expense}")
        self.closing.setText(f"Closing: {balance}")
        self.forward.setText(f"Forward: {balance}")

    # =========================
    # ADD
    # =========================
    def add_transaction(self):
        
        if self.current_subtype == "Loan":

         person = self.item_input.text().strip()
         amount = float(self.loan_amount_input.text() or 0)
         interest = float(self.interest_input.text() or 0)
         months = int(float(self.installment_input.text() or 0))
         start_date = self.loan_start_date.date().toString("yyyy-MM-dd")

         if not person or amount <= 0:
             QMessageBox.warning(self, "Loan", "Enter person and loan amount")
             return

         emi = self.calculate_emi(amount, interest, months)

         self.cursor.execute("""
         INSERT INTO loans(category,person,loan_amount,interest,installments,emi,start_date,remaining,status)
         VALUES(?,?,?,?,?,?,?,?,?)
         """,(
             self.current_category,
             person,
             amount,
             interest,
             months,
             emi,
             start_date,
             amount,
             "Active"
         ))

         self.db.commit()

         self.load_loans()

         self.item_input.clear()
         self.loan_amount_input.clear()
         self.interest_input.clear()
         self.installment_input.clear()
         return


        if self.current_subtype == "Simple Note":

            note_text = self.note_input.toPlainText().strip()
            date = self.date_input.date().toString("yyyy-MM-dd")

            if not note_text:
                QMessageBox.warning(self, "Note", "Enter a note")
                return

            self.cursor.execute("""
            INSERT INTO notes(category,date,person,amount,return_date,status)
            VALUES(?,?,?,?,?,?)
            """, (
                self.current_category,
                date,
                note_text,
                0,
                "",
                ""
            ))

            self.db.commit()

            self.load_notes()

            self.note_input.clear()

            return


        if not self.current_category:
            return

        date = self.date_input.date().toString("yyyy-MM-dd")
        item = self.item_input.text()

        inward_text = self.inward_input.text().strip() 
        outward_text = self.outward_input.text().strip()

        # validation: both empty
        if not inward_text and not outward_text:
            QMessageBox.warning(self, "Invalid Entry", "Enter amount in Inward or Outward.")
            return

        inward = float(inward_text or 0)
        outward = float(outward_text or 0)

        self.cursor.execute("""
        INSERT INTO transactions(category,date,item,inward,outward)
        VALUES(?,?,?,?,?)
        """, (self.current_category, date, item, inward, outward))

        self.db.commit()

        self.load_table()

        # reset form
        self.item_input.clear()
        self.inward_input.clear()
        self.outward_input.clear()
        self.date_input.setDate(QDate.currentDate())

        

    # =========================
    # DELETE
    # =========================
    def delete_transaction(self):

        row = self.table.currentRow()

        if row < 0:
            return

        tid = int(self.table.item(row, 0).text())

         # Handle loan deletion
        if self.current_subtype == "Loan":

            self.cursor.execute("DELETE FROM loans WHERE id=?", (tid,))
            self.cursor.execute("DELETE FROM loan_payments WHERE loan_id=?", (tid,))
            self.db.commit()

            self.load_loans()
            return

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
