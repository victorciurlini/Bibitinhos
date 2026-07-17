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

# Loop de simulação e engine
from simulation.engine import SimulationEngine
from simulation.creature import Creature
from simulation.params import set_param, reset_params
from simulation.rtneat_wrapper import genome_to_dict

engine = SimulationEngine()


def build_creature_inspection(engine, creature_id):
    """Monta o payload unicast creature_inspection (BIT-27).

    Puro (nao toca o socket) para ser testavel direto — o TestClient nao roda
    neste venv (starlette 0.27 + httpx 0.28 nao convivem; mesmo desvio do BIT-26).
    Criatura inexistente/morta => genome null (o cliente trata sem quebrar).
    """
    creature = next((c for c in engine.creatures if c.id == creature_id), None)
    return {
        "type": "creature_inspection",
        "creature_id": creature_id,
        "genome": genome_to_dict(creature.genome, creature.config) if creature else None,
    }

@app.get("/metrics/history")
def metrics_history():
    """Historico amostrado de metricas populacionais (BIT-26) — bootstrap do painel do HUD.

    O broadcast de 30 FPS carrega so os agregados correntes (campo "metrics" do state_update);
    a serie temporal completa vive aqui, em ordem cronologica (ate METRICS_HISTORY_MAX itens).
    """
    return {"history": list(engine.metrics_history)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            action = msg.get("action")
            if action == "set_time_control":
                engine.set_time_control(paused=msg.get("paused"), speed=msg.get("speed"))
            elif action == "drag":
                phase = msg.get("phase")
                if phase == "start":
                    engine.start_drag(msg.get("creature_id"))
                elif phase == "move":
                    try:
                        engine.drag_to(float(msg.get("x")), float(msg.get("y")))
                    except (TypeError, ValueError):
                        pass
                elif phase == "end":
                    engine.end_drag()
            elif action == "set_param":
                set_param(engine, msg.get("name"), msg.get("value"))
            elif action == "reset_params":
                reset_params(engine)
            elif action == "inspect_creature":
                # Resposta UNICAST ao socket que pediu (o genoma nao vai no broadcast).
                await websocket.send_json(
                    build_creature_inspection(engine, msg.get("creature_id"))
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        engine.end_drag()  # cliente caiu no meio de um drag: solta a criatura

async def simulation_loop():
    # BIT-24: aceleracao/desaceleracao por SUBSTEPS de dt fixo (1/30), nunca mudando o dt.
    # 0.5x = um step a cada duas iteracoes; 2x/4x = 2/4 substeps por iteracao. Pausado: nenhum
    # step, mas o broadcast continua (o cliente precisa do eco de paused/speed e do estado
    # corrente para drag/inspecao).
    speed_accumulator = 0.0
    while True:
        try:
            if not engine.paused:
                speed_accumulator += engine.speed
                while speed_accumulator >= 1.0:
                    engine.step(1 / 30.0)
                    speed_accumulator -= 1.0
            state = engine.get_state()
            state["type"] = "state_update"
            await manager.broadcast(state)
        except Exception:
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
