from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from ws.endpoints import router as ws_router

app = FastAPI(title='HRT Gateway MVP', version='0.0.1')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.get('/healthz')
def healthz():
    return {'ok': True, 'mode': 'mock'}
