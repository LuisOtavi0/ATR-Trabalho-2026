#include "tarefas_robo.hpp"
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include <zmq.hpp>
#include <mosquitto.h>

// =============================================================================
// HELPERS: Parser JSON mínimo para o payload do simulador
// =============================================================================

static int parse_int_json(const std::string& json, const std::string& key) {
    std::string search = "\"" + key + "\": ";
    auto pos = json.find(search);
    if (pos == std::string::npos) return 0;
    try { return std::stoi(json.substr(pos + search.size())); }
    catch (...) { return 0; }
}

static bool parse_bool_json(const std::string& json, const std::string& key) {
    std::string search = "\"" + key + "\": ";
    auto pos = json.find(search);
    if (pos == std::string::npos) return false;
    size_t val_start = pos + search.size();
    return json.substr(val_start, 4) == "true";
}

static double parse_double_json(const std::string& json, const std::string& key) {
    std::string search = "\"" + key + "\": ";
    auto pos = json.find(search);
    if (pos == std::string::npos) return 0.0;
    try { return std::stod(json.substr(pos + search.size())); }
    catch (...) { return 0.0; }
}

// =============================================================================
// TASK 0 (nova): IPC EXCHANGE — troca dados com o simulador Python (20 ms)
// BUG CORRIGIDO: main.cpp fechava o socket após o handshake e as tasks nunca
// mais enviavam/recebiam dados. Agora um socket dedicado por thread faz a
// troca contínua: envia o_aceleracao → recebe i_lidar + i_encoder.
// =============================================================================
void task_ipc_exchange() {
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_REQ);

    // O mesmo endereço do handshake — após o handshake o REP Python já está
    // pronto para o próximo recv(), então basta conectar e começar a enviar.
    socket.connect("tcp://localhost:5555");

    std::cout << "[IPC] Thread de troca de dados iniciada (20 ms)." << std::endl;

    auto next = std::chrono::steady_clock::now();
    while (true) {
        // Lê atuação calculada pelo PID
        double accel_out;
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);
            accel_out = state.aceleracao_saida;
        }

        // Envia para o Python
        char buf[64];
        snprintf(buf, sizeof(buf), "{\"o_aceleracao\": %.2f}", accel_out);
        zmq::message_t msg_send(strlen(buf));
        memcpy(msg_send.data(), buf, strlen(buf));
        socket.send(msg_send, zmq::send_flags::none);

        // Recebe resposta com dados de sensores
        zmq::message_t msg_recv;
        socket.recv(msg_recv, zmq::recv_flags::none);
        std::string resp(static_cast<char*>(msg_recv.data()), msg_recv.size());

        int    lidar_val = parse_int_json(resp,    "i_lidar");
        bool   enc_val   = parse_bool_json(resp,   "i_encoder");
        double vel_val   = parse_double_json(resp,  "velocidade");

        {
            std::lock_guard<std::mutex> lock(state.mtx_sensores);
            state.i_lidar   = lidar_val;
            state.i_encoder = enc_val;
        }
        // Velocidade real do simulador físico → feedback limpo para o PID
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);
            state.velocidade_atual = vel_val;
        }

        next += std::chrono::milliseconds(20);
        std::this_thread::sleep_until(next);
    }
}

// =============================================================================
// TASK 1: CÁLCULO DE DISTÂNCIA PERCORRIDA (20 ms)
// Lê i_encoder (atualizado pelo task_ipc_exchange) e conta transições.
// Cada transição lógica (0→1 ou 1→0) representa 1 metro percorrido.
//
// Não estimamos velocidade aqui: com 1 pulso/metro a estimativa via dt entre
// pulsos explode em dt → 0 no startup (quando encoder Python faz toggle
// spurious) e fica imprecisa durante a aceleração. A velocidade real já vem
// do simulador via IPC (task_ipc_exchange → state.velocidade_atual).
// =============================================================================
void task_calculo_distancia() {
    auto next = std::chrono::steady_clock::now();
    bool encoder_anterior = false;

    while (true) {
        bool encoder_atual;
        {
            std::lock_guard<std::mutex> lock(state.mtx_sensores);
            encoder_atual = state.i_encoder;
        }

        if (encoder_atual != encoder_anterior) {
            encoder_anterior = encoder_atual;
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);
            state.distancia_total += 1.0; // cada transição = 1 metro
        }

        next += std::chrono::milliseconds(20);
        std::this_thread::sleep_until(next);
    }
}

// =============================================================================
// TASK 2: CONTROLE DE NAVEGAÇÃO — PID (80 ms)
// =============================================================================
void task_controle_navegacao() {
    auto next = std::chrono::steady_clock::now();
    const double dt = 0.080;

    while (true) {
        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);

            double erro = state.setpoint_velocidade - state.velocidade_atual;

            double P = state.Kp * erro;

            state.erro_acumulado += erro * dt;
            state.erro_acumulado  = std::max(-50.0, std::min(state.erro_acumulado, 50.0));
            double I = state.Ki * state.erro_acumulado;

            double D = state.Kd * (erro - state.erro_anterior) / dt;

            double saida = P + I + D;
            state.aceleracao_saida = std::max(-100.0, std::min(saida, 100.0));
            state.erro_anterior    = erro;
        }

        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

// =============================================================================
// TASK 3: COMANDO DE NAVEGAÇÃO (80 ms)
// Recebe comandos MQTT via shared state (mtx_mqtt) e aplica ao controlador.
// =============================================================================
void task_comando_navegacao() {
    auto next = std::chrono::steady_clock::now();
    while (true) {
        // Snapshot dos comandos MQTT recebidos assincronamente
        bool do_auto, do_man, do_para, do_dir, do_esq;
        int  sp_vel;
        double novo_limite;
        {
            std::lock_guard<std::mutex> lock(state.mtx_mqtt);
            do_auto    = state.c_automatico_cmd;  state.c_automatico_cmd = false;
            do_man     = state.c_man_cmd;          state.c_man_cmd        = false;
            do_para    = state.c_para_cmd;
            do_dir     = state.c_direita_cmd;
            do_esq     = state.c_esquerda_cmd;
            sp_vel     = state.j_sp_velocidade_cmd;
            novo_limite = state.limite_variacao_novo;
            if (novo_limite >= 0.0) state.limite_variacao_novo = -1.0;
        }

        // Aplica parâmetro configurável de detecção de falhas
        if (novo_limite >= 0.0) {
            std::lock_guard<std::mutex> lock(state.mtx_sensores);
            state.limite_variacao_falha = novo_limite;
        }

        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);

            if (do_auto) state.e_automatico = true;
            if (do_man)  state.e_automatico = false;

            if (state.e_automatico) {
                if (!state.e_inspecao) {
                    // Cruzeiro automático com setpoint remoto (mínimo 1 m/s)
                    state.setpoint_velocidade = (sp_vel > 0) ? (double)sp_vel : 2.0;
                }
                // Durante inspeção, a task_reconstrucao já reduziu o setpoint
            } else {
                // Modo manual: comandos de direção
                if (do_para) {
                    state.setpoint_velocidade = 0.0;
                } else if (do_dir) {
                    state.setpoint_velocidade = std::min(5.0, state.setpoint_velocidade + 0.5);
                } else if (do_esq) {
                    state.setpoint_velocidade = std::max(0.0, state.setpoint_velocidade - 0.5);
                }
            }
        }

        next += std::chrono::milliseconds(80);
        std::this_thread::sleep_until(next);
    }
}

// =============================================================================
// TASK 4: RECONSTRUÇÃO DA SUPERFÍCIE DO TETO (100 ms)
// BUG CORRIGIDO: agora É PRODUTORA do buffer (antes ninguém produzia).
// Aplica filtro de média móvel, detecta anomalias e sinaliza câmera.
// =============================================================================
void task_reconstrucao_superficie() {
    auto next = std::chrono::steady_clock::now();

    while (true) {
        bool   disparar = false;
        double nova_media = 0.0;
        double dist_atual = 0.0;

        // --- Leitura do LIDAR e filtro MA ---
        {
            std::lock_guard<std::mutex> lock(state.mtx_sensores);

            state.historico_lidar.push_back(state.i_lidar);
            if ((int)state.historico_lidar.size() > state.TAMANHO_FILTRO)
                state.historico_lidar.erase(state.historico_lidar.begin());

            double soma = 0.0;
            for (int v : state.historico_lidar) soma += v;
            nova_media = state.historico_lidar.empty() ? 0.0
                       : soma / (double)state.historico_lidar.size();

            double variacao = std::abs(nova_media - (double)state.i_lidar);
            state.media_movel_teto = nova_media;

            if (variacao > state.limite_variacao_falha && !state.historico_lidar.empty())
                disparar = true;
        }

        {
            std::lock_guard<std::mutex> lock(state.mtx_navegacao);
            dist_atual = state.distancia_total;
        }

        // --- Produz entrada no buffer para o Coletor de Dados ---
        LogEntry entrada;
        entrada.timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        entrada.x               = dist_atual;
        entrada.y               = nova_media;
        entrada.nivel_confianca = 0.0; // calculado online pelo coletor
        buffer_telemetria.produzir(entrada);

        // --- Sinalização de falha ---
        if (disparar) {
            {
                std::lock_guard<std::mutex> lock(state.mtx_navegacao);
                if (!state.e_inspecao) {
                    state.e_inspecao         = true;
                    state.setpoint_velocidade = 0.5; // velocidade reduzida
                    state.o_liga_camera       = true;
                    std::cout << "[ALERTA] Variacao severa detectada! Acionando camera." << std::endl;
                }
            }
            state.cv_camera.notify_one(); // aciona task_inspecao_camera
        }

        next += std::chrono::milliseconds(100);
        std::this_thread::sleep_until(next);
    }
}

// =============================================================================
// TASK 5: INSPEÇÃO DETALHADA POR CÂMERA (assíncrona, event-driven)
// Aguarda cv_camera e executa carga CPU real — NÃO usa sleep (conforme PDF).
// =============================================================================
void task_inspecao_camera() {
    while (true) {
        std::unique_lock<std::mutex> lock(state.mtx_navegacao);
        state.cv_camera.wait(lock, [] { return state.e_inspecao; });

        std::cout << "[CAMERA] Iniciando processamento pesado (simulando YOLO)..." << std::endl;
        lock.unlock(); // libera mutex durante a carga pesada

        // Carga CPU real: evita inversão de prioridade durante processamento
        volatile double carga = 0.0;
        for (int i = 1; i < 25000000; ++i)
            carga += std::sqrt((double)i) * std::sin((double)i);

        lock.lock();
        state.e_inspecao   = false;
        state.o_liga_camera = false;
        std::cout << "[CAMERA] Inspecao concluida. Retomando velocidade normal. (checksum="
                  << (long long)carga % 1000 << ")" << std::endl;
    }
}

// =============================================================================
// TASK 6: COLETOR DE DADOS (assíncrona, bloqueante no buffer)
// BUG CORRIGIDO: agora CONSOME do buffer (antes era produtora, causando
// buffer cheio e travamento).
// Grava em disco (JSONL) e publica telemetria via MQTT.
// Calcula nível de confiança online: mais medições próximas = mais confiança.
// =============================================================================
void task_coletor_dados() {
    // Histórico para cálculo de confiança por densidade de medições
    std::vector<double> historico_x;
    const size_t MAX_HIST      = 30;
    const double JANELA_M      = 0.5; // janela de 50 cm

    std::ofstream log_file("robot_inspection_log.jsonl", std::ios::app);
    if (!log_file.is_open())
        std::cerr << "[COLETOR] AVISO: nao foi possivel abrir arquivo de log!" << std::endl;

    while (true) {
        // Bloqueia até haver dado disponível no buffer (produtor-consumidor)
        LogEntry entrada = buffer_telemetria.consumir();

        // Cálculo online do nível de confiança
        historico_x.push_back(entrada.x);
        if (historico_x.size() > MAX_HIST)
            historico_x.erase(historico_x.begin());

        int proximas = 0;
        for (double x : historico_x)
            if (std::abs(x - entrada.x) <= JANELA_M) ++proximas;
        entrada.nivel_confianca = std::min(1.0, proximas / 5.0);

        // Grava em disco
        if (log_file.is_open()) {
            log_file << "{\"timestamp\":" << entrada.timestamp
                     << ",\"x\":"         << entrada.x
                     << ",\"y\":"         << entrada.y
                     << ",\"nivel_confianca\":" << entrada.nivel_confianca
                     << "}" << std::endl;
        }

        // Publica no MQTT para a Operação Remota
        if (g_mqtt_client) {
            char payload[256];
            snprintf(payload, sizeof(payload),
                "{\"timestamp\":%lld,\"x\":%.3f,\"y\":%.3f,\"nivel_confianca\":%.3f}",
                (long long)entrada.timestamp, entrada.x, entrada.y, entrada.nivel_confianca);
            mosquitto_publish(g_mqtt_client, nullptr, "robo/telemetria",
                              (int)strlen(payload), payload, 0, false);
        }

        std::cout << "[COLETOR] x=" << entrada.x << "m | y_teto=" << entrada.y
                  << "cm | conf=" << (int)(entrada.nivel_confianca * 100) << "%" << std::endl;
    }
}
