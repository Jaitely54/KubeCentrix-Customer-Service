import hashlib

class UserAuth:
    def __init__(self, crm):
        self.crm = crm
        self.salt = b'fixed_salt_for_all_users'  # Use a fixed salt for simplicity

    def authenticate_user(self, user_id, password):
        stored_hash = self.crm.get_password_hash(user_id)
        if stored_hash:
            return self._verify_password(stored_hash, password)
        return False

    def create_user(self, user_id, password, name, credit_score, account_balance):
        try:
            hashed_password = self._hash_password(password)
            if self.crm.add_customer(user_id, name, credit_score, account_balance, hashed_password):
                return True
            else:
                print("CRM failed to add customer.")
                return False
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return False

    def _hash_password(self, password):
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), self.salt, 100000).hex()

    def _verify_password(self, stored_password, provided_password):
        return stored_password == self._hash_password(provided_password)