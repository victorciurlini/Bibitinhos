# Bibites: Simulador de Vida Artificial Evolutiva

![Status](https://img.shields.io/badge/Status-Refinamento%20Concluído-green)
![Version](https://img.shields.io/badge/Versão-1.0-blue)
![Architecture](https://img.shields.io/badge/Arquitetura-Distribuída%20Cliente--Servidor-blue)

## 📊 Informações Técnicas

| Aspecto | Detalhes |
|--------|----------|
| **Padrão Arquitetural** | Distribuído (Cliente-Servidor) / OOP |
| **Backend** | Python + Pymunk (Motor Físico) |
| **Frontend** | Angular + Canvas/WebGL |
| **Comunicação** | WebSockets (60 ticks/segundo) |
| **Conteinerização** | Docker |
| **Execução Headless** | Suportada com aceleração de tempo |

---

## 📑 Sumário

- [1. Visão Geral do Produto](#1-visão-geral-do-produto)
- [2. Arquitetura de Software](#2-arquitetura-de-software)
- [3. Motor Físico e Espacial](#3-motor-físico-e-espacial)
- [4. Biologia e Entidades](#4-biologia-e-entidades)
- [5. Ecologia e Ambiente](#5-ecologia-e-ambiente)
- [6. Sistema Cognitivo Evolutivo](#6-sistema-cognitivo-evolutivo)
- [7. Estrutura de Classes (OOP)](#7-estrutura-de-classes-oop)
- [8. Plano de Implementação](#8-plano-de-implementação-incremental)

---

## 1. Visão Geral do Produto

O sistema é um **simulador de ecossistemas 2D de alta performance** focado em **evolução por seleção natural** e **inteligência emergente**.

### Características Principais

- **Sem Scripts Comportamentais**: Inteligência puramente emergente via redes neurais
- **Redes Neurais Evolutivas (rtNEAT)**: Topologia mutável e auto-adaptativa
- **Simulação Física Realística**: Mecânica newtoniana 2D contínua
- **Comportamentos Complexos**: Sobrevivência, nomadismo, uso de apêndices e reprodução sexuada
- **Evolução Natural**: Seleção natural pura, sem métricas artificiais

---

## 2. Arquitetura de Software

A arquitetura **separa estritamente** o motor lógico da visualização, permitindo escalabilidade e execução desacoplada.

### 2.1 Backend (Motor de Simulação - Python)

- **Responsabilidade**: 100% da lógica de negócio, física e IA
- **Motor Físico**: Pymunk (C-based, alta performance)
- **Processamento Paralelo**: Multiprocessing para cálculos genéticos isolados
- **Stream de Dados**: WebSocket a 60 ticks/segundo
- **Ciclo de Loop**: Orquestrado por `SimulationManager`

### 2.2 Frontend (Camada de Observabilidade - Angular)

- **Responsabilidade**: Visualização e interface de usuário
- **Renderização**: HTML5 Canvas ou WebGL
- **Consumo**: Payload JSON via WebSocket
- **Funcionalidades**: 
  - Painéis de métricas em tempo real
  - Gráficos populacionais
  - Inspetor de redes neurais

### 2.3 Modo Headless (Execução Acelerada)

- **Funcionamento**: Motor sem camada visual
- **WebSocket**: Desativado para melhor performance
- **Use Cases**: Treinamento de IA, saltos geracionais em background

---

## 3. Motor Físico e Espacial

A simulação é fundada em **mecânica newtoniana 2D**. Todas as entidades colidem, possuem massa, inércia e limites de torque.

### 3.1 Gestão de Tempo

- **Delta Time Variável**: Renderização cliente-side
- **Ticks de Física Constantes**: Servidor mantém integridade dos cálculos
- **Benefício**: Evita transposição de polígonos e erros de colisão

### 3.2 Otimização de Corpos Rígidos

| Entidade | Colisor | Razão |
|----------|---------|-------|
| **Oásis** | Círculo | Custo computacional mínimo |
| **Comida** | Círculo | Performance |
| **Ovos** | Círculo | Simplicidade |
| **Bibites** | Cápsula | Deslizamento fluido em manadas |

### 3.3 Acoplamento Físico e Inventário

- **Sem Memória Abstrata**: Itens não vão para "slots"
- **Junta Dinâmica**: `Weld Joint` acopla item ao bibite
- **Física Integrada**: Massa do item soma-se ao corpo
- **Impacto**: Inércia aumenta, velocidade reduz, comportamentos cinéticos emergem (roubos, "cabo de guerra")

---

## 4. Biologia e Entidades

### 4.1 Morfologia e Simetria

Toda mutação morfológica ocorre sob **Simetria Bilateral Forçada**:

- ✓ Mantém Centro de Massa alinhado
- ✓ Impede torques laterais indesejados
- ✓ Garante locomoção viável após mutações
- **Controle Motor**: Vetorial (aceleração + rotação no eixo)

### 4.2 Máquina de Estados - Ciclo de Vida

| Estado | Descrição |
|--------|-----------|
| **🥚 EGG** | Inerte, estático; contador regressivo (hatch_timer); dreno basal de energia de incubação |
| **👶 JUVENILE** | Ativo inicial; motor e sensores ligados; foco em ganho calórico; sistema reprodutivo inativo |
| **🦁 ADULT** | Pico metabólico (1.0x); gatilhos hormonais liberados; permite reprodução sexuada |
| **👴 ELDER** | Degradação progressiva; queima massiva de energia; visão periférica reduzida; caminha para inanição |
| **💀 DEAD** | Colapso neural; corpo regido apenas por inércia; será descartado/reabsorvido |

---

## 5. Ecologia e Ambiente

### 5.1 OasisManager - Biomas Efêmeros

O ecossistema incentiva **nomadismo** através de zonas dinâmicas:

- **Áreas de Fertilidade Invisíveis**: Governadas por Time to Live (TTL)
- **Spawn Randomizado**: Geração de `Food` dentro de limites de saturação
- **Pressão de Seleção**: Desaparecimento de oásis força movimento, punindo sedentarismo
- **Taxa de Reprodução**: Variável conforme densidade de recursos

### 5.2 "Jardim do Éden" - Failsafe Crítico

**Acionamento**: População total < 10 indivíduos

**Resposta do Sistema**:
- Gera oásis **altamente densos** nas coordenadas dos sobreviventes
- Garante **tração inicial** no desenvolvimento genético
- Previne **extinção completa** do modelo

---

## 6. Sistema Cognitivo Evolutivo

### 6.1 Matriz de I/O e Genes Adormecidos

Para evitar quebra das matrizes matemáticas durante mutações, usa-se **pré-alocação estática com ativação progressiva**.

#### Camada de Entrada (Inputs)

| Sensor | Tipo | Descrição |
|--------|------|-----------|
| **Visual_Sectors[0..8]** | Binário | Até 9 cones visuais; Gen 0: apenas 3 ativos, resto recebe -1.0 |
| **Energy_Level** | Float | Escala 0.0 a 1.0 |
| **Age_Degradation** | Float | Escala 0.0 a 1.0 |
| **Hormonal_Level** | Float | Fertilidade (ativo apenas em ADULT) |
| **Biological_Clock** | Senoidal | Oscilador para evitar paralisia decisória |
| **Load_Sensor** | Categórico | 0.0 (vazio), 0.5 (comida), 1.0 (ovo) |
| **Kinetic_Feedback** | Vetor | Aceleração atual do motor físico |

#### Camada de Saída (Outputs)

| Output | Tipo | Descrição |
|--------|------|-----------|
| **Motor_Forward** | Contínuo | Aceleração frontal (positiva/negativa) |
| **Motor_Torque** | Contínuo | Rotação esquerda/direita |
| **Action_Grab_Drop** | Binário | Gatilho da junta física da boca |
| **Action_Mate** | Binário | Gatilho biológico de procriação |

### 6.2 Motor Evolutivo (rtNEAT)

#### Topologia Mutável

- **Algoritmo**: Real-Time NeuroEvolution of Augmenting Topologies
- **Crescimento**: Neurônios ocultos surgem esporadicamente
- **Sincronização Global**: Números de Inovação Histórica (Innovation IDs)
- **Gen 0**: Conexão direta Input → Output

#### Métrica de Fitness

- **Puramente Natural**: Sem pontuação artificial
- **Medida**: Estar vivo + depositar material genético
- **Seleção**: Natural, implícita no sistema

#### Reprodução Sexuada e Crossover

```
Dois ADULT + colisão física + Action_Mate ativado
    ↓
Processo de fertilização interrompe motores
    ↓
Crossover de DNA baseado em Innovation IDs
    ↓
Progenitor dominante definido por:
  • Volume de energia momentânea
  • Idade no instante do acasalamento
    ↓
Prole gerada como EGG com topologia híbrida
```

---

## 7. Estrutura de Classes (OOP)

### 7.1 Módulo Core (Engine)

```
SimulationManager
├─ Singleton orquestrando o Game Loop
├─ Englobamento do PhysicsEngine
└─ Broadcast JSON via WebSocket

OasisManager
├─ Temporizadores assíncronos
├─ Criar/destruir polígonos de zona fértil
└─ Gerenciar arrays de Food

NeatManager
├─ Repositório genético global
├─ Inovações históricas
└─ Matemática de crossover
```

### 7.2 Camada de Entidades

```
Entity (Classe Base Abstrata)
├─ ID
├─ Coordinate
└─ RigidBody

Bibite (Extends Entity)
│
├─ 🧬 Metabolism
│  ├─ Consumo passivo vs ativo
│  ├─ Máquina de estados (EGG → DEAD)
│  └─ Gatilhos de ciclo de vida
│
├─ 🧠 NeuralBrain
│  └─ Feedforward rtNEAT
│
├─ 👁️ SensorModule
│  └─ Colisões Pymunk → arrays escalares
│
└─ ⚙️ ActuatorModule
   ├─ apply_force() e torque
   └─ Restrições de junta no espaço físico
```

---

## 8. Plano de Implementação Incremental

### Milestone 1: O Aquário Físico e a Ponte de Dados

**Tema**: Infraestrutura física e comunicação

**Tarefas**:
1. Inicialização Python + Angular
2. Motor físico Pymunk com Delta Time
3. Objetos `Food` e colisores
4. Servidor WebSocket para transmissão de estado

**Validação**: 
- ✓ Frontend renderiza corpos físicos perfeitamente
- ✓ Entidades interagem, envelhecem e desaparecem

---

### Milestone 2: O Despertar Sensorial

**Tema**: IA e Integração Sensório-Motora

**Tarefas**:
1. Implementar `SensorModule`
2. Converter visão e colisões em arrays estruturados
3. Rede neural fixa provisória
4. Acoplamento de atuadores mecânicos

**Validação**:
- ✓ Reprodução assexuada (clonagem) funciona
- ✓ Entidades viram e aceleram em direção a comida
- ✓ Demonstração de aprendizado básico

---

### Milestone 3: A Dança do Acasalamento (rtNEAT)

**Tema**: Evolução genética e reprodução

**Tarefas**:
1. Remoção da IA provisória
2. Injeção completa do motor matemático rtNEAT
3. Acasalamento sexual por colisão (ADULT)
4. Sistema de `EGG` e herança genética
5. Genes adormecidos (expansão visual, atributos de massa)

**Validação**:
- ✓ Simulação estável por 24+ horas sem memory leaks
- ✓ População auto-regulada
- ✓ Mutações contínuas sem crashes

---

### Milestone 4: Observabilidade e Otimização Final

**Tema**: Interface, Observabilidade e Deploy

**Tarefas**:
1. Componentes Angular para painéis de métricas
2. Inspetor interativo: clicar em polígono → visualizar rede neural em tempo real
3. Conteinerização final via Docker
4. Refinamento dos biomas dinâmicos
5. Preparação para implantação

**Validação**:
- ✓ Simulação remota com aceleração headless
- ✓ Observabilidade completa (linhagens, população, métricas)
- ✓ Pipeline CI/CD funcional