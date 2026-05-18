#include <iostream>
#include <thread>
#include <chrono>
#include <cmath>
#include <ctime>
#include <algorithm>
#include "shared_data.hpp"

SharedState state;

void task_calculo_distancia() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        {
            std::lock_guard<std::mutex> lock_nav(state.mtx_navegacao);
            std::lock_guard<std::mutex> lock_sens(state.mtx_sensores);
            state.distancia_total += (state.velocidade_atual * 0.02); 

            static double ultima_posicao_metro = 0;
            if (std::abs(state.distancia_total - ultima_posicao_metro) >= 1.0) {
                state.i_encoder = !state.i_encoder;
                ultima_posicao_metro = state.distancia_total;
            }
        }
        next += std::chrono::milliseconds(20); 
        std::this_thread::sleep_until(next);
    }
}

void task_controle_navegacao() {
    auto next = std::chrono::steady_clock::now();
    const double dt = 0.080;

    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);

            double erro = state.setpoint_velocidade - state.velocidade_atual;

            double P = state.Kp * erro;

            state.erro_acumulado += erro * dt;
            if (state.erro_acumulado > 50.0) state.erro_acumulado = 50.0;
            if (state.erro_acumulado < -50.0) state.erro_acumulado = -50.0;

            double I = state.Ki * state.erro_acumulado;
            double D = state.Kd * (erro - state.erro_anterior) / dt;

            double saida = P + I + D;

            if (saida > 100.0) saida = 100.0;
            if (saida < -100.0) saida = -100.0;

            state.aceleracao_saida = saida;
            state.erro_anterior = erro;

            state.velocidade_atual += (state.aceleracao_saida * 0.01); 
        }

        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

void task_comando_navegacao() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);
            
            if (state.e_automatico) {
                if (!state.e_inspecao) {
                    state.setpoint_velocidade = 2.0; 
                }
            }
        }
        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

void task_reconstrucao_superficie() {
    auto next = std::chrono::steady_clock::now();
    
    while (true) {
        bool disparar_sinalizacao = false;
        double nova_media = 0.0;
        double variacao = 0.0;

        {
            std::lock_guard<std::mutex> lock_sens(state.mtx_sensores);
            
            if (!state.buraco_detectado_no_sensor) {
                if ((std::rand() % 100) < 1) { 
                    state.buraco_detectado_no_sensor = true;
                    state.duracao_buraco = 20 + (std::rand() % 30);
                }
            }

            if (state.buraco_detectado_no_sensor) {
                state.i_lidar = 150 + (std::rand() % 11);
                state.duracao_buraco--;
                if (state.duracao_buraco <= 0) state.buraco_detectado_no_sensor = false;
            } else {
                state.i_lidar = 100 + (std::rand() % 5);
            }
            
            state.historico_lidar.push_back(state.i_lidar);
            if (state.historico_lidar.size() > state.TAMANHO_FILTRO) {
                state.historico_lidar.erase(state.historico_lidar.begin());
            }

            double soma = 0;
            for (int valor : state.historico_lidar) soma += valor;
            nova_media = soma / state.historico_lidar.size();

            variacao = std::abs(nova_media - state.i_lidar);
            state.media_movel_teto = nova_media;

            if (variacao > state.limite_variacao_falha) {
                disparar_sinalizacao = true;
            }
        }

        if (disparar_sinalizacao) {
            {
                std::lock_guard<std::mutex> lock_nav(state.mtx_navegacao);
                state.e_inspecao = true; 
                state.setpoint_velocidade = 1.0; 
            }
            state.cv_camera.notify_one(); // Acorda a câmera imediatamente sem polling ativo
        }

        next += std::chrono::milliseconds(100);
        std::this_thread::sleep_until(next);
    }
}

void task_inspecao_camera() {
    while (true) {
        std::unique_lock<std::mutex> lock(state.mtx_navegacao);

        state.cv_camera.wait(lock, []{ return state.e_inspecao; });
        std::cout << "[ALERTA] Falha detectada! Iniciando inspeção por câmera..." << std::endl;
        lock.unlock(); 

        double dummy = (double)(std::rand() % 100);
        for (int i = 0; i < 50000000; ++i) {
            dummy += std::sqrt(i) * std::tan(i);
        }

        lock.lock();
        state.e_inspecao = false;
        std::cout << "[INFO] Inspeção concluída. Resultado dummy: " << dummy << std::endl;
    }
}

void task_coletor_dados() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        LogEntry entrada;
        {
            std::lock_guard<std::mutex> lock_sens(state.mtx_sensores);
            std::lock_guard<std::mutex> lock_nav(state.mtx_navegacao);

            double variacao = std::abs(state.media_movel_teto - state.i_lidar);

            entrada.timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
            entrada.x = state.distancia_total;
            entrada.y = state.media_movel_teto;
            
            entrada.nivel_confianca = 1.0 - (std::min(variacao, 20.0) / 40.0);
        }

        {
            std::lock_guard<std::mutex> lock_buf(state.mtx_buffer);
            state.buffer_coletor.push_back(entrada);

            if (state.buffer_coletor.size() > 1000) {
            state.buffer_coletor.clear();
            }
        }
            std::cout << "[COLETOR] Log salvo - Pos: " << entrada.x << "m | Teto: " << entrada.y << "m"
          << " | PID -> SP: " << state.setpoint_velocidade 
          << " | PV: " << state.velocidade_atual 
          << " | OUT: " << state.aceleracao_saida << "%"
          << " | Confiança: " << entrada.nivel_confianca << std::endl;

        next += std::chrono::milliseconds(500);
        std::this_thread::sleep_until(next);
    }
}

int main() {
    std::srand(std::time(nullptr));
    std::cout << "Iniciando Sistema de Inspeção de Túneis" << std::endl;

    {
        std::lock_guard<std::mutex> lock(state.mtx_navegacao);
        state.e_automatico = true;
    }

    std::thread t1(task_calculo_distancia);
    std::thread t2(task_controle_navegacao);
    std::thread t3(task_reconstrucao_superficie);
    std::thread t4(task_inspecao_camera);
    std::thread t5(task_coletor_dados);
    std::thread t6(task_comando_navegacao);

    t1.join(); t2.join(); t3.join(); t4.join(); t5.join(); t6.join();
    return 0;
}