import sqlite3
conn = sqlite3.connect("db.sqlite3")
cur = conn.execute("PRAGMA table_info(sales_quotation_salesquotation)")
cols = [r[1] for r in cur.fetchall()]
print("Columns:", cols)
print("Has po_ref:", "po_ref" in cols)
cur = conn.execute("SELECT name, applied FROM django_migrations WHERE app='sales_quotation'")
print("Migrations:", cur.fetchall())
conn.close()
