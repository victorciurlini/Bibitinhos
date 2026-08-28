Você é o implementer do projeto Bibitinhos (simulador de vida artificial evolutiva). Execute a spec aprovada de uma task `BIT-XX`, paralelizando via sub-agentes o que for independente.

**Pré-condição:** diretório `.sdd/tasks/refiner/BIT-XX/` com um arquivo `BIT-XX <Título Curto>.md` existente (spec aprovada pelo developer).

**Sem Linear:** o status da task é o **próprio diretório** — mover a pasta entre `refiner/` → `implementer/` → `implemented/` é como o progresso é rastreado (ver memória `bibitinhos-tasks-folder-state-model`). Não criar/atualizar nada no Linear.

---

## Protocolo

### 1. Criar branch BIT-XX (PRIMEIRO PASSO — antes de tocar qualquer código)

**Este é o passo zero. Nenhum arquivo de código é tocado antes da branch existir.**

```powershell
# Certifique-se de estar na raiz do projeto
git branch --show-current   # confirme onde está

# Parta sempre de develop atualizado
git checkout develop
git pull origin develop

# Crie a branch da task
git checkout -b BIT-XX      # substitua XX pelo número real
```

> **Por que antes?** Incidente histórico: BIT-21 e BIT-22 foram implementados na branch errada porque o agente criou a branch só no final. Toda implementação começa neste passo.

---

### 2. Identificar tarefa e mover para `implementer/`

**Se o argumento for um ID (ex: `BIT-02`):**
- Procurar `.sdd/tasks/refiner/BIT-02/`
- Se não existir lá, checar se já está em `.sdd/tasks/implementer/BIT-02/` (retomando um implementer interrompido)
- Se não existir em nenhuma das duas, informar o developer que a task não foi refinada ainda

**Se nenhum argumento for fornecido:**
- Listar os diretórios em `.sdd/tasks/refiner/BIT-*/`
- Se houver mais de um, perguntar ao developer qual implementar

Mover o diretório de `.sdd/tasks/refiner/BIT-XX/` para `.sdd/tasks/implementer/BIT-XX/` (git mv se estiver versionado, senão mover no filesystem) — isso sinaliza visualmente que a implementação está em andamento.

Leia a **spec completa** (`BIT-XX <Título Curto>.md`) antes de qualquer edição de código. Note o campo `**Tipo:**` da spec — ele define se o bump de versão será `minor` (feature) ou `patch` (fix).

**Atenção a concorrência:** se este mesmo diretório de trabalho tiver outra sessão de implementer ativa em paralelo (outra branch/chat mexendo nos mesmos arquivos), confirme com o developer antes de prosseguir — editar `creature.py`/`engine.py` simultaneamente em duas sessões causa conflito.

---

### 3. Planejar execução paralela

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

### 4. Ler relatórios de implementação

Se sub-agentes foram usados, leia todos os `impl-report-*.md`. Verifique:
- Todos os passos da spec foram cobertos
- Nenhum sub-agente reportou BLOQUEADO
- Não há conflitos entre as alterações

---

### 5. Gate de qualidade (obrigatório)

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

### 6. Validação funcional (se a mudança tem efeito observável na simulação)

Suba os serviços via `manager.py` (`manager.bat` ou `python manager.py` com o venv do backend ativo) e confirme manualmente que a simulação roda sem exceções por alguns segundos, e que o comportamento esperado pela spec é observável (ex: criaturas se movendo de forma não-determinística, comida sendo consumida, novos EGGs nascendo) — usar `manager.py` → Logs para acompanhar `backend.log` em busca de tracebacks.

Documente o resultado no relatório/evidência.

---

### 7. Gerar arquivo de evidência

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

### 8. Commit, push e merge para develop

Com o gate verde, commite as alterações na branch `BIT-XX` e integre em `develop`:

```bash
# 8.1 Commit na branch BIT-XX
git add <arquivos modificados>    # adicione seletivamente — nunca git add -A cego
git commit -m "feat(BIT-XX): <título curto da task>"
# Use "fix(BIT-XX):" se o tipo da spec for fix

# 8.2 Push da branch para o remoto
git push -u origin BIT-XX

# 8.3 Merge em develop (sem fast-forward — preserva a topologia da branch)
git checkout develop
git pull origin develop           # garantir develop atualizado antes do merge
git merge --no-ff BIT-XX -m "merge(BIT-XX): <título curto da task>"
git push origin develop

# 8.4 Rodar a suíte em develop (gate pós-merge)
cd C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\backend
venv\Scripts\python.exe -c "import main; print('OK')"
venv\Scripts\python.exe -m pytest tests/ -v
```

Se os testes em `develop` falharem: **NÃO avance**. Investigue a causa — pode ser conflito de merge ou regressão introduzida — e corrija antes de continuar.

---

### 9. Bump de versão

Após `develop` verde, aplique o bump de versão conforme o campo `**Tipo:**` da spec:

| Tipo da spec | Regra semver | Exemplo |
|---|---|---|
| `feature` | incrementa `minor`, zera `patch` | `0.2.0` → `0.3.0` |
| `fix` | incrementa `patch` | `0.2.0` → `0.2.1` |
| (major só por decisão explícita do developer — nunca automático) | | |

```bash
# Ler versão atual
current=$(cat VERSION)          # ex: 0.2.0
IFS='.' read -r major minor patch <<< "$current"

# Para feature:
minor=$((minor + 1)); patch=0
# Para fix:
# patch=$((patch + 1))

new_version="$major.$minor.$patch"

# Atualizar VERSION (fonte canônica)
echo "$new_version" > VERSION

# Atualizar frontend/package.json (manter em sincronia)
# Use sed ou edite diretamente:
sed -i "s/\"version\": \"$current\"/\"version\": \"$new_version\"/" frontend/package.json

# Commit do bump
git add VERSION frontend/package.json
git commit -m "chore: bump version $current → $new_version (BIT-XX)"
git push origin develop

# Tag no develop
git tag "v$new_version"
git push origin "v$new_version"
```

---

### 10. Mover para `implemented/` e finalizar

Mover o diretório completo de `.sdd/tasks/implementer/BIT-XX/` para `.sdd/tasks/implemented/BIT-XX/` (spec + research + evidence.md juntos).

Informe o developer:
- Arquivos criados/modificados
- Resultado do gate de qualidade (branch BIT-XX + develop pós-merge)
- Versão bumpeada: `X.Y.Z → X.Y+1.Z` (feature) ou `X.Y.Z → X.Y.Z+1` (fix)
- Tag criada: `vX.Y.Z`
- Como validar manualmente o que foi implementado
- Task movida para `.sdd/tasks/implemented/BIT-XX/`

---

## Portão de saída

- [ ] Branch `BIT-XX` criada **antes** de qualquer código editado
- [ ] Todos os passos da spec executados (verificar contra `BIT-XX <Título Curto>.md`)
- [ ] `import main` sem erros
- [ ] `pytest backend/tests/` 100% verde na branch BIT-XX
- [ ] `npm run test`/`npm run build` verdes (se frontend tocado)
- [ ] Nenhum `impl-report-*.md` com status BLOQUEADO
- [ ] Validação funcional feita via `manager.py` (se a mudança tem efeito observável)
- [ ] `evidence.md` gerado
- [ ] Branch `BIT-XX` commitada e pushed para origin
- [ ] Merge `--no-ff` em `develop` + push
- [ ] `pytest` verde em `develop` pós-merge
- [ ] `VERSION` e `frontend/package.json` bumpeados e commitados em `develop`
- [ ] Tag `vX.Y.Z` criada e pushada
- [ ] Diretório da task movido para `.sdd/tasks/implemented/BIT-XX/`
- [ ] Developer informado sobre como validar
