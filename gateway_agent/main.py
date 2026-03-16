from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from robot_services.camera_monitor.scripts.mqtt_video_service import get_mqtt_video_service
from robot_services.manipulation.scripts.mqtt_manipulation_service import get_mqtt_manipulation_service
from robot_services.motion.scripts.mqtt_motion_service import get_mqtt_motion_service
from robot_services.point_navigation.scripts.mqtt_point_navigation_service import get_mqtt_point_navigation_service
from robot_services.vision.scripts.mqtt_vision_service import get_mqtt_vision_service
from security import apply_security_headers, get_allowed_origins
from ws.endpoints import router as ws_router

app = FastAPI(title='HRT Gateway MVP', version='0.0.1')
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['Authorization', 'Content-Type'],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.on_event("startup")
def startup_event() -> None:
    get_mqtt_video_service().start()
    get_mqtt_manipulation_service().start()
    get_mqtt_motion_service().start()
    get_mqtt_point_navigation_service().start()
    get_mqtt_vision_service().start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    get_mqtt_vision_service().stop()
    get_mqtt_point_navigation_service().stop()
    get_mqtt_motion_service().stop()
    get_mqtt_manipulation_service().stop()
    get_mqtt_video_service().stop()


@app.get('/healthz')
def healthz():
    return {'ok': True, 'mode': 'mvp'}


@app.middleware('http')
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    apply_security_headers(response.headers)
    return response
