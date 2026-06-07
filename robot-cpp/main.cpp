#include <iostream>
#include <thread>
#include <vector>
#include "shared_data.hpp"
#include "buffer_concorrente.hpp"
#include "tarefas_robo.hpp"

SharedState state;

// Instanciamos o Buffer Concorrente com capacidade para 100 elementos (Evita estouro de memória)
BufferConcorrente buffer_telemetria(100);

int main() {
    std::cout << "=================================================" << std::endl;
    std::cout << " INICIANDO SISTEMA EMBARCADO DE INSPEÇÃO DE TÚNEIS" << std::endl;
    std::cout << "=================================================" << std::endl;

    // --- CONFIGURAÇÃO INICIAL DO ESTADO ---
    {
        std::lock_guard<std::mutex> lock(state.mtx_navegacao);
        state.e_automatico = true; // Força o robô a iniciar no modo automático para testes da Etapa 1
        state.limite_variacao_falha = 15.0; // Define a sensibilidade padrão de detecção do LIDAR
    }

    // --- CRIAÇÃO E DISPARO DAS THREADS (CONCORRÊNCIA POSIX) ---
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