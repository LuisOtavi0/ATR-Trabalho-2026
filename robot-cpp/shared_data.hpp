#ifndef SHARED_STATE_HPP
#define SHARED_STATE_HPP

#include <mutex>
#include <condition_variable>
#include <vector>

// Estrutura de dados para o Coletor de Dados
struct LogEntry {
    long long timestamp; // Tempo em milissegundos
    double x;            // Posição horizontal do robô
    double y;            // Distância medida até o teto
    double nivel_confianca; // Cálculo online de confiabilidade
};

// Estrutura global compartilhada pelas Threads do Robô
struct SharedState {
    // --- ESTADOS DE OPERAÇÃO ---
    bool e_automatico = false; // Modos de operação (0: manual, 1: automático)
    bool e_inspecao = false;   // Indica falha detectada e inspeção ativa
    
    // --- DINÂMICA E CONTROLE (PID) ---
    double setpoint_velocidade = 0.0; // Velocidade desejada
    double velocidade_atual = 0.0;    // Velocidade real calculada
    double distancia_total = 0.0;     // Distância acumulada (X)
    double aceleracao_saida = 0.0;    // Sinal de controle para os motores (-100 a 100%)

    double erro_acumulado = 0.0;      // Termo Integrador do PID
    double erro_anterior = 0.0;       // Termo Derivativo do PID

    // --- PARÂMETROS DO PID ---
    const double Kp = 12.0; 
    const double Ki = 0.4;
    const double Kd = 0.15;

    // --- DADOS DOS SENSORES EMULADOS ---
    bool i_encoder = false;           // Altera estado a cada metro
    int i_lidar = 0;                  // Leitura vertical atual
    
    // BÔNUS: Dados do Sensor IMU (Unidade de Medição Inercial)
    double imu_aceleracao_x = 0.0;    // Aceleração linear no eixo de movimento
    double imu_angulo_pitch = 0.0;    // Ângulo de inclinação do robô (para detectar declives)

    // --- RECONSTRUÇÃO DE SUPERFÍCIE ---
    static const int TAMANHO_FILTRO = 5;
    std::vector<int> historico_lidar; // Janela para o filtro de média móvel
    double media_movel_teto = 0.0;    // Superfície filtrada
    double limite_variacao_falha = 15.0; // Parâmetro configurável remotamente

    // --- PRIMITIVAS DE SINCRONIZAÇÃO DE TEMPO REAL (POSIX) ---
    std::mutex mtx_navegacao;         // Protege variáveis de controle e estado do veículo
    std::mutex mtx_sensores;          // Protege as leituras vindas do simulador
    
    std::condition_variable cv_camera; // Sincronização por evento para a Câmera (YOLO)
};

#endif