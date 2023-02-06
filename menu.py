from typing import List
import fastapi.responses
from fastapi import Query, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import etc_manager

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/twitch/menu", response_class=fastapi.responses.HTMLResponse)
def menu_provider(remove: List[str] = Query(default=[], max_length=50)):
    result = ""
    for menu, content in etc_manager.menus.items():
        if menu not in remove:
            result += etc_manager.menu_template.render(
                link=content[0], menu_name=content[1]
            )
    return result
