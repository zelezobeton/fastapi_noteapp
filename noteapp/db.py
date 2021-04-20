import sqlite3

con = sqlite3.connect('example.db')

cur = con.cursor()

# Implementing tags 
# CREATE TABLE IF NOT EXISTS 
#   tag (
#     tag_id              INTEGER PRIMARY KEY,
#     tag_name            TEXT NOT NULL
#   )

# CREATE TABLE IF NOT EXISTS 
#   post_tag_link (
#     post_id         INTEGER,
#     tag_id          INTEGER
#   )

# Create table
cur.execute('DROP TABLE IF EXISTS post')
cur.execute('''CREATE TABLE post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    body TEXT NOT NULL
    )''')

# Insert a row of data
cur.execute("INSERT INTO post (title, body) VALUES ('Dobrej nadpis','Jeste lepsi obsah')")
cur.execute("INSERT INTO post (title, body) VALUES ('Neco jinyho','At to neni repetetivni')")
cur.execute("INSERT INTO post (title, body) VALUES ('A vis co','Neco dalsiho')")

# Save (commit) the changes
con.commit()

for row in cur.execute('SELECT * FROM post ORDER BY id LIMIT 5'):
    print(row[0])
    print(row[1])
    print(row[2])
    print(row[3],"\n")

