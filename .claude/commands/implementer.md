Você é o implementer do projeto Bibitinhos (simulador de vida artificial evolutiva). Execute a spec aprovada de uma task `BIT-XX`, paralelizando via sub-agentes o que for independente.

**Pré-condição:** diretório `.sdd/tasks/refiner/BIT-XX/` com um arquivo `BIT-XX <Título Curto>.md` existente (spec aprovada pelo developer).

**Sem Linear:** o status da task é o **próprio diretório** — mover a pasta entre `refiner/` → `implementer/` → `implemented/` é como o progresso é rastreado (ver memória `bibitinhos-tasks-folder-state-model`). Não criar/atualizar nada no Linear.

---

## Protocolo

### 1. Identificar tarefa e mover para `implementer/`

**Se o argumento for um ID (ex: `BIT-02`):**
- Procurar `.sdd/tasks/refiner/BIT-02/`
- Se não existir lá, checar se já está em `.sdd/tasks/implementer/BIT-02/` (retomando um implementer interrompido)
- Se não existir em nenhuma das duas, informar o developer que a task não foi refinada ainda

**Se nenhum argumento for fornecido:**
- Listar os diretórios em `.sdd/tasks/refiner/BIT-*/`
- Se houver mais de um, perguntar ao developer qual implementar

Mover o diretório de `.sdd/tasks/refiner/BIT-XX/` para `.sdd/tasks/implementer/BIT-XX/` (git mv se estiver versionado, senão mover no filesystem) — isso sinaliza visualmente que a implementação está em andamento.

Leia a **spec completa** (`BIT-XX <Título Curto>.md`) antes de qualquer edição de código.

**Atenção a concorrência:** se este mesmo diretório de trabalho tiver outra sessão de implementer ativa em paralelo (outra branch/chat mexendo nos mesmos arquivos), confirme com o developer antes de prosseguir — editar `creature.py`/`engine.py` simultaneamente em duas sessões causa conflito.

---

### 2. Planejar execução paralela

Analise os passos da spec e classifique:
- **Independentes:** sem dependência entre si → podem ser executados em paralelo por sub-agentes
- **Dependentes:** requerem output de outro passo → executar sequencialmente após os independentes terminarem

Para tasks pequenas/isoladas (a maioria das `backend/simulation/*`), pode ser mais rápido e seguro implementar direto (sem sub-agentes) do que paralelizar — use sub-agentes quando os passos tocam arquivos genuinamente diferentes e independentes (ex: um mexe só em `frontend/`, outro só em `backend/simulation/`).

**Prompt padrão para cada sub-agente de implementação** (quando usado):

```
Contexto:
- Projeto: Bibitinhos (simulador de vida artificial evolutiva)
- Caminho base: C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos
- Stack: Python 3.10 + FastAPI + Pymunk + neat-python 0.92 (backend) | React + Vite + Canvas (frontend)

Spec completa:
[incluir conteúdo integral da spec BIT-XX]

Passos atribuídos a este sub-agente:
[passos específicos da spec]

Convenções obrigatórias:
- Backend: funções puras onde possível (padrão de `rtneat_wrapper.py`), sem introduzir dependências novas sem necessidade
- Testes: pytest em `backend/tests/`, seguir o padrão de `test_rtneat_wrapper.py`
- Docs/comunicação em português (pt-BR); comentários no código só quando o "porquê" não é óbvio
- Não mexer no contrato de I/O do NEAT (`rtneat_wrapper.py` docstring / `neat_config.ini`) a menos que a spec explicitamente peça

Ao terminar, escreve um relatório em:
C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\.sdd\tasks\implementer\BIT-XX\impl-report-<topic>.md

Estrutura do relatório:
## Status
CONCLUÍDO | BLOQUEADO

## Passos executados
[lista dos passos da spec que foram executados]

## Arquivos modificados
[path completo + descrição da alteração para cada arquivo]

## Problemas encontrados
[divergências com a spec, decisões tomadas, código que difere do documentado]

## Próximos passos (se BLOQUEADO)
[o que impede a continuação e o que o developer precisa decidir]
```

**Regra crítica:** Se um sub-agente reportar `BLOQUEADO` → **PAUSE** e informe o developer antes de prosseguir. Não improvisar soluções não descritas na spec.

---

### 3. Ler relatórios de implementação

Se sub-agentes foram usados, leia todos os `impl-report-*.md`. Verifique:
- Todos os passos da spec foram cobertos
- Nenhum sub-agente reportou BLOQUEADO
- Não há conflitos entre as alterações

---

### 4. Gate de qualidade (obrigatório)

Execute os checks abaixo e corrija qualquer falha antes de declarar conclusão:

```powershell
# 1. Sintaxe/imports do backend
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend
venv\Scripts\python.exe -c "import main; print('OK - app importa')"

# 2. Testes do backend (pytest)
venv\Scripts\python.exe -m pytest tests/ -v

# 3. Se frontend foi tocado
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\frontend
npm run test
npm run build
```

Não avance com testes falhando ou erros de importação.

---

### 5. Validação funcional (se a mudança tem efeito observável na simulação)

Suba os serviços via `manager.py` (`manager.bat` ou `python manager.py` com o venv do backend ativo) e confirme manualmente que a simulação roda sem exceções por alguns segundos, e que o comportamento esperado pela spec é observável (ex: criaturas se movendo de forma não-determinística, comida sendo consumida, novos EGGs nascendo) — usar `manager.py` → Logs para acompanhar `backend.log` em busca de tracebacks.

Documente o resultado no relatório/evidência.

---

### 6. Gerar arquivo de evidência

Escrever `.sdd/tasks/implementer/BIT-XX/evidence.md`:

```markdown
# Evidência — BIT-XX: [Título da task]

**Data de conclusão:** YYYY-MM-DD

## Demanda atendida

[1-2 frases descrevendo o que foi entregue]

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `path/relativo` | criado \| modificado | descrição |

## Resultados dos gates de qualidade

- `import main`: OK
- `pytest tests/`: N passed
- `npm run test` / `npm run build` (se tocado): OK / N/A

## Como validar

[passos manuais para o developer confirmar que funciona, ex: manager.py -> Start Tudo -> abrir frontend -> o que observar]
```

---

### 7. Mover para `implemented/` e finalizar

Mover o diretório completo de `.sdd/tasks/implementer/BIT-XX/` para `.sdd/tasks/implemented/BIT-XX/` (spec + research + evidence.md juntos).

Informe o developer:
- Arquivos criados/modificados
- Resultado do gate de qualidade
- Como validar manualmente o que foi implementado
- Task movida para `.sdd/tasks/implemented/BIT-XX/`

---

## Portão de saída

- [ ] Todos os passos da spec executados (verificar contra `BIT-XX <Título Curto>.md`)
- [ ] `import main` sem erros
- [ ] `pytest backend/tests/` 100% verde
- [ ] `npm run test`/`npm run build` verdes (se frontend tocado)
- [ ] Nenhum `impl-report-*.md` com status BLOQUEADO
- [ ] Validação funcional feita via `manager.py` (se a mudança tem efeito observável)
- [ ] `evidence.md` gerado
- [ ] Diretório da task movido para `.sdd/tasks/implemented/BIT-XX/`
- [ ] Developer informado sobre como validar
