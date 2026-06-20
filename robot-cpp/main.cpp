#include <iostream>
#include <thread>
#include <cstring>
#include <zmq.hpp>
#include <mosquitto.h>
#include "shared_data.hpp"
#include "buffer_concorrente.hpp"
#include "tarefas_robo.hpp"

SharedState state;
BufferConcorrente buffer_telemetria(100);
struct mosquitto* g_mqtt_client = nullptr;

static void on_mqtt_connect(struct mosquitto*, void*, int rc) {
    if (rc == 0) {
        mosquitto_subscribe(g_mqtt_client, nullptr, "robo/comando/#", 0);
        std::cout << "[MQTT] Conectado ao broker. Inscrito em robo/comando/#" << std::endl;
    } else {
        std::cerr << "[MQTT] Falha na conexao, codigo: " << rc << std::endl;
    }
}

static void on_mqtt_message(struct mosquitto*, void*,
                            const struct mosquitto_message* msg) {
    if (!msg->payload || msg->payloadlen == 0) return;
    std::string topic(msg->topic);
    std::string payload(static_cast<char*>(msg->payload), msg->payloadlen);

    std::lock_guard<std::mutex> lock(state.mtx_mqtt);

    if (topic.find("c_automatico") != std::string::npos) {
        state.c_automatico_cmd = (payload == "true");

    } else if (topic.find("c_man") != std::string::npos) {
        state.c_man_cmd = (payload == "true");

    } else if (topic.find("j_sp_velocidade") != std::string::npos) {
        try { state.j_sp_velocidade_cmd = std::stoi(payload); } catch (...) {}

    } else if (topic.find("direcao") != std::string::npos) {
        std::string dir = payload;
        if (dir.size() >= 2 && dir.front() == '"')
            dir = dir.substr(1, dir.size() - 2);
        state.c_direita_cmd  = (dir == "direita");
        state.c_esquerda_cmd = (dir == "esquerda");
        state.c_para_cmd     = (dir == "para");

    } else if (topic.find("limite_variacao") != std::string::npos) {
        try { state.limite_variacao_novo = std::stod(payload); } catch (...) {}
    }
}

int main() {
    std::cout << "=================================================" << std::endl;
    std::cout << " SISTEMA EMBARCADO DE INSPEÇÃO DE TÚNEIS — ATR 2026" << std::endl;
    std::cout << "=================================================" << std::endl;

    state.e_automatico         = true;
    state.limite_variacao_falha = 15.0;
    state.j_sp_velocidade_cmd  = 2;

    mosquitto_lib_init();
    g_mqtt_client = mosquitto_new("robo_embarcado_cpp", true, nullptr);
    if (!g_mqtt_client) {
        std::cerr << "[MQTT] Falha ao criar cliente Mosquitto." << std::endl;
    } else {
        mosquitto_connect_callback_set(g_mqtt_client, on_mqtt_connect);
        mosquitto_message_callback_set(g_mqtt_client, on_mqtt_message);

        int rc = mosquitto_connect(g_mqtt_client, "localhost", 1883, 60);
        if (rc != MOSQ_ERR_SUCCESS) {
            std::cerr << "[MQTT] Broker indisponivel (rc=" << rc
                      << "). Continuando sem MQTT." << std::endl;
        } else {
            mosquitto_loop_start(g_mqtt_client);
        }
    }

    std::cout << "[SISTEMA] Aguardando simulador Python (ZMQ handshake)..." << std::endl;
    try {
        zmq::context_t ctx_hs(1);
        zmq::socket_t  sock_hs(ctx_hs, ZMQ_REQ);
        sock_hs.connect("tcp://localhost:5555");

        const char* ping = "{\"status\": \"conectar\"}";
        bool conectado = false;
        while (!conectado) {
            try {
                zmq::message_t m_ping(strlen(ping));
                memcpy(m_ping.data(), ping, strlen(ping));
                sock_hs.send(m_ping, zmq::send_flags::none);

                zmq::message_t m_resp;
                sock_hs.recv(m_resp, zmq::recv_flags::none);
                conectado = true;
            } catch (const zmq::error_t&) {
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
            }
        }
        std::cout << "[SISTEMA] Handshake OK — simulador pronto." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[ERRO] Handshake falhou: " << e.what() << std::endl;
    }

    std::thread t_ipc       (task_ipc_exchange);
    std::thread t_odometria (task_calculo_distancia);
    std::thread t_controle  (task_controle_navegacao);
    std::thread t_comando   (task_comando_navegacao);
    std::thread t_recon     (task_reconstrucao_superficie);
    std::thread t_camera    (task_inspecao_camera);
    std::thread t_coletor   (task_coletor_dados);

    std::cout << "[SISTEMA] 7 threads de tempo real ativas." << std::endl;

    t_ipc.join();
    t_odometria.join();
    t_controle.join();
    t_comando.join();
    t_recon.join();
    t_camera.join();
    t_coletor.join();

    if (g_mqtt_client) {
        mosquitto_loop_stop(g_mqtt_client, false);
        mosquitto_destroy(g_mqtt_client);
    }
    mosquitto_lib_cleanup();

    return 0;
}
