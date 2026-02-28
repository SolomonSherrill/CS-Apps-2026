import psycopg2
import os
from dotenv import load_dotenv

class inventory:
    def __init__(self):
        load_dotenv()
        db_url = os.getenv("SUPABASE_URL")
        if not db_url:
            raise ValueError("SUPABASE_URL not found in environment variables.")
        self.conn = psycopg2.connect(db_url)
        self.cur = self.conn.cursor()

    def get_inventory(self):
        try:
            self.cur.execute("SELECT * FROM parts")
            rows = self.cur.fetchall()
            return {"inventory": rows}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_part(self, name, category, vendor, quantity, min_quantity, part_number=None, url=None, notes=None):
        try:
            self.cur.execute(
                "INSERT INTO parts (name, category, vendor, quantity, min_quantity, part_number, url, notes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (name, category, vendor, quantity, min_quantity, part_number, url, notes)
            )
            self.conn.commit()
            return {"success": True, "id": self.cur.fetchone()[0]}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}

    def update_inventory(self, id, quantity):
        try:
            self.cur.execute("UPDATE parts SET quantity = %s WHERE id = %s", (quantity, id))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}