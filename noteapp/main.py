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
    query = '''CREATE TABLE IF NOT EXISTS note_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL)'''
    await database.execute(query=query)

### Handlers ###################################################################

async def create_note(item):
    # Save note to database
    query = "INSERT INTO note_table (title, content) VALUES (:title, :content)"
    values = {
        "title": item['title'], 
        "content": item['content']}
    await database.execute(query=query, values=values)

    # Get new note id
    query2 = "SELECT * FROM note_table ORDER BY id DESC LIMIT 1"
    result = await database.fetch_one(query=query2)
    note_id = result[0]

    # Send note back to frontend with correct ID
    return {
        'method': 'POST_BACK',
        'id': note_id,
        'title': item['title'],
        'content': item['content']
    }

async def read_notes():
    # Run a database query
    query = "SELECT * FROM note_table ORDER BY id DESC LIMIT 10"
    rows = await database.fetch_all(query=query)

    # Put notes in list of dicts for frontend 
    note_list = []
    for note in rows:
        note_list.append({
            'id': note[0],
            'title': note[1],
            'content': note[2]
        })
    
    return {
        'method': 'GET_BACK',
        'note_list': note_list
    }

async def edit_note(item):
    query = "UPDATE note_table SET title=:title, content=:content WHERE id=:id"
    values = {
        "id": item['id'], 
        "title": item['title'], 
        "content": item['content']}
    await database.execute(query=query, values=values)

    return {'method': 'EDIT_BACK'}

async def delete_note(item):
    query = "DELETE FROM note_table WHERE id=:id"
    values = {'id': item['id']}
    await database.execute(query=query, values=values)

    return {'method': 'DELETE_BACK'}

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
                    
    except WebSocketDisconnect:
        print('WebSocket was closed!')