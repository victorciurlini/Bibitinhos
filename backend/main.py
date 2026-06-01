from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

app = FastAPI(title="Bibitinhos Backend")

# Permitir conexões do frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, defina a URL exata
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
def read_root():
    return {"status": "Bibitinhos Backend is Running!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Em um cenário real, o client não precisará enviar muito,
            # apenas receber o state do servidor.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Loop de simulação placeholder (será integrado ao engine.py futuramente)
from simulation.engine import SimulationEngine
from simulation.creature import Creature

engine = SimulationEngine()

async def simulation_loop():
    while True:
        try:
            engine.step(1 / 30.0)
            state = engine.get_state()
            state["type"] = "state_update"
            await manager.broadcast(state)
        except Exception as e:
            import traceback
            traceback.print_exc()
        await asyncio.sleep(1 / 30.0) # 30 FPS

@app.on_event("startup")
async def startup_event():
    # Adicionar algumas criaturas iniciais
    for _ in range(10):
        engine.add_creature(Creature(engine))
    # Inicia o loop da simulação em background
    app.state.sim_task = asyncio.create_task(simulation_loop())
