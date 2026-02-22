import sqlite3
conn = sqlite3.connect('complaints.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row['name'] for row in cursor.fetchall()]
print("Tables:", tables)

# Check complaint #25
cursor.execute('''
    SELECT c.*
    FROM complaints c
    WHERE c.id = 25
''')
row = cursor.fetchone()

if row:
    print('\nComplaint #25:')
    print(f'  Complaint Type: {row["complaint_type"]}')
    print(f'  Route Number: {row["route_number"]}')
    
# Check media files
cursor.execute('SELECT * FROM complaint_media WHERE complaint_id = 25')
media = cursor.fetchall()

print(f'\nMedia files: {len(media)}')
for i, m in enumerate(media):
    print(f'  {i+1}. {m["file_name"]}')
    print(f'      Path: {m["file_path"]}')
    print(f'      Type: {m["mime_type"]}')

conn.close()
