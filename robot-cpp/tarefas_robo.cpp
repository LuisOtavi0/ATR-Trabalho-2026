#include "tarefas_robo.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <cmath>
#include <algorithm>

// --- TASK 1: CALCULO DE DISTANCIA (Período: 20 ms) ---
void task_calculo_distancia() {
    auto next = std::chrono::steady_clock::now();
    double ultima_posicao_metro = 0.0;

    while (true) {
        {
            // SOLUÇÃO DO DEADLOCK: Adquirimos os dois mutexes simultaneamente sem ordem fixa interna
            std::lock(state.mtx_navegacao, state.mtx_sensores);
            std::lock_guard<std::mutex> lock_nav(state.mtx_navegacao, std::adopt_lock);
            std::lock_guard<std::mutex> lock_sens(state.mtx_sensores, std::adopt_lock);

            // Integração numérica da posição baseado na velocidade atual (X = X + v * dt)
            state.distancia_total += (state.velocidade_atual * 0.020); 

            // Emulação do funcionamento físico do encoder (Troca de estado lógico a cada 1 metro)
            if (std::abs(state.distancia_total - ultima_posicao_metro) >= 1.0) {
                state.i_encoder = !state.i_encoder;
                ultima_posicao_metro = std::floor(state.distancia_total);
            }
        } // Seção Crítica finalizada. Locks liberados aqui.

        next += std::chrono::milliseconds(20); 
        std::this_thread::sleep_until(next);
    }
}

// --- TASK 2: CONTROLE DE NAVEGACAO - PID (Período: 80 ms) ---
void task_controle_navegacao() {
    auto next = std::chrono::steady_clock::now();
    const double dt = 0.080; // Período de amostragem do controlador

    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);

            // Cálculo do Erro de Velocidade
            double erro = state.setpoint_velocidade - state.velocidade_atual;

            // Termo Proporcional (P)
            double P = state.Kp * erro;

            // Termo Integrador (I) com anti-windup (Prevenção de saturação do erro acumulado)
            state.erro_acumulado += erro * dt;
            state.erro_acumulado = std::max(-50.0, std::min(state.erro_acumulado, 50.0));
            double I = state.Ki * state.erro_acumulado;

            // Termo Derivativo (D) baseado na taxa de variação do erro
            double D = state.Kd * (erro - state.erro_anterior) / dt;

            // Sinal de Controle Total (Saída PID)
            double saida = P + I + D;
            state.aceleracao_saida = std::max(-100.0, std::min(saida, 100.0)); // Saturação física (-100% a 100%)
            state.erro_anterior = erro;

            // BÔNUS (IMU): O modelo físico real usará a aceleração calculada aqui para atuar no veículo.
            // Para testes internos da Etapa 1, simulamos uma resposta inercial simples:
            state.velocidade_atual += (state.aceleracao_saida * 0.01); 
        }

        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

// --- TASK 3: COMANDO DE NAVEGACAO (Período: 80 ms) ---
void task_comando_navegacao() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);
            
            // Lógica de Automação: Se estiver em modo automático e sem inspeção, mantém cruzeiro
            if (state.e_automatico && !state.e_inspecao) {
                state.setpoint_velocidade = 2.0; // Velocidade padrão em metros por segundo
            }
        }
        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

// --- TASK 4: RECONSTRUCAO DA SUPERFICIE (Período: 100 ms) ---
void task_reconstrucao_superficie() {
    auto next = std::chrono::steady_clock::now();
    
    while (true) {
        bool disparar_sinalizacao = false;
        double nova_media = 0.0;
        double variacao = 0.0;

        {
            std::lock_guard<std::mutex> lock_sens(state.mtx_sensores);
            
            // FILTRO DE MÉDIA MÓVEL: Insere dado atual do LIDAR no histórico
            state.historico_lidar.push_back(state.i_lidar);
            if (state.historico_lidar.size() > state.TAMANHO_FILTRO) {
                state.historico_lidar.erase(state.historico_lidar.begin());
            }

            double soma = 0;
            for (int valor : state.historico_lidar) soma += valor;
            nova_media = soma / state.historico_lidar.size();

            // Detecta desvios abruptos da superfície filtrada (Anomalias no teto)
            variacao = std::abs(nova_media - state.i_lidar);
            state.media_movel_teto = nova_media;

            if (variacao > state.limite_variacao_falha) {
                disparar_sinalizacao = true;
            }
        }

        // Se uma falha grave foi detectada, modifica o comportamento do robô com segurança
        if (disparar_sinalizacao) {
            {
                std::lock_guard<std::mutex> lock_nav(state.mtx_navegacao);
                if (!state.e_inspecao) {
                    state.e_inspecao = true; 
                    state.setpoint_velocidade = 0.5; // Reduz a velocidade para inspeção detalhada
                }
            }
            // Sincronização por evento: Notifica a thread da câmera/YOLO imediatamente
            state.cv_camera.notify_one(); 
        }

        next += std::chrono::milliseconds(100);
        std::this_thread::sleep_until(next);
    }
}

// --- TASK 5: INSPECAO DETALHADA POR CAMERA / YOLO (Assíncrona) ---
void task_inspecao_camera() {
    while (true) {
        std::unique_lock<std::mutex> lock(state.mtx_navegacao);

        // Bloqueio por Evento: A thread libera o Mutex e dorme até receber o notify_one()
        state.cv_camera.wait(lock, []{ return state.e_inspecao; });
        
        std::cout << "[ALERTA] Anomalia detectada no teto! Ativando processamento computacional..." << std::endl;
        
        // Destrancamos o mutex durante o processamento pesado para evitar Inversão de Prioridade
        lock.unlock(); 

        // CARGA DE TRABALHO REAL
        // Substitui o "sleep" por processamento matemático pesado para simular a inferência do YOLO
        double carga_cpu = 0.0;
        for (int i = 0; i < 20000000; ++i) {
            carga_cpu += std::sqrt(i) * std::sin(i);
        }

        // Bloqueia novamente para atualizar o estado de término de forma segura
        lock.lock();
        state.e_inspecao = false;
        std::cout << "[INFO] Inspeção visual concluída. Carga processada: " << carga_cpu << std::endl;
    }
}

// --- TASK 6: COLETOR DE DADOS (Período: 500 ms) ---
void task_coletor_dados() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        LogEntry entrada;
        {
            // SOLUÇÃO DO DEADLOCK: Adquire os dois mutexes usando o mesmo padrão sem risco de travamento cruzado
            std::lock(state.mtx_navegacao, state.mtx_sensores);
            std::lock_guard<std::mutex> lock_nav(state.mtx_navegacao, std::adopt_lock);
            std::lock_guard<std::mutex> lock_sens(state.mtx_sensores, std::adopt_lock);

            double variacao = std::abs(state.media_movel_teto - state.i_lidar);

            // Captura de Timestamp do relógio do sistema operacional (Tempo Real)
            entrada.timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
                
            entrada.x = state.distancia_total;
            entrada.y = state.media_movel_teto;
            
            // Cálculo do nível de confiança online: quanto maior a variação/ruído, menor a confiança
            entrada.nivel_confianca = std::max(0.0, 1.0 - (variacao / 50.0));
        }

        // PRODUÇÃO: Envia a entrada gerada de forma segura para o Buffer Concorrente Thread-Safe
        buffer_telemetria.produzir(entrada);

        std::cout << "[ROBO COLETOR] Registro enviado ao buffer -> X: " << entrada.x 
                  << "m | Y (Teto): " << entrada.y 
                  << "m | Confiança: " << (entrada.nivel_confianca * 100) << "%" << std::endl;

        next += std::chrono::milliseconds(500);
        std::this_thread::sleep_until(next);
    }
}