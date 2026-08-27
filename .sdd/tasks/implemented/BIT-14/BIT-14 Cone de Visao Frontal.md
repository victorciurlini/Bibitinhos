# Spec — BIT-14: Cone de Visão Frontal

**Linear:** N/A
**Risco:** medium
**Camada(s):** Múltiplas (Backend + Frontend)

---

## Demanda

Feedback do developer após ver o BIT-12/BIT-13 rodando: a visão estava grande demais (raio 200, ~20x o corpo da criatura) e ampla demais (cobria os 360° ao redor, não só a frente). Pedido explícito: "ela deverá ser um CONE, a frente da 'cabeça' do bibite".

## Abordagem técnica

Restringir `compute_vision()` a uma janela angular fixa (`VISION_FOV_DEGREES = 120`, confirmado com o developer) centrada no eixo frontal da criatura (`creature.body.angle`), em vez dos 360° atuais — qualquer coisa fora dessa janela (incluindo tudo atrás da criatura) não ativa nenhum setor, independente da distância. Reduzir `VISION_RADIUS` de 200 para 80 (também confirmado com o developer). O setor do meio (índice 4 de 0-8) passa a representar o eixo "para frente"; os setores 0 e 8 são as bordas extremas do cone (±60°). Propagar o novo FOV para o frontend (`vision_fov_degrees`, mesmo padrão do `vision_radius` já exposto no BIT-12) para o desenho do leque acompanhar a geometria real do sensor.

## Arquivos a tocar

| Arquivo (path relativo à raiz do projeto) | Alteração | Descrição |
|---|---|---|
| `backend/simulation/sensors.py` | modificar | `VISION_RADIUS` 200→80; nova constante `VISION_FOV_DEGREES = 120`; `compute_vision()` restringe a janela angular |
| `backend/simulation/rtneat_wrapper.py` | modificar | Docstring de `Visual_Sectors` atualizada (cone frontal, setor central) |
| `backend/simulation/engine.py` | modificar | `get_state()` passa a incluir `vision_fov_degrees` |
| `frontend/src/components/SimulationCanvas.jsx` | modificar | Leque desenhado só dentro do cone frontal, não mais 360° |
| `backend/tests/test_sensors.py` | modificar | Setor central passa a ser o índice 4; testes de "atrás" viram testes de "fora do cone" |

## Passos de implementação

1. **`sensors.py`**: `VISION_RADIUS = 80.0`; nova `VISION_FOV_DEGREES = 120.0` e `VISION_FOV_RADIANS = math.radians(VISION_FOV_DEGREES)`. Em `compute_vision()`, após calcular `relative_angle`, descartar (`continue`) qualquer shape com `abs(relative_angle) > VISION_FOV_RADIANS / 2`. Índice do setor recalculado a partir de `shifted = relative_angle + half_fov` (em vez de `% 2π` sobre o círculo completo), com `sector_width = VISION_FOV_RADIANS / NUM_VISION_SECTORS` e clamp final em `NUM_VISION_SECTORS - 1` para o caso de borda exata (`relative_angle == +half_fov`).
2. **`rtneat_wrapper.py`**: atualizar a linha de `Visual_Sectors` no contrato de I/O, descrevendo o cone de 120°, setor 4 como eixo central, e que nada fora do cone (incluindo atrás) ativa qualquer setor.
3. **`engine.py`**: importar `VISION_FOV_DEGREES` de `simulation.sensors` e adicionar `"vision_fov_degrees": VISION_FOV_DEGREES` em `get_state()`, ao lado de `vision_radius`.
4. **`SimulationCanvas.jsx`**: calcular `visionFovRadians` a partir de `data.vision_fov_degrees` (fallback 120); os setores passam a ser desenhados a partir de `fovStart = rotation - visionFovRadians/2`, com `sectorWidth = visionFovRadians / sectorCount`, em vez de cobrir `2π` completo.
5. **`test_sensors.py`**: setor central (`NUM_VISION_SECTORS // 2` = 4) substitui o índice 0 como "para frente" nos testes de comida/criatura diretamente à frente; testes que validavam detecção "atrás" da criatura passam a validar que ficam **fora do cone** (sem sinal); novo teste cobrindo um objeto logo fora da borda do FOV (ex: 70° de diferença angular, fora dos ±60°).

## Contratos técnicos

### Backend (Simulação)
- `VISION_RADIUS: float = 80.0` (era 200.0).
- `VISION_FOV_DEGREES: float = 120.0` (nova constante).
- `compute_vision(creature, engine) -> list[float]` — mesma assinatura e tamanho de retorno; setor central (índice 4) agora é o eixo frontal; nada fora do cone de 120° ativa qualquer setor.
- `num_inputs`/`num_outputs` em `neat_config.ini` inalterados (16/4) — mudança é só de geometria/semântica dos 9 primeiros inputs, não de contagem.

### API/WebSocket
- `get_state()` ganha campo aditivo `"vision_fov_degrees": float`, ao lado de `vision_radius` (já existente desde o BIT-12).

### Frontend
- `SimulationCanvas.jsx`: leque de setores desenhado dentro de `data.vision_fov_degrees` graus (não mais 360°), lido do payload, sem hardcode.

## Critérios de aceite

- [ ] Nada fora de um cone de 120° à frente da criatura (incluindo tudo atrás) ativa qualquer setor de visão.
- [ ] `VISION_RADIUS` é 80.
- [ ] Setor central (índice 4) é o eixo "para frente"; setores 0 e 8 são as bordas do cone.
- [ ] `vision_fov_degrees` chega no payload do WebSocket.
- [ ] O leque desenhado no canvas cobre só o cone frontal de 120°, com o raio reduzido, girando junto com a criatura.
- [ ] `pytest backend/tests/` 100% verde (suíte completa, sem regressão).
- [ ] `npm run build`/`npm run test` sem erros.

## Rollback

Reverter `sensors.py` (`VISION_RADIUS` volta a 200, remover `VISION_FOV_DEGREES` e a restrição angular); reverter `rtneat_wrapper.py` (docstring); reverter `engine.py` (remover `vision_fov_degrees`); reverter `SimulationCanvas.jsx` (leque volta a cobrir 360°); reverter `test_sensors.py`.
