/* Manage reconnection of websockets. Everytime connection is lost, 
functions must be assigned again to the new websocket */
var ws;
var firstFetch = true;
function connect() {
    ws = new WebSocket('ws://localhost:8000/ws');
    ws.onopen = function () {
        // Get first few notes (Do I need note refresh every reconnection?)
        if (firstFetch) {
            ws.send(JSON.stringify({
                'method': 'GET'
            }));
        }
    };

    // Wait for messages from server
    ws.onmessage = function(event) {
        var noteObj = JSON.parse(event.data);

        // Decide what to do with message from server
        if (noteObj['method'] == 'GET_BACK') {
            var noteList = noteObj['note_list']
            for (var item of noteList) {
                displayNote(item, false)
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
        else if (noteObj['method'] == 'SEARCH_BACK') {
            removeNotes();

            // Display notes displaying searched text
            var noteList = noteObj['note_list']
            for (var item of noteList) {
                displayNote(item, false)
            }
        }
    };

    // Try to reconnect (in case of server reload etc.)
    ws.onclose = function (event) {
        firstFetch = false;
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

/// Helper functions ///////////////////////////////////////////////////////////

// Visualy comfort user, that his data is saved on server
function notify(text, color){
    var res = document.querySelector("#result");
    var orig_color = res.style.color;
    var orig_text = res.textContent;

    // Don't change result if it's in process of changing
    if (orig_text == 'RESULT') {
        res.style.color = color;
        res.textContent = text;
        setTimeout(function(){
            res.style.color = orig_color;
            res.textContent = orig_text;
        }, 3000);
    }
}

function timestampToDatetime(timestamp) {
    var datetime = new Date(timestamp);
    return datetime.toLocaleDateString("cs-CZ") + ' - ' +  datetime.toLocaleTimeString("cs-CZ")
}

function tagStrToList(tagStr) {
    var tagList = [];
    for (var tag of tagStr.split(',')) {
        if (tag != "") {
            tagList.push(tag.trim());
        }
    }
    return tagList
}

/// CRUD functions /////////////////////////////////////////////////////////////

function submitNote(event) {
    var title = document.querySelector("#noteTitleSubmit")
    var content = document.querySelector("#noteContentSubmit")
    var tags = document.querySelector("#noteTagsSubmit")
    
    // Send message to server with note data
    var timestamp = Math.floor(Date.now());
    var obj = {
        'method': 'POST',
        'created': timestamp,
        'changed': timestamp,
        'title': title.value,
        'content': content.value,
        'tags': tagStrToList(tags.value)
    }
    ws.send(JSON.stringify(obj))
    
    // Clear textareas
    title.value = ''
    content.value = ''
    tags.value = ''
}

function displayNote(noteObj, prepend) {
    var notesContainer = document.querySelector(".notesContainer");
    var noteTemplate = document.querySelector('#noteTemplate');
    
    // Fill template of note with data
    var note = noteTemplate.content.cloneNode(true);
    note.querySelector(".note").dataset.noteid = noteObj['id']; // Use data attribute for id
    note.querySelector(".noteChanged").textContent = timestampToDatetime(noteObj['changed'])
    note.querySelector(".noteTitle").textContent = noteObj['title'];
    note.querySelector(".noteContent").textContent = noteObj['content'];
    
    // Display tags
    var tagsContainer = note.querySelector(".noteTags");
    displayTags(tagsContainer, noteObj['tags']);

    // Decide if prepend or append note
    if (prepend) {
        notesContainer.prepend(note)
    } else {
        notesContainer.append(note)
    }
}

function displayTags(tagsContainer, tagList) {
    var tagTemplate = document.querySelector('#tagTemplate');
    tagsContainer.dataset.taglist = tagList; // Use data attribute for saving tags
    for (var tagName of tagList) {
        var element = tagTemplate.content.cloneNode(true);
        element.querySelector(".tag").textContent = tagName;
        tagsContainer.append(element);
    }
}

function removeNotes() {
    // Remove notes currently on canvas
    var notesContainer = document.querySelector(".notesContainer");
    while (notesContainer.firstChild) {
        notesContainer.firstChild.remove()
    }
}

// Change appearance of note while editing
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
    noteEdit.querySelector("#noteTagsEdit").value = innerNoteElement.querySelector(".noteTags").dataset.taglist;
    noteElement.append(noteEdit)
}

// Update note content on backend
function updateNote(event) {
    var innerNoteEditElement = event.currentTarget.parentNode.parentNode;
    var noteElement = innerNoteEditElement.parentNode;
    var innerNoteElement = noteElement.querySelector(".innerNote");
    var old_title = innerNoteElement.querySelector(".noteTitle").textContent;
    var old_content = innerNoteElement.querySelector(".noteContent").textContent;
    var old_tags = innerNoteElement.querySelector(".noteTags").dataset.taglist;
    
    // Get new data and remove element for editing
    var title = document.querySelector("#noteTitleEdit").value;
    var content = document.querySelector("#noteContentEdit").value;
    var tags = document.querySelector("#noteTagsEdit").value;
    innerNoteEditElement.remove();
    
    // In case that strings didn't change, skip database change
    if (title.trim() == old_title.trim() && 
        content.trim() == old_content.trim() &&
        tags.trim() == old_tags.trim()) {
        // Unhide note
        innerNoteElement.style.display = '';
    } else {
        // Remove hidden old note 
        noteElement.remove();

        // Create note object filled with new data
        var timestamp = Math.floor(Date.now());
        var noteObj = {
            'method': 'EDIT',
            'id': noteElement.dataset.noteid,
            'changed': timestamp,
            'title': title,
            'content': content,
            'tags': tagStrToList(tags)
        }

        // Display edited note and send it to server
        displayNote(noteObj, true)
        ws.send(JSON.stringify(noteObj))
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

function searchText(event) {
    if (event.key == "Enter") {
        // Send message to server with id of note to be deleted
        var inputArea = event.currentTarget;
        var obj = {
            'method': 'SEARCH',
            'text': inputArea.value
        }
        ws.send(JSON.stringify(obj))

        inputArea.value = ''
    }
}