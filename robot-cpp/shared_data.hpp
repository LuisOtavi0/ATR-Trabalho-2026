#ifndef SHARED_STATE_HPP
#define SHARED_STATE_HPP

#include <mutex>
#include <condition_variable>
#include <vector>

struct LogEntry {
    long long timestamp;
    double x;
    double y;
    double nivel_confianca;
};

struct SharedState {
    bool e_automatico = true;
    bool e_inspecao   = false;

    bool o_liga_camera   = false;
    double aceleracao_saida = 0.0;

    double setpoint_velocidade = 0.0;
    double velocidade_atual    = 0.0;
    double distancia_total     = 0.0;

    double erro_acumulado = 0.0;
    double erro_anterior  = 0.0;

    const double Kp = 12.0;
    const double Ki = 0.4;
    const double Kd = 0.15;

    bool i_encoder = false;
    int  i_lidar   = 100;

    double imu_aceleracao_x = 0.0;
    double imu_angulo_pitch = 0.0;

    static const int TAMANHO_FILTRO = 5;
    std::vector<int> historico_lidar;
    double media_movel_teto      = 100.0;
    double limite_variacao_falha = 15.0;

    bool c_automatico_cmd  = false;
    bool c_man_cmd         = false;
    int  j_sp_velocidade_cmd = 2;
    bool c_direita_cmd     = false;
    bool c_esquerda_cmd    = false;
    bool c_para_cmd        = false;
    double limite_variacao_novo = -1.0;

    std::mutex mtx_navegacao;
    std::mutex mtx_sensores;
    std::mutex mtx_mqtt;

    std::condition_variable cv_camera;
};

#endif
