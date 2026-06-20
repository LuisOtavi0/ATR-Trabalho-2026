# Sistema de Inspeção Robótica de Túneis — Arquitetura de Tempo Real

Este projeto constitui o Trabalho Final da disciplina Automação em Tempo Real (2026/1) do Departamento de Engenharia de Controle e Automação (DELT) da Escola de Engenharia da UFMG. O objetivo é o desenvolvimento de uma aplicação embarcada multitarefa para um robô autônomo de inspeção (Rover) voltado ao mapeamento e detecção de anomalias na integridade estrutural de túneis.

## 🚀 Visão Geral do Sistema

O sistema opera de forma distribuída e concorrente. Toda a inteligência de controle em tempo real (desenvolvida em C++) comunica-se de forma determinística com o Centro de Operação Remota e o Simulador do Ambiente Físico (desenvolvidos em Python) utilizando dois barramentos de rede assíncronos:

1. **Inter-Process Communication (IPC):** Realizado via **ZeroMQ (ZMQ)** com arquitetura REP/REQ para troca de dados síncrona de alta frequência (50Hz) entre a simulação física e as threads do robô.
2. **Rede Distribuída Pub/Sub:** Realizado via **MQTT (Mosquitto)** para envio de telemetria online do robô e recebimento de comandos do operador através do dashboard.

---

## 🛠️ Arquitetura de Software (Núcleo C++)

A aplicação embarcada gerencia **7 threads em paralelo** utilizando mecanismos nativos de exclusão mútua (`std::mutex`) e variáveis de condição (`std::condition_variable`) para gerenciar buffers concorrentes e sincronização de eventos:

| Módulo / Tarefa | Tipo | Período / Disparo | Função Principal |
| :--- | :--- | :--- | :--- |
| **Troca de Dados IPC (`ZMQ`)** | Cíclica | 20ms (50Hz) | Sincronismo de E/S de alta frequência com o simulador físico. |
| **Cálculo de Distância** | Cíclica | 20ms (50Hz) | Leitura do encoder para cálculo de odometria linear. |
| **Controle de Navegação** | Cíclica | 80ms (12.5Hz) | Algoritmo PID de velocidade responsável pelo acionamento dos motores. |
| **Comando de Navegação** | Cíclica | 80ms (12.5Hz) | Gestão de modos (Manual/Automático) e tradução de setpoints. |
| **Reconstrução de Superfície** | Cíclica | 100ms (10Hz) | Filtro de Média Móvel do LIDAR e detecção de variações severas do teto. |
| **Inspeção por Câmera** | Evento | Aperiódica | Processamento pesado simulando algoritmo de inteligência incorporada (YOLO). |
| **Coletor de Dados** | Bloqueante | Consumo FIFO | Análise de confiança online, registro em arquivo .jsonl e pub MQTT. |

---

## 💡 Recursos Avançados e Otimizações de Tempo Real

### Otimizações Críticas de Memória e CPU
- **Pooling de Texturas no Pygame:** A transferência de imagens do OpenCV para a interface gráfica foi otimizada via `pygame.pixelcopy.array_to_surface`, eliminando a alocação dinâmica de superfícies em tempo de execução. O uso de memória RAM permanece constante e linear.
- **Yielding Cooperativo:** A thread de processamento pesado da câmera realiza a simulação matemática exigida sem gerar *starvation* (fome de CPU) das rotinas de controle (PID) e rede (ZMQ), cedendo espaço por meio de `std::this_thread::yield()`.

### Recursos Visuais e de Engenharia Civil
- **Dashboard Industrial Dark Mode:** Interface gráfica unificada dividida em grades simétricas para visualização ergonômica de métricas de telemetria.
- **Gráfico Dinâmico do LIDAR:** Plotagem vetorial em tempo real da Máscara de Mapeamento 2D do túnel (Perfil de Altura $\times$ Posição Horizontal), mantendo o histórico cumulativo do percurso de forma estável.
- **Simulação de Túnel com Declive:** Integração física e visual do relevo da pista com a leitura do sensor IMU (Pitch), rotacionando o Rover realisticamente sobre o solo.
- **Injeção de Bounding Boxes:** Emulação estrutural de Visão Computacional desenhando caixas delimitadoras vermelhas diretamente sobre o feed de imagem ao identificar falhas (Buraco e Saliência).

---

## 📦 Como Compilar e Executar

A solução utiliza **Docker** e **Docker Compose** para orquestrar e isolar as dependências das linguagens e bibliotecas utilitárias (C++, Python, Mosquitto, ZeroMQ).

### Pré-requisitos
- Docker Desktop instalado e em execução.

### Passo a Passo para Execução Unificada
Para compilar o núcleo de tempo real, inicializar o broker MQTT local e levantar a interface supervisória com um único comando, execute na raiz do diretório do projeto:

```bash
docker compose up --build