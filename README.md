# Sistema de Inspeção Robótica de Túneis - Etapa 1

Este projeto faz parte da disciplina de Automação em Tempo Real da UFMG. O objetivo é desenvolver o software de controle e monitoramento de um robô de inspeção estrutural.

## 🚀 Status da Etapa 1

Conforme os requisitos, foram implementadas todas as **Tarefas Azuis** (Arquitetura do Robô) utilizando C++ moderno e threads POSIX. O sistema opera de forma multitarefa e concorrente, garantindo os requisitos de periodicidade de tempo real.

## 🛠️ Arquitetura do Sistema

O software é composto por 6 threads principais que se comunicam via memória compartilhada protegida por **Mutexes** (Exclusão Mútua):

| Tarefa                         | Tipo    | Período    | Função Principal                                         |
| :----------------------------- | :------ | :--------- | :------------------------------------------------------- |
| **Cálculo de Distância**       | Cíclica | 20ms       | Integração da velocidade e simulação do encoder.         |
| **Controle de Navegação**      | Cíclica | 80ms       | Algoritmo PID para controle de aceleração/velocidade.    |
| **Comando de Navegação**       | Cíclica | 80ms       | Gestão de estados (Manual/Automático) e setpoints.       |
| **Reconstrução de Superfície** | Cíclica | 100ms      | Filtro de Média Móvel e Detecção de Falhas Estruturais.  |
| **Coletor de Dados**           | Cíclica | 500ms      | Telemetria e persistência em buffer de memória.          |
| **Inspeção por Câmera**        | Evento  | Aperiódica | Simulação de processamento pesado (CPU Bound) de imagem. |

## 🧪 Funcionalidades Implementadas

- **Controle PID:** Ajuste dinâmico da aceleração para manter o setpoint de velocidade.
- **Filtro Digital:** Média móvel para suavização de ruído nas leituras do sensor LIDAR.
- **Sincronização RAII:** Uso de `std::lock_guard` para garantir que o acesso aos dados seja thread-safe.
- **Simulação Estocástica:** Inserção aleatória de falhas (buracos) no teto para teste de robustez da detecção.

## 📦 Como Executar

O projeto utiliza **Docker** para garantir que o ambiente de execução seja idêntico para todos os colaboradores, eliminando problemas de dependências locais.

1. Certifique-se de ter o Docker e Docker Compose instalados.
2. Na raiz do projeto, execute:
   ```bash
   docker-compose up --build
   ```
