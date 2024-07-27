import sqlite3
from datetime import datetime
import logging
from contextlib import contextmanager

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UserFileManager:
    def __init__(self):
        self.user_files = {}
        logger.debug("UserFileManager initialized")

    def add_user_files(self, user_id, file_list):
        self.user_files[user_id] = file_list
        logger.debug(f"Files added for user {user_id}: {file_list}")

    def get_user_files(self, user_id):
        files = self.user_files.get(user_id, [])
        logger.debug(f"Retrieved files for user {user_id}: {files}")
        return files

    def add_file_to_user(self, user_id, filename):
        if user_id not in self.user_files:
            self.user_files[user_id] = []
        self.user_files[user_id].append(filename)
        logger.debug(f"File {filename} added for user {user_id}")

class BankCRM:
    def __init__(self, db_path='bank_crm.db'):
        self.db_path = db_path
        self.file_manager = UserFileManager()
        logger.debug(f"BankCRM initialized with database: {db_path}")
        self.create_tables()

    @contextmanager
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def create_tables(self):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    credit_score INTEGER,
                    account_balance REAL,
                    last_login DATETIME,
                    password_hash TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    product_name TEXT,
                    FOREIGN KEY (user_id) REFERENCES customers (user_id)
                )
            ''')
            conn.commit()
        logger.debug("Database tables created")

    def add_customer(self, user_id, name, credit_score, account_balance, password_hash):
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO customers (user_id, name, credit_score, account_balance, last_login, password_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, name, credit_score, account_balance, datetime.now(), password_hash))
                conn.commit()
            
            self.add_product(user_id, "savings_account")
            
            if credit_score >= 650:
                self.add_product(user_id, "credit_card")
                logger.info(f"Credit card automatically added for {user_id} due to good credit score.")
            else:
                logger.info(f"{user_id} is not eligible for a credit card due to low credit score.")
            
            logger.debug(f"Customer {user_id} added successfully")
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"IntegrityError adding customer {user_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding customer {user_id}: {str(e)}")
            return False
        
    def get_password_hash(self, user_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash FROM customers WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
        logger.debug(f"Retrieved password hash for user {user_id}")
        return result[0] if result else None

    def add_product(self, user_id, product_name):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (user_id, product_name)
                VALUES (?, ?)
            ''', (user_id, product_name))
            conn.commit()
        logger.debug(f"Product {product_name} added for user {user_id}")

    def get_user_info(self, user_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.user_id, c.name, c.credit_score, c.account_balance, c.last_login,
                       GROUP_CONCAT(p.product_name, ', ') as products
                FROM customers c
                LEFT JOIN products p ON c.user_id = p.user_id
                WHERE c.user_id = ?
                GROUP BY c.user_id
            ''', (user_id,))
            result = cursor.fetchone()
        
        if result:
            user_info = {
                'user_id': result[0],
                'name': result[1],
                'credit_score': result[2],
                'account_balance': result[3],
                'last_login': result[4],
                'products': result[5].split(', ') if result[5] else []
            }
            logger.debug(f"Retrieved user info for {user_id}")
            return user_info
        logger.debug(f"No user info found for {user_id}")
        return None

    def update_last_login(self, user_id):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE customers
                SET last_login = ?
                WHERE user_id = ?
            ''', (datetime.now(), user_id))
            conn.commit()
        logger.debug(f"Updated last login for user {user_id}")

    def add_file_to_user(self, user_id, filename):
        self.file_manager.add_file_to_user(user_id, filename)
        logger.debug(f"File {filename} added for user {user_id}")

    def get_user_files(self, user_id):
        files = self.file_manager.get_user_files(user_id)
        logger.debug(f"Retrieved files for user {user_id}: {files}")
        return files

    # No need for close() or __del__() methods anymore