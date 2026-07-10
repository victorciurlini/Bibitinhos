Você é o implementer do projeto Financeiro. Execute a spec.md aprovada, paralelizando via sub-agentes o que for independente.

**Pré-condição:** diretório `.sdd/tasks/FIN-XX/` com `spec.md` existente.

> O status da task (Backlog → In Progress → Done) é gerenciado no Linear, não na spec.md.

---

## Protocolo

### 1. Identificar tarefa e ler spec

**Se o argumento for um ID Linear (ex: `FIN-35`):**
- Abrir diretamente `.sdd/tasks/FIN-35/spec.md`
- Se o diretório não existir, informar o developer que a task não foi refinada ainda

**Se nenhum argumento for fornecido:**
- Listar os diretórios em `.sdd/tasks/FIN-*/` (ignorar `WIP-*` — ainda em refinamento)
- Se houver mais de um, perguntar ao developer qual implementar

Leia a **spec.md completa** antes de qualquer edição de código.

**Atualizar o status no Linear para "In Progress"** usando `mcp__plugin_linear_linear__save_issue` com o ID da spec (campo `**Linear:**`) e `state: "In Progress"`.

---

### 2. Planejar execução paralela

Analise os passos da spec.md e classifique:
- **Independentes:** sem dependência entre si → podem ser executados em paralelo por sub-agentes
- **Dependentes:** requerem output de outro passo → executar sequencialmente após os independentes terminarem

Lance sub-agentes do tipo `claude` em paralelo para cada grupo de passos independentes.

**Prompt padrão para cada sub-agente de implementação:**

```
Contexto:
- Projeto: Financeiro (dashboard web pessoal)
- Caminho base: C:\Users\victo.000\OneDrive\Documentos\Financeiro
- Stack: Python 3.10 + Flask 3.0 + SQLite + Vanilla JS + Chart.js

Spec completa:
[incluir conteúdo integral da spec.md]

Passos atribuídos a este sub-agente:
[passos específicos da spec]

Convenções obrigatórias:
- Python: sem ORM, sem Pandas no backend web; usar sqlite3 nativo com row_factory
- SQL: valores monetários negativos = débito, positivos = crédito; excluir is_iof=1 e cat.nome='Pagamentos/Créditos' nas queries de gasto
- Flask: todos os endpoints retornam JSON no padrão {status, data, metadata}; usar get_db() de core/db_connection.py
- JS: sem frameworks; estado global em AppState; fetch via apiFetch(); charts via Chart.js 4.4
- CSS: usar variáveis CSS definidas em main.css; dark mode glassmorphism
- Nunca abrir conexão SQLite diretamente nas rotas — sempre via get_db()
- Nunca escrever no banco (read-only via URI mode)

Ao terminar, escreve um relatório em:
C:\Users\victo.000\OneDrive\Documentos\Financeiro\.sdd\tasks\FIN-XX\impl-report-<topic>.md

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

OBRIGATÓRIO: escreve o relatório antes de terminar.
```

**Regra crítica:** Se um sub-agente reportar `BLOQUEADO` → **PAUSE** e informe o developer antes de prosseguir. Não improvisar soluções não descritas na spec.

---

### 3. Ler relatórios de implementação

Após todos os sub-agentes terminarem, leia todos os arquivos `impl-report-*.md`. Verifique:
- Todos os passos da spec foram cobertos
- Nenhum sub-agente reportou BLOQUEADO
- Não há conflitos entre as alterações dos sub-agentes

---

### 4. Gate de qualidade (obrigatório)

Execute os checks abaixo e corrija qualquer falha antes de declarar conclusão:

```powershell
# 1. Verificação de sintaxe Python (todos os .py tocados)
cd C:\Users\victo.000\OneDrive\Documentos\Financeiro\web_app
python -c "from run import app; print('OK — rotas:', len(list(app.url_map.iter_rules())))"

# 2. Se ETL foi tocado — verificar que importa sem erro
cd C:\Users\victo.000\OneDrive\Documentos\Financeiro\financeiro_xlsx
python -c "import config; import database; print('ETL imports OK')"

# 3. Se banco foi tocado — confirmar que DB abre em read-only
python -c "
import sqlite3
from pathlib import Path
db = Path(r'C:\Users\victo.000\OneDrive\Documentos\Financeiro\financeiro_xlsx\financeiro.db')
conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
print('DB OK — tabelas:', [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])
conn.close()
"
```

Não avance com erros de importação ou sintaxe.

---

### 5. Validação funcional (se camada Frontend ou Backend)

Se a tarefa tocou Flask ou frontend, suba o servidor e confirme manualmente:

```powershell
cd C:\Users\victo.000\OneDrive\Documentos\Financeiro\web_app
python run.py
# Abrir http://localhost:5000 e verificar o fluxo principal da tarefa
```

Documente o resultado da validação no relatório de implementação.

---

### 6. Gerar arquivo de evidência

Escrever `.sdd/tasks/FIN-XX/evidence.md` com o seguinte conteúdo:

```markdown
# Evidência — FIN-XX: [Título da task]

**Data de conclusão:** YYYY-MM-DD
**Linear:** FIN-XX

## Demanda atendida

[1-2 frases descrevendo o que foi entregue]

## Arquivos criados/modificados

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `path/relativo` | criado \| modificado | descrição |

## Resultados dos gates de qualidade

- `from run import app`: OK — N rotas
- ETL imports: OK (se tocado) / N/A
- DB: OK — tabela `X` presente (se tocado) / N/A

## Como validar

[passos manuais para o developer confirmar que funciona]
```

---

### 7. Finalizar

- Atualizar o status no Linear para **Done** usando `mcp__plugin_linear_linear__save_issue` com `state: "Done"`
- Informe o developer:
  - Arquivos criados/modificados
  - Resultado do gate de qualidade
  - Como validar manualmente o que foi implementado
  - Linear `FIN-XX` marcado como Done

---

## Portão de saída

- [ ] Todos os passos da spec executados (verificar contra spec.md)
- [ ] `python -c "from run import app"` sem erros
- [ ] Nenhum `impl-report-*.md` com status BLOQUEADO
- [ ] `evidence.md` gerado em `.sdd/tasks/FIN-XX/`
- [ ] Linear `FIN-XX` atualizado para Done
- [ ] Developer informado sobre como validar
