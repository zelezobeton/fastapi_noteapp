# TODO
* When reloading server, notes get shown 2x on frontend
* Make WebSocket connection more robust
    * How to keep connection after server reload? -> ws.onopen
    * When shutting off server, tell fronted, so websockets are not trying to connect?
* Replace JSON with sqlite
* Implement search
* Implement tags
* Implement links to other notes

# DONE
* Upload to github
* Implement UPDATE and DELETE
* Later try websockets? https://fastapi.tiangolo.com/advanced/websockets/

# LINKS
* https://fastapi.tiangolo.com/advanced/websockets/
* https://dev.to/ramonak/javascript-how-to-access-the-return-value-of-a-promise-object-1bck
* https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch
* Use WebSockets as REST - https://stackoverflow.com/a/44122364
* https://github.com/tiangolo/fastapi/issues/130#issuecomment-624764879
* Basic PWA structure - https://github.com/oliverjam/minimal-pwa
* https://stackoverflow.com/questions/22431751/websocket-how-to-automatically-reconnect-after-it-dies

# DATABASE
* https://stackoverflow.com/questions/65270624/how-to-connect-to-a-sqlite3-db-file-and-fetch-contents-in-fastapi
* https://fastapi.tiangolo.com/advanced/async-sql-databases/
* Use SQLAlchemy core queries? (like query = notes.insert()) - https://www.encode.io/databases/database_queries/

# COMMANDS
```bash
uvicorn main:app --reload
SHIFT + F5 # for refresh of CSS
```