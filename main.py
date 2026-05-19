from fastapi import FastAPI
from routes.auth import authrouter
from routes.upload import uploadrouter
from routes.create import createrouter
from routes.ask import askrouter

app = FastAPI()

app.include_router(authrouter)
app.include_router(uploadrouter)
app.include_router(createrouter)
app.include_router(askrouter)