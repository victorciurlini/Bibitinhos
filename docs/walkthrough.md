# Walkthrough: CLI Manager & Automação de Testes

## O que foi construído
Nesta etapa (Sprint 2), com a aprovação do Product Owner e Tech Lead, criamos uma interface profissional em Python para gerenciar o ecossistema "Bibitinhos".

### 1. Infraestrutura de Testes
- **Backend:** Foi adicionado o `pytest`. Foi criado o teste `backend/tests/test_simulation.py` assegurando a viabilidade lógica de test-driven-development no motor Python.
- **Frontend:** O `vitest` foi incorporado no React, com o comando genérico `"test": "vitest run"` e o teste base `frontend/src/tests/App.test.jsx`.

### 2. A Ferramenta de CLI (TUI Manager)
Escrevemos o **`manager.py`**, uma interface de usuário de terminal extremamente polida usando as bibliotecas `rich` e `questionary`.

- **Painel de Status em Tempo Real:** Sempre que o menu renderiza, ele varre as portas 8000 e 5173 para checar e colorir o Status: `[ONLINE]` (Verde) e `[OFFLINE]` (Vermelho).
- **Abordagem Stateless & Background:** Ao iniciar os serviços (Start Backend/Frontend), eles rodam como processos *detached* nativos do Windows. As saídas são gravadas nos arquivos `backend.log` e `frontend.log` de forma silenciosa.
- **Process Killing Seguros:** Conforme o Tech Lead exigiu, o comando de *Stop* utiliza `taskkill /F /T /PID` e detecta as portas usando filtros rígidos (`LISTENING`) para evitar matar abas de navegador locais.

### 3. Integração de Sistema
O arquivo **`manager.bat`** foi incluído na raiz do seu projeto `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos\manager.bat`. Ele automaticamente ativa a VENV local do seu backend e dispara o Python, fornecendo uma porta de entrada amigável com zero de complexidade de terminal.

---

## Como Validar
1. Abra um terminal na pasta raiz original do seu projeto: `C:\Users\victo.000\OneDrive\Documentos\python\Bibitinhos`.
2. Dê um duplo-clique no arquivo `manager.bat` (ou rode ele no terminal).
3. Navegue no menu com as setas do teclado!
4. Use a função **Start All** para subir tudo, e então experimente **View Logs** ou abra seu navegador para ver o frontend rodando enquanto acompanha pelo painel se eles estão "ONLINE".
