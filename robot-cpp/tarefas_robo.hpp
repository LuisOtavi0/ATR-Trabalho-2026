#ifndef TAREFAS_ROBO_HPP
#define TAREFAS_ROBO_HPP

#include "shared_data.hpp"
#include "buffer_concorrente.hpp"

// Instância global do estado do robô compartilhada entre as tarefas
extern SharedState state;

// Instância global do buffer concorrente para comunicação Reconstrução -> Coletor
extern BufferConcorrente buffer_telemetria;

// (Período: 80 ms)
void task_comando_navegacao();

// (Período: 80 ms)
void task_controle_navegacao();

// (Período: 20 ms)
void task_calculo_distancia();

// (Período: 100 ms)
void task_reconstrucao_superficie();

// YOLO
void task_inspecao_camera();

// (Período: 500 ms)
void task_coletor_dados();

#endif