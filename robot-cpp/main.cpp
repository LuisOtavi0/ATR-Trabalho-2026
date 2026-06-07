#include <iostream>
#include <thread>
#include <vector>
#include <zmq.hpp> // Importante: precisamos do ZeroMQ para o Handshake inicial
#include "shared_data.hpp"
#include "buffer_concorrente.hpp"
#include "tarefas_robo.hpp"

SharedState state;

// Instanciamos o Buffer Concorrente com capacidade para 100 elementos
BufferConcorrente buffer_telemetria(100);

int main() {
    std::cout << "=================================================" << std::endl;
    std::cout << " INICIANDO SISTEMA EMBARCADO DE INSPEÇÃO DE TÚNEIS" << std::endl;
    std::cout << "=================================================" << std::endl;

    // --- CONFIGURAÇÃO INICIAL DO ESTADO ---
    {
        std::lock_guard<std::mutex> lock(state.mtx_navegacao);
        state.e_automatico = true; // Força o modo automático para testes
        state.limite_variacao_falha = 15.0; 
    }

    // =========================================================================
    // BARREIRA DE SINCRONIZAÇÃO (HANDSHAKE) COM O SIMULADOR PYTHON
    // =========================================================================
    std::cout << "[SISTEMA] Aguardando inicialização gráfica do Pygame..." << std::endl;
    
    try {
        zmq::context_t context(1);
        zmq::socket_t socket_sincronia(context, ZMQ_REQ); // Mudar para REQ (Requisitante)
        
        // RESTRUTURAÇÃO: Conecta ao invés de dar bind, já que o host é compartilhado
        socket_sincronia.connect("tcp://localhost:5555"); 

        std::string ping = "{\"status\": \"conectar\"}";
        zmq::message_t mensagem_ping(ping.size());
        memcpy(mensagem_ping.data(), ping.c_str(), ping.size());
        
        // Envia requisições repetidas até o Pygame aceitar e responder
        bool conectado = false;
        while (!conectado) {
            try {
                socket_sincronia.send(mensagem_ping, zmq::send_flags::none);
                
                zmq::message_t resposta_inicial;
                socket_sincronia.recv(resposta_inicial, zmq::recv_flags::none);
                conectado = true;
            } catch (const zmq::error_t& e) {
                // Se o Pygame ainda não subiu, aguarda 200ms e tenta de novo
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
            }
        }

        std::cout << "[SISTEMA] Handshake concluído com sucesso. Liberando threads de tempo real." << std::endl;
        socket_sincronia.close();
        context.close();
    } 
    catch (const std::exception& e) {
        std::cerr << "[ERRO] Falha na barreira de sincronia: " << e.what() << std::endl;
    }
    // =========================================================================

    // --- CRIAÇÃO E DISPARO DAS THREADS (Só rodam após o Pygame estar pronto) ---
    std::thread t_odometria(task_calculo_distancia);
    std::thread t_controle(task_controle_navegacao);
    std::thread t_comando(task_comando_navegacao);
    std::thread t_reconstrucao(task_reconstrucao_superficie);
    std::thread t_camera(task_inspecao_camera);
    std::thread t_coletor(task_coletor_dados);

    std::cout << "[SISTEMA] Todas as 6 threads de tempo real foram disparadas com sucesso." << std::endl;

    // --- SINCRONIZAÇÃO DE TÉRMINO (.join) ---
    t_odometria.join();
    t_controle.join();
    t_comando.join();
    t_reconstrucao.join();
    t_camera.join();
    t_coletor.join();

    return 0;
}