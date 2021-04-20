import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

app = FastAPI()

# For serving static files
app.mount("/static", StaticFiles(directory="static"), name="static")

### Handlers ###################################################################

def create_note(item, notes):
    if len(notes) == 0:
        # First note
        new_id = 0
    else:
        # Write id of last/top note plus 1 
        new_id = notes[0]['id'] + 1
    
    # Prepend note to note list
    new_note = {
        'id': new_id,
        'title': item['title'],
        'content': item['content']
    }
    notes.insert(0, new_note)
    with open('../notes.json', 'w') as outfile:
        json.dump(notes, outfile)
    
    # Send note back to frontend with correct ID
    message = new_note.copy()
    message['method'] = 'POST_BACK'
    return message

def read_notes():
    if not os.path.exists('../notes.json'):
        # Create JSON file if it doesn't exist yet
        with open('../notes.json', 'w+') as outfile:
            json.dump([], outfile)
        notes = []
    else:
        # If JSON with notes exists, send notes to frontend
        with open('../notes.json', 'r') as json_file:
            notes = json.load(json_file)

    # Save last few notes to list for frontend
    return {
        'method': 'GET',
        'note_list': notes[:10]
    }

def edit_note(item, notes):
    # Find note for edit
    for note in notes:
        if note['id'] == int(item['id']):
            note['title'] = item['title']
            note['content'] = item['content']
    
    # Save notes with edited item
    with open('../notes.json', 'w') as outfile:
        json.dump(notes, outfile)

def delete_note(item, notes):
    # Find index of item, that will be deleted
    idx = None
    for i, j in enumerate(notes):
        if j['id'] == int(item['id']):
            idx = i
    notes.pop(idx) # Delete item

    # Save notes without deleted item
    with open('../notes.json', 'w') as outfile:
        json.dump(notes, outfile)

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

    # Send last few notes to frontend
    message = read_notes()
    await websocket.send_json(message)

    try:
        while True:
            # Wait for messages from frontend
            data = await websocket.receive_text()
            item = json.loads(data)

            # Open notes.json everytime message comes
            with open('../notes.json') as json_file:
                notes = json.load(json_file)

            if item['method'] == 'POST':
                message = create_note(item, notes)

                # Send note back to frontend with correct ID, so it can be displayed
                await websocket.send_json(message)
            
            elif item['method'] == 'EDIT':
                edit_note(item, notes)
                
                # Inform frontend that note has been edited on server
                message = {'method': 'EDIT_BACK'}
                await websocket.send_json(message)

            elif item['method'] == 'DELETE':
                delete_note(item, notes)
                
                # Inform frontend that note has been removed on server
                message = {'method': 'DELETE_BACK'}
                await websocket.send_json(message)
                    
    except WebSocketDisconnect:
        print('WebSocket was closed!')