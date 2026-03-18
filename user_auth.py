import psycopg2
import os
from datetime import datetime, timedelta
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
    def connect(self):
        self.conn = psycopg2.connect(os.getenv("SUPABASE_URL"))
        self.cur = self.conn.cursor()
    def hash_password(self, password):
        ph = PasswordHasher()
        return ph.hash(password)
    def change_password(self, username, old_password, new_password):
        lowercase_letters = "abcdefghijklmnopqrstuvwxyz"
        uppercase_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits = "0123456789"
        special_characters = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
        if len(new_password) < 10:
            return {"success": False, "error": "Password must be at least 10 characters long."}
        if not any(c in lowercase_letters for c in new_password):
            return {"success": False, "error": "Password must contain at least one lowercase letter."}
        if not any(c in uppercase_letters for c in new_password):
            return {"success": False, "error": "Password must contain at least one uppercase letter."}
        if not any(c in digits for c in new_password):
            return {"success": False, "error": "Password must contain at least one digit."}
        if not any(c in special_characters for c in new_password):
            return {"success": False, "error": "Password must contain at least one special character."}
        self.connect()
        try:
            self.cur.execute("SELECT password FROM users WHERE username = %s", (username,))
            row = self.cur.fetchone()
            if not row:
                return {"success": False, "error": "User not found."}
            passHash = row[0]
            ph = PasswordHasher()
            ph.verify(passHash, old_password)
            newHash = ph.hash(new_password)
            self.cur.execute("UPDATE users SET password = %s WHERE username = %s", (newHash, username))
            self.conn.commit()
            return {"success": True}
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return {"success": False, "error": "Old password is incorrect."}
        finally:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
    def create_user(self, username, password, invite_code=None):
        lowercase_letters = "abcdefghijklmnopqrstuvwxyz"
        uppercase_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits = "0123456789"
        special_characters = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
        if len(password) < 10:
            return {"success": False, "error": "Password must be at least 10 characters long."}
        if not any(c in lowercase_letters for c in password):
            return {"success": False, "error": "Password must contain at least one lowercase letter."}
        if not any(c in uppercase_letters for c in password):
            return {"success": False, "error": "Password must contain at least one uppercase letter."}
        if not any(c in digits for c in password):
            return {"success": False, "error": "Password must contain at least one digit."}
        if not any(c in special_characters for c in password):
            return {"success": False, "error": "Password must contain at least one special character."}
        if invite_code == os.getenv("BASIC_CODE"):
            role = "basic"
        elif invite_code == os.getenv("ADMIN_CODE"):
            role = "admin"
        elif invite_code is None:
            return {"success": False, "error": "Invite code is required."}
        else:            
            return {"success": False, "error": "Invalid invite code."}
        hashed_password = self.hash_password(password)
        try:
            self.connect()
            self.cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password, role))
            self.conn.commit()
            return {"success": True}
        except psycopg2.errors.UniqueViolation:
            self.conn.rollback()
            return {"success": False, "error": "Username already exists."}
        finally:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
    def authenticate_user(self, username, password) -> bool:
        try:
            self.connect()
            self.cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            userData = self.cur.fetchone()
            ph = PasswordHasher()
            if not userData:
                try:
                    ph.verify("fakehash", password)
                except:
                    pass
                return {"success": False, "error": "Invalid username or password"}
            locked_until = userData[6]
            if locked_until and locked_until > datetime.utcnow():
                return {"success": False, "error": f"Account locked until {locked_until}"}
            hashed_password = userData[2]
            role = userData[3]
            last_failed_attempt = userData[5]
            try:
                ph.verify(hashed_password, password)
                if ph.check_needs_rehash(hashed_password):
                    new_hash = ph.hash(password)
                    self.cur.execute("UPDATE users SET password = %s WHERE username = %s", (new_hash, username))
                    self.conn.commit()
                self.cur.execute("UPDATE users SET failed_attempts = 0, last_failed_attempt = NULL, locked_until = NULL WHERE username = %s", (username,))
                self.conn.commit()
                return {"success":  True, "role": role} 
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                
                if last_failed_attempt is None or last_failed_attempt < datetime.utcnow() - timedelta(hours=1):
                    failed_attempts = 1
                else:
                    failed_attempts = userData[4] + 1
                locked_until = datetime.utcnow() + timedelta(hours=1) if failed_attempts >= 3 else None
                self.cur.execute("UPDATE users SET failed_attempts = %s, last_failed_attempt = %s, locked_until = %s WHERE username = %s", (failed_attempts, datetime.utcnow(), locked_until, username))
                self.conn.commit()
                return {"success": False, "error": "Invalid username or password"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
    def get_users(self):
        try:            
            self.connect()
            self.cur.execute("SELECT username, role, failed_attempts, last_failed_attempt, locked_until FROM users")
            rows = self.cur.fetchall()
            return {"success": True, "users": rows}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass  
    def unlock_user(self, username):
        try:
            self.connect()
            self.cur.execute("UPDATE users SET failed_attempts = 0, last_failed_attempt = NULL, locked_until = NULL WHERE username = %s", (username,))
            self.conn.commit()
            if self.cur.rowcount == 0:
                return {"success": False, "error": "User not found."}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass