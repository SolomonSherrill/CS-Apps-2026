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

    def search_parts(self, name=None, category=None, vendor=None, part_number=None):
        query = "SELECT * FROM inventory WHERE 1=1"
        params = []
        if name:
            query += " AND name ILIKE %s"
            params.append(f"%{name}%")
        if category:
            query += " AND category = %s"
            params.append(f"%{category}%")
        if vendor:
            query += " AND vendor = %s"
            params.append(f"%{vendor}%")
        if part_number:
            query += " AND part_number = %s"
            params.append(f"%{part_number}%")
        self.cur.execute(query, tuple(params))
        rows = self.cur.fetchall()
        return {"parts": rows}
    
    def get_low_inventory(self):
        self.cur.execute("SELECT * FROM inventory WHERE quantity < minquantity")
        rows = self.cur.fetchall()
        return {"low_inventory": rows}
    
    def update_inventory(self, id, quantity):
        try:
            self.cur.execute("UPDATE parts SET quantity = %s WHERE id = %s", (quantity, id))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}