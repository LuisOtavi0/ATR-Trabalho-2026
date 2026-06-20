#ifndef TAREFAS_ROBO_HPP
#define TAREFAS_ROBO_HPP

#include "shared_data.hpp"
#include "buffer_concorrente.hpp"

struct mosquitto;

extern SharedState state;
extern BufferConcorrente buffer_telemetria;
extern struct mosquitto* g_mqtt_client;

void task_comando_navegacao();

void task_controle_navegacao();

void task_calculo_distancia();

void task_reconstrucao_superficie();

void task_inspecao_camera();

void task_coletor_dados();

void task_ipc_exchange();

#endif
