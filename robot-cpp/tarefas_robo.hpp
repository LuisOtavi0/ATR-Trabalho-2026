#ifndef TAREFAS_ROBO_HPP
#define TAREFAS_ROBO_HPP

#include "shared_data.hpp"
#include "buffer_concorrente.hpp"

// Forward declaration para evitar incluir mosquitto.h em todo lugar
struct mosquitto;

extern SharedState state;
extern BufferConcorrente buffer_telemetria;
extern struct mosquitto* g_mqtt_client;

// (Período: 80 ms) Recebe comandos MQTT e define setpoints
void task_comando_navegacao();

// (Período: 80 ms) Controlador PID de velocidade
void task_controle_navegacao();

// (Período: 20 ms) Lê encoder para calcular distância percorrida
void task_calculo_distancia();

// (Período: 100 ms) Filtro MA + detecção de anomalias + produz no buffer
void task_reconstrucao_superficie();

// (Assíncrona) Aguarda cv_camera e executa processamento pesado (YOLO)
void task_inspecao_camera();

// (Assíncrona, bloqueante no buffer) Consome buffer, grava disco, publica MQTT
void task_coletor_dados();

// (Período: 20 ms) Troca dados IPC com o simulador Python via ZeroMQ
void task_ipc_exchange();

#endif
