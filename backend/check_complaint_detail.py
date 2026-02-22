import sqlite3
import sys

db_path = '../data/servonix.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check complaint #25
cursor.execute('''
    SELECT c.*
    FROM complaints c
    WHERE c.id = 25
''')
row = cursor.fetchone()

if row:
    print('Complaint #25:')
    print(f'  Complaint Type: {row["complaint_type"]}')
    print(f'  Route Number: {row["route_number"]}')
    print()
else:
    print('Complaint #25 not found')
    sys.exit(1)
    
# Check media files
cursor.execute('SELECT * FROM complaint_media WHERE complaint_id = 25')
media = cursor.fetchall()

print(f'Media files: {len(media)}')
for i, m in enumerate(media):
    print(f'  {i+1}. {m["file_name"]}')
    print(f'      Path: {m["file_path"]}')
    print(f'      Type: {m["mime_type"]}')

conn.close()
