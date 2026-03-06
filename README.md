# Expense Tracker (PySide6 Desktop Application)

## Overview
**Expense Tracker** is a desktop application built using **Python and PySide6** that helps users manage their finances by tracking income, expenses, and money lending records.

The application provides a clean **ledger-style interface**, supports **multiple categories**, includes **monthly transaction views**, and allows **secure hidden categories protected by passwords**.

All data is stored locally using **SQLite**, allowing the application to work **completely offline** without requiring internet access.

---

# Features

## Category Management
- Create unlimited categories for different purposes (personal, business, etc.)
- Three category types available:
  - **Ledger (Income / Expense)** – for standard financial tracking
  - **Note (Money Lending)** – track money lent to others and repayment
  - **Hidden (Password Protected)** – secure category protected with a password
- Delete categories along with all associated data.

---

## Transaction Tracking
Users can record:

- **Date**
- **Item / Person**
- **Inward (Income / Amount Received)**
- **Outward (Expense / Amount Given)**

Transactions are stored in a **SQLite database** and automatically displayed in the ledger table.

---

## Monthly Ledger View
Transactions are organized by **months**.

Users can switch between months using the **Jan–Dec buttons** to view monthly financial records.

---

## Financial Dashboard
The application displays real-time financial summaries:

- **Balance**
- **Total Income**
- **Total Expense**

These values update automatically when new transactions are added.

---

## Search System
A built-in **search bar** allows users to quickly filter transactions by item or person name.

The ledger table updates dynamically based on the search input.

---

## Export Data
Users can export category transaction data as a **CSV file**.

Exported fields include:

- Date
- Item
- Inward
- Outward

This allows easy import into **Excel, Google Sheets, or accounting tools**.

---

## Dark Theme Support
The application includes two visual themes:

- **Modern Indigo Theme**
- **Minimal Dark Theme**

Users can toggle themes using the **Switch Theme** button.

---

# Technologies Used

| Technology | Purpose |
|------------|--------|
| Python | Core programming language |
| PySide6 | Desktop GUI framework |
| SQLite | Local database storage |
| hashlib (SHA256) | Password security |
| CSV module | Data export |

---

# Database Structure

The application automatically creates three tables.

### Categories Table

```
categories
-------------------------
name TEXT (PRIMARY KEY)

```

### Transactions Table

```
transactions
-------------------------
id INTEGER PRIMARY KEY
category TEXT
date TEXT
item TEXT
inward REAL
outward REAL
```


---

# Installation

## Requirements

Python **3.9 or higher**

Install required library:

```
pip install PySide6
```

---

# Run the Application

Navigate to the project folder and run:

```
python main.py
```

---

# Convert to Windows Application

You can convert this Python app into a standalone Windows executable.

Install PyInstaller:

```
pip install pyinstaller
```

Build the executable:

```
pyinstaller --onefile --windowed main.py
```

The executable will be generated in:

```
dist/main.exe
```

You can rename it to:

```
ExpenseTracker.exe
```

---

# Project Structure

```
ExpenseTracker
│
├── main.py
├── expense_data.db
├── icon.ico
└── README.md
```



# Future Improvements

Possible enhancements include:

- Monthly balance carry-forward
- Financial analytics dashboard
- Automatic loan repayment reminders
- Database backup & restore system
- Windows installer package

---

# Author

**Jenil Sabhaya**

---

# License

This project is provided for **educational and personal use**.