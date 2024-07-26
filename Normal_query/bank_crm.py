import sqlite3
from datetime import datetime

class UserFileManager:
    def __init__(self):
        self.user_files = {}

    def add_user_files(self, user_id, file_list):
        self.user_files[user_id] = file_list

    def get_user_files(self, user_id):
        return self.user_files.get(user_id, [])

    def add_file_to_user(self, user_id, filename):
        if user_id not in self.user_files:
            self.user_files[user_id] = []
        self.user_files[user_id].append(filename)

class BankCRM:
    def __init__(self, db_path='bank_crm.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.file_manager = UserFileManager()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                credit_score INTEGER,
                account_balance REAL,
                last_login DATETIME,
                password_hash TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                user_id TEXT,
                product_name TEXT,
                FOREIGN KEY (user_id) REFERENCES customers (user_id)
            )
        ''')
        self.conn.commit()

    def add_customer(self, user_id, name, credit_score, account_balance, password_hash):
        try:
            self.cursor.execute('''
                INSERT INTO customers (user_id, name, credit_score, account_balance, last_login, password_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, credit_score, account_balance, datetime.now(), password_hash))
            self.conn.commit()
            self.add_product(user_id, "savings_account")
            
            if credit_score >= 650:
                self.add_product(user_id, "credit_card")
                print(f"Credit card automatically added for {user_id} due to good credit score.")
            else:
                print(f"{user_id} is not eligible for a credit card due to low credit score.")
            
            return True
        except sqlite3.IntegrityError as e:
            print(f"IntegrityError: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error in add_customer: {str(e)}")
            return False
        
    def get_password_hash(self, user_id):
        self.cursor.execute('SELECT password_hash FROM customers WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_product(self, user_id, product_name):
        self.cursor.execute('''
            INSERT INTO products (user_id, product_name)
            VALUES (?, ?)
        ''', (user_id, product_name))
        self.conn.commit()

    def get_user_info(self, user_id):
        self.cursor.execute('''
            SELECT c.user_id, c.name, c.credit_score, c.account_balance, c.last_login,
                   GROUP_CONCAT(p.product_name, ', ') as products
            FROM customers c
            LEFT JOIN products p ON c.user_id = p.user_id
            WHERE c.user_id = ?
            GROUP BY c.user_id
        ''', (user_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'user_id': result[0],
                'name': result[1],
                'credit_score': result[2],
                'account_balance': result[3],
                'last_login': result[4],
                'products': result[5].split(', ') if result[5] else []
            }
        return None

    def update_last_login(self, user_id):
        self.cursor.execute('''
            UPDATE customers
            SET last_login = ?
            WHERE user_id = ?
        ''', (datetime.now(), user_id))
        self.conn.commit()

    def add_file_to_user(self, user_id, filename):
        self.file_manager.add_file_to_user(user_id, filename)

    def get_user_files(self, user_id):
        return self.file_manager.get_user_files(user_id)

    def close(self):
        self.conn.close()