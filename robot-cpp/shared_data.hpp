#ifndef SHARED_DATA_HPP
#define SHARED_DATA_HPP

#include <mutex>
#include <vector>
#include <string>
#include <chrono>

struct LogEntry {
    long long timestamp;
    double x, y;
    double nivel_confianca;
};

struct SharedState {
    bool e_automatico = false;
    bool e_inspecao = false;
    double setpoint_velocidade = 0.0;
    double velocidade_atual = 0.0;
    double distancia_total = 0.0;
    
    bool buraco_detectado_no_sensor = false;
    int duracao_buraco = 0;

    double erro_acumulado = 0.0;
    double erro_anterior = 0.0;
    double aceleracao_saida = 0.0;

    static const int TAMANHO_FILTRO = 5;
    std::vector<int> historico_lidar;
    double media_movel_teto = 0.0;

    double limite_variacao_falha = 15.0;

    const double Kp = 10.0; 
    const double Ki = 0.5;
    const double Kd = 0.1;

    bool i_encoder = false;
    int i_lidar = 0;

    std::mutex mtx;
    std::vector<LogEntry> buffer_coletor;
};

#endif