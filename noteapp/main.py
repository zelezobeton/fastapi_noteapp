import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

app = FastAPI()

# For serving static files
app.mount("/static", StaticFiles(directory="static"), name="static")

### Database ###################################################################

from databases import Database # For async access of sqlite DB

database = Database("sqlite:///../test.db")

@app.on_event("startup")
async def database_connect():
    await database.connect()
    await create_table()

@app.on_event("shutdown")
async def database_disconnect():
    await database.disconnect()

# Create table
async def create_table():
    query1 = '''CREATE TABLE IF NOT EXISTS 
        note_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created INTEGER,
            changed INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )'''
    query2 = '''CREATE TABLE IF NOT EXISTS 
        tag_table (
            tag_id INTEGER PRIMARY KEY,
            tag_name TEXT NOT NULL
        )'''
    query3 = '''CREATE TABLE IF NOT EXISTS 
        note_tag_mapping (
            note_reference         INTEGER,
            tag_reference          INTEGER
        )'''
    await database.execute(query=query1)
    await database.execute(query=query2)
    await database.execute(query=query3)

### Tags #######################################################################

def is_in_list(my_list, string):
    for x in my_list:
        if string.lower().strip() == x.lower().strip():
            return True
    return False

async def inspect_tags():
    query3 = '''SELECT note_table.id, group_concat(tag_name,',')
        FROM note_tag_mapping
        JOIN note_table ON note_reference = note_table.id
        JOIN tag_table ON tag_reference = tag_table.tag_id
        GROUP BY note_table.id'''
    rows = await database.fetch_all(query=query3)
    for x in rows:
        print(x)

async def add_tag_to_note(note_id, tag_name):
    # Don't accept empty string as tag
    if tag_name == "":
        return

    # Find out if tag exists already
    query1 = f'SELECT EXISTS (SELECT 1 FROM tag_table WHERE tag_name = "{tag_name}")'
    result = await database.fetch_val(query=query1)
    
    if result == 0:
        # Tag doesn't exist yet, create it
        query2 = f'INSERT INTO tag_table (tag_name) VALUES ("{tag_name}")'
        await database.execute(query=query2)
    
    # Get tag id
    query3 = f'SELECT tag_id FROM tag_table WHERE tag_name = "{tag_name}"'
    tag_id = await database.fetch_val(query=query3)

    # Insert note-tag mapping only if it doesn't exist yet
    query4 = f'''INSERT INTO note_tag_mapping (note_reference, tag_reference)
        SELECT {note_id}, {tag_id} 
        WHERE NOT EXISTS(SELECT 1 FROM note_tag_mapping 
        WHERE note_reference = {note_id} AND tag_reference = {tag_id})'''
    await database.execute(query=query4)

async def remove_tag_from_note(note_id, tag_name):
    # Get tag id
    query1 = f'SELECT tag_id FROM tag_table WHERE tag_name = "{tag_name}"'
    tag_id = await database.fetch_val(query=query1)

    # Remove note-tag connection in db
    query2 = f"DELETE FROM note_tag_mapping WHERE tag_reference={tag_id} AND note_reference = {note_id}"
    await database.execute(query=query2)

async def get_note_tags(note_id):
    # Get note tags from database
    query = f'''SELECT group_concat(tag_name,',')
        FROM note_tag_mapping
        JOIN note_table ON note_reference = note_table.id
        JOIN tag_table ON tag_reference = tag_table.tag_id
        WHERE note_table.id = {note_id}'''
    tags_str = await database.fetch_val(query=query)

    # Return tags in list
    if tags_str is None:
        return []
    else:
        return tags_str.split(",")

async def update_note_tags(note_id, frontend_tags):
    backend_tags = await get_note_tags(note_id)
    
    # Compare frontend and backend tags
    new_tags = [tag for tag in frontend_tags if not is_in_list(backend_tags, tag)]
    removed_tags = [tag for tag in backend_tags if not is_in_list(frontend_tags, tag)]

    # Add new tags
    for tag in new_tags:
        await add_tag_to_note(note_id, tag)

    # Remove missing tags
    for tag in removed_tags:
        await remove_tag_from_note(note_id, tag)

### Handlers ###################################################################

async def create_note(item):
    # Save note to database
    query1 = "INSERT INTO note_table (created, changed, title, content) VALUES (:created, :changed, :title, :content)"
    values = {
        "created": item['created'], 
        "changed": item['changed'], 
        "title": item['title'], 
        "content": item['content']}
    await database.execute(query=query1, values=values)

    # Get new note id
    query2 = "SELECT * FROM note_table ORDER BY id DESC LIMIT 1"
    note_id = await database.fetch_val(query=query2)

    # Update tags of note
    await update_note_tags(note_id, item['tags'])

    # Send note back to frontend with correct ID
    return {
        'method': 'POST_BACK',
        'id': note_id,
        'created': item['created'], 
        'changed': item['changed'], 
        'title': item['title'],
        'content': item['content'],
        'tags': item['tags']
    }

async def read_notes():
    # Get notes with tags
    query = '''SELECT note_table.id, created, changed, title, content, group_concat(tag_name,',')
        FROM note_table
        LEFT JOIN note_tag_mapping ON note_table.id = note_tag_mapping.note_reference
        LEFT JOIN tag_table ON note_tag_mapping.tag_reference = tag_table.tag_id
        GROUP BY note_table.id
        ORDER BY note_table.changed DESC LIMIT 10'''
    rows = await database.fetch_all(query=query)

    # Put notes in list of dicts for frontend 
    note_list = []
    for note in rows:
        # Split tags from database by comma and create taglist
        tag_list = note[5].split(",") if note[5] is not None else []
        note_list.append({
            'id': note[0],
            'created': note[1],
            'changed': note[2],
            'title': note[3],
            'content': note[4],
            'tags': tag_list
        })
    
    return {
        'method': 'GET_BACK',
        'note_list': note_list
    }

async def edit_note(item):
    query = "UPDATE note_table SET changed=:changed, title=:title, content=:content WHERE id=:id"
    values = {
        "id": item['id'], 
        "changed": item['changed'], 
        "title": item['title'], 
        "content": item['content']}
    await database.execute(query=query, values=values)

    # Update tags of note
    await update_note_tags(item['id'], item['tags'])

    return {'method': 'EDIT_BACK'}

async def delete_note(item):
    query = "DELETE FROM note_table WHERE id=:id"
    values = {'id': item['id']}
    await database.execute(query=query, values=values)

    return {'method': 'DELETE_BACK'}

async def search_notes(item):
    text = item['text']
    query = f'''SELECT note_table.id, created, changed, title, content, group_concat(tag_name,',')
        FROM note_table
        LEFT JOIN note_tag_mapping ON note_table.id = note_tag_mapping.note_reference
        LEFT JOIN tag_table ON note_tag_mapping.tag_reference = tag_table.tag_id
        WHERE title LIKE "%{text}%" OR content LIKE "%{text}%"
        GROUP BY note_table.id
        ORDER BY note_table.changed DESC LIMIT 10'''
    rows = await database.fetch_all(query=query)

    # Only save notes containing search text
    note_list = []
    for note in rows:
        tag_list = note[5].split(",") if note[5] is not None else []
        note_list.append({
            'id': note[0],
            'created': note[1],
            'changed': note[2],
            'title': note[3],
            'content': note[4],
            'tags': tag_list
        })
    
    return {
        'method': 'SEARCH_BACK',
        'note_list': note_list
    }

### Routes #####################################################################

@app.get("/")
async def read_index():
    '''
    Serve website at root
    '''
    return RedirectResponse(url="/static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Wait for frontend to accept connection
    await websocket.accept()

    # await inspect_tags()

    try:
        while True:
            # Wait for messages from frontend
            data = await websocket.receive_text()
            item = json.loads(data)

            if item['method'] == 'POST':
                # Send note back to frontend with correct ID, so it can be displayed
                message = await create_note(item)
                await websocket.send_json(message)

            elif item['method'] == 'GET':
                # Send last few notes to frontend
                message = await read_notes()
                await websocket.send_json(message)
            
            elif item['method'] == 'EDIT':
                # Inform frontend that note has been edited on server
                message = await edit_note(item)
                await websocket.send_json(message)

            elif item['method'] == 'DELETE':
                # Inform frontend that note has been removed on server
                message = await delete_note(item)
                await websocket.send_json(message)
            
            elif item['method'] == 'SEARCH':
                message = await search_notes(item)
                await websocket.send_json(message)
                    
    except WebSocketDisconnect:
        print('WebSocket was closed!')
