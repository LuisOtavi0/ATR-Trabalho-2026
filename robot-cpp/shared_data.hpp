#ifndef SHARED_DATA_HPP
#define SHARED_DATA_HPP

#include <mutex>
#include <vector>
#include <string>
#include <chrono>

// Estrutura para o Coletor de Dados [cite: 95]
struct LogEntry {
    long long timestamp;
    double x, y;
    double nivel_confianca;
};

// Dados compartilhados protegidos por Mutex
struct SharedState {
    // Estado do Robô [cite: 123]
    bool e_automatico = false;
    bool e_inspecao = false;
    double setpoint_velocidade = 0.0;
    double velocidade_atual = 0.0;
    double distancia_total = 0.0;
    // No shared_data.hpp, dentro da struct SharedState:
    double erro_acumulado = 0.0;
    double erro_anterior = 0.0;
    double aceleracao_saida = 0.0; // o_aceleracao (-100 a 100%) 

    // Ganhos do PID (valores iniciais para ajuste)
    const double Kp = 10.0; 
    const double Ki = 0.5;
    const double Kd = 0.1;

    // Sensores simulados [cite: 119]
    bool i_encoder = false;
    int i_lidar = 0;

    // Buffers e Mutexes [cite: 20, 90]
    std::mutex mtx;
    std::vector<LogEntry> buffer_coletor;
};

#endif