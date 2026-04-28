#include <iostream>
#include <thread>
#include <chrono>
#include <cmath>
#include "shared_data.hpp"

SharedState state;

// 1. Cálculo de distância percorrida (Ciclo: 20ms) [cite: 60, 88]
void task_calculo_distancia() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx);
            // Lógica: simular troca de estado do encoder a cada metro [cite: 89]
        }
        next += std::chrono::milliseconds(20);
        std::this_thread::sleep_until(next);
    }
}

void task_controle_navegacao() {
    auto next = std::chrono::steady_clock::now();
    const double dt = 0.080; // Delta tempo de 80ms

    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx);

            // 1. Cálculo do Erro
            double erro = state.setpoint_velocidade - state.velocidade_atual;

            // 2. Termo Proporcional
            double P = state.Kp * erro;

            // 3. Termo Integral (com proteção contra Windup)
            state.erro_acumulado += erro * dt;
            double I = state.Ki * state.erro_acumulado;

            // 4. Termo Derivativo
            double D = state.Kd * (erro - state.erro_anterior) / dt;

            // 5. Saída Total
            double saida = P + I + D;

            // Saturação da saída entre -100% e 100% 
            if (saida > 100.0) saida = 100.0;
            if (saida < -100.0) saida = -100.0;

            state.aceleracao_saida = saida;
            state.erro_anterior = erro;

            // Para fins de teste na Etapa 1, simulamos que a velocidade 
            // responde à aceleração (na Etapa 2 isso virá da simulação física)
            state.velocidade_atual += (state.aceleracao_saida * 0.01); 
        }

        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

// 3. Reconstrução da superfície do teto (Ciclo: 100ms) [cite: 61, 90]
void task_reconstrucao_superficie() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx);
            // Lógica: Filtro de média móvel e detecção de falhas [cite: 90, 91]
        }
        next += std::chrono::milliseconds(100);
        std::this_thread::sleep_until(next);
    }
}

// 4. Inspeção detalhada por câmera (Baseada em evento) [cite: 71, 92]
void task_inspecao_camera() {
    while (true) {
        // Aguarda sinalização (via variável de condição ou flag) 
        if (state.e_inspecao) {
            // Simular processamento pesado (ex: cálculo matemático intenso) [cite: 93]
            for(int i=0; i<1000000; ++i) { std::sqrt(i * 123.456); } 
            state.e_inspecao = false;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

int main() {
    std::cout << "Iniciando Sistema de Inspeção de Túneis - Etapa 1" << std::endl;

    // Criar as threads para cada tarefa azul [cite: 83]
    std::thread t1(task_calculo_distancia);
    std::thread t2(task_controle_navegacao);
    std::thread t3(task_reconstrucao_superficie);
    std::thread t4(task_inspecao_camera);

    t1.join(); t2.join(); t3.join(); t4.join();
    return 0;
}