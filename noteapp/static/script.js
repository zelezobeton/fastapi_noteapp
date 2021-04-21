/* Manage reconnection of websockets. Everytime connection is lost, 
functions must be assigned again to the new websocket */
var ws;
function connect() {
    ws = new WebSocket('ws://localhost:8000/ws');
    ws.onopen = function () {
        // Get first few notes (Do I need note refresh every reconnection?)
        ws.send(JSON.stringify({
            'method': 'GET'
        }));
    };

    // Wait for messages from server
    ws.onmessage = function(event) {
        var noteObj = JSON.parse(event.data);

        // Decide what to do with message from server
        if (noteObj['method'] == 'GET_BACK') {
            var noteList = noteObj['note_list']
            for (var item in noteList) {
                displayNote(noteList[item], false)
            }
        } 
        else if (noteObj['method'] == 'POST_BACK') {
            displayNote(noteObj, true)
            notify('SUBMITED', 'green')
        }  
        else if (noteObj['method'] == 'DELETE_BACK') {
            notify('DELETED', 'green')
        }
        else if (noteObj['method'] == 'EDIT_BACK') {
            notify('EDITED', 'green')
        }
    };

    // Try to reconnect (in case of server reload etc.)
    ws.onclose = function (event) {
        console.log('Socket is closed. Reconnect will be attempted in 1 second.', event.reason);
        setTimeout(function () {
            connect();
        }, 1000);
    };

    // Log errors
    ws.onerror = function (err) {
        console.error('Socket encountered error: ', err.message, 'Closing socket');
        ws.close();
    };
}
connect();

// Visualy comfort user, that his data is saved on server
function notify(text, color){
    var res = document.querySelector("#result");
    var orig_color = res.style.color;
    var orig_text = res.textContent;

    // Don't change if it's in process of changing
    if (orig_text == 'RESULT') {
        res.style.color = color;
        res.textContent = text;
        setTimeout(function(){
            res.style.color = orig_color;
            res.textContent = orig_text;
        }, 3000);
    }
}

/// CRUD functions /////////////////////////////////////////////////////////////

function submitNote(event) {
    var title = document.querySelector("#noteTitleSubmit")
    var content = document.querySelector("#noteContentSubmit")
    
    // Send message to server with note data
    var obj = {
        'method': 'POST',
        'title': title.value,
        'content': content.value
    }
    ws.send(JSON.stringify(obj))
    
    // Clear textareas
    title.value = ''
    content.value = ''
}

function displayNote(noteObj, prepend) {
    var notesContainer = document.querySelector(".notesContainer");
    var noteTemplate = document.querySelector('#noteTemplate');

    // Fill template of note with data
    var note = noteTemplate.content.cloneNode(true);
    note.querySelector(".note").dataset.noteid = noteObj['id']; // Use data attribute for id
    note.querySelector(".noteTitle").textContent = noteObj['title'];
    note.querySelector(".noteContent").textContent = noteObj['content'];

    // Decide if prepend or append note
    if (prepend) {
        notesContainer.prepend(note)
    } else {
        notesContainer.append(note)
    }
}

function editNote(event) {
    var innerNoteElement = event.currentTarget.parentNode.parentNode;
    var noteElement = innerNoteElement.parentNode;
    
    // Hide element
    innerNoteElement.style.display = 'none';
    
    // Fill input areas with current data
    var noteEditTemplate = document.querySelector('#noteEditTemplate');
    var noteEdit = noteEditTemplate.content.cloneNode(true);
    noteEdit.querySelector("#noteTitleEdit").value = innerNoteElement.querySelector(".noteTitle").textContent;
    noteEdit.querySelector("#noteContentEdit").value = innerNoteElement.querySelector(".noteContent").textContent;
    noteElement.append(noteEdit)
}

function updateNote(event) {
    var innerNoteEditElement = event.currentTarget.parentNode.parentNode;
    var noteElement = innerNoteEditElement.parentNode;
    var innerNoteElement = noteElement.querySelector(".innerNote");
    var old_title = innerNoteElement.querySelector(".noteTitle").textContent;
    var old_content = innerNoteElement.querySelector(".noteContent").textContent;
    
    // Get new data and remove element for editing
    var title = document.querySelector("#noteTitleEdit").value;
    var content = document.querySelector("#noteContentEdit").value;
    innerNoteEditElement.remove();
    
    // In case that strings didn't change, skip database change
    if (title.trim() == old_title.trim() && content.trim() == old_content.trim()) {
        // Unhide note
        innerNoteElement.style.display = '';
    } else {
        // Fill note with current data and unhide it
        innerNoteElement.querySelector(".noteTitle").textContent = title;
        innerNoteElement.querySelector(".noteContent").textContent = content;
        innerNoteElement.style.display = '';
        
        // Send edited note to server
        var obj = {
            'method': 'EDIT',
            'id': noteElement.dataset.noteid,
            'title': title,
            'content': content
        }
        ws.send(JSON.stringify(obj))
    }
}

function deleteNote(event) {
    var noteElement = event.currentTarget.parentNode.parentNode.parentNode;

    // Send message to server with id of note to be deleted
    var obj = {
        'method': 'DELETE',
        'id': noteElement.dataset.noteid
    }
    ws.send(JSON.stringify(obj))

    // Remove note from HTML canvas
    noteElement.remove()
}