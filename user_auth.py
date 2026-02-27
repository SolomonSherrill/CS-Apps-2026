import psycopg2
import os
from dotenv import load_dotenv
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
class user_auth:
    def __init__(self):
        load_dotenv()
        db_url = os.getenv("SUPABASE_URL")
        if not db_url:
            raise ValueError("SUPABASE_URL not found in environment variables.")
        self.conn = psycopg2.connect(db_url)
        self.cur = self.conn.cursor() 
    def hash_password(self, password):
        ph = PasswordHasher()
        return ph.hash(password)
    def create_user(self, username, password):
        hashed_password = self.hash_password(password)
        try:
            self.cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            self.conn.commit()
            return {"success": True}
        except psycopg2.errors.UniqueViolation:
            self.conn.rollback()
            return {"success": False, "error": "Username already exists."}
    def authenticate_user(self, username, password) -> bool:
        self.cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        userData = self.cur.fetchone()
        ph = PasswordHasher()
        if not userData:
            try:
                ph.verify("fakehash", password)
            except:
                pass
            return False
        hashed_password = userData[2]
        try:
            ph.verify(hashed_password, password)
            if ph.check_needs_rehash(hashed_password):
                new_hash = ph.hash(password)
                self.cur.execute("UPDATE users SET password = %s WHERE username = %s", (new_hash, username))
                self.conn.commit()
            return {"success": True} 
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return {"success": False, "error": "Invalid username or password"}