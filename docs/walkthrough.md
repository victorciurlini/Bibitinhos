# Walkthrough: Épico 2 - O Motor de Física e Evolução (Bibitinhos Core)

## O que foi construído
Com a fundação do projeto garantida, introduzimos o sistema nervoso e as leis da física no mundo dos Bibitinhos, integrando perfeitamente a **Inteligência Artificial (NEAT)** ao **Pymunk (Box2D Python)**.

### 1. Física Contínua (`physics.py` e `pymunk`)
- O motor de posições estáticas foi descartado e substituído pela biblioteca nativa C `pymunk`.
- O mundo agora é uma caixa delimitada de **2000x2000** coordenadas (sem gravidade). 
- Foi adicionado um **Damping (Atrito) de 0.9** no vácuo para impedir acelerações infinitas e *tunneling* em altas velocidades.
- Os *Bibitinhos* deixaram de ser coordenadas puras e tornaram-se `pymunk.Body`, sujeitos a **Massa (1.0)**, **Torque** e colisões elásticas contra as paredes e uns aos outros.

### 2. Integração do NEAT Orgânico (`rtneat_wrapper.py`)
- Em vez de usar as "Gerações" lentas e bloqueantes da biblioteca padrão, abstraímos os módulos matemáticos (`crossover`, `mutate`) para que a evolução ocorra em modo **Real-Time NEAT (rtNEAT)**.
- O genoma é gerado sob demanda, visando o futuro cruzamento dinâmico que ocorrerá no ato da colisão física entre dois seres maduros de alta energia.

### 3. Adaptações do React / Frontend
O componente `SimulationCanvas.jsx` foi vastamente expandido:
- **Centralização Escalável (Viewport):** O Front lê as dimensões do mundo recebidas pelo WebSocket (`2000x2000`) e usa `ctx.scale()` para "expremer" a visualização inteira para dentro da resolução atual do seu monitor de forma responsiva.
- **Geometria de Rotação:** Antes eram apenas círculos. Agora, as criaturas renderizam um **Vetor Visual** (uma linha reta espessa saindo do meio da forma) indicando com precisão trigonométrica o ângulo em que a física e o "olho" da criatura estão apontando.

---

## Como Validar
1. Inicie a aplicação com o **`manager.bat`** (clique em "Start Tudo").
2. Abra o painel do Frontend no seu navegador. 
3. Você visualizará as entidades aparecendo no plano 2000x2000 escalado perfeitamente na sua tela. Os corpos reagem à engine nativa de C, demonstrando inércia e limites de espaço, além de exporem graficamente sua orientação e estado.
