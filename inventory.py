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
        
    def edit_part(self, id, name=None, category=None, vendor=None, quantity=None, min_quantity=None, part_number=None, url=None, notes=None):
        try:
            updates = []
            values = []
            if name is not None:
                updates.append("name = %s")
                values.append(name)
            if category is not None:
                updates.append("category = %s")
                values.append(category)
            if vendor is not None:
                updates.append("vendor = %s")
                values.append(vendor)
            if quantity is not None:
                updates.append("quantity = %s")
                values.append(quantity)
            if min_quantity is not None:
                updates.append("min_quantity = %s")
                values.append(min_quantity)
            if part_number is not None:
                updates.append("part_number = %s")
                values.append(part_number)
            if url is not None:
                updates.append("url = %s")
                values.append(url)
            if notes is not None:
                updates.append("notes = %s")
                values.append(notes)
            if not updates:
                return {"success": False, "error": "No fields to update"}
            values.append(id)
            update_query = "UPDATE parts SET " + ", ".join(updates) + " WHERE id = %s"
            self.cur.execute(update_query, tuple(values))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def delete_part(self, id):
        try:
            self.cur.execute("DELETE FROM parts WHERE id = %s", (id,))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}