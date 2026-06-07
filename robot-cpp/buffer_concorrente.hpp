#ifndef BUFFER_CONCORRENTE_HPP
#define BUFFER_CONCORRENTE_HPP

#include <mutex>
#include <condition_variable>
#include <vector>
#include <stdexcept>
#include "shared_data.hpp" // Para termos acesso à estrutura LogEntry

class BufferConcorrente {
private:
    std::vector<LogEntry> buffer;
    size_t capacidade;
    size_t head = 0; // Índice de escrita (onde o produtor insere)
    size_t tail = 0; // Índice de leitura (onde o consumidor remove)
    size_t tamanho_atual = 0;

    std::mutex mtx;
    std::condition_variable cv_nao_cheio;
    std::condition_variable cv_nao_vazio;

public:
    explicit BufferConcorrente(size_t cap) : capacidade(cap) {
        buffer.resize(capacidade);
    }

    // Insere um elemento no buffer (Produção)
    void produzir(const LogEntry& entrada) {
        std::unique_lock<std::mutex> lock(mtx);

        // Bloqueia se o buffer estiver completamente cheio (Prevenção de Overflow)
        cv_nao_cheio.wait(lock, [this]() { return tamanho_atual < capacidade; });

        // Seção Crítica: Inserção indexada de forma circular
        buffer[head] = entrada;
        head = (head + 1) % capacidade;
        tamanho_atual++;

        // Notifica a thread consumidora (Coletor de Dados) que há dados novos
        cv_nao_vazio.notify_one();
    } // O lock é liberado automaticamente aqui (RAII)

    // Remove e retorna um elemento do buffer (Consumo)
    LogEntry consumir() {
        std::unique_lock<std::mutex> lock(mtx);

        // Bloqueia se o buffer estiver completamente vazio (Prevenção de Underflow)
        cv_nao_vazio.wait(lock, [this]() { return tamanho_atual > 0; });

        // Seção Crítica: Remoção indexada de forma circular
        LogEntry entrada = buffer[tail];
        tail = (tail + 1) % capacidade;
        tamanho_atual--;

        // Notifica a thread produtora (Reconstrução) que abriu uma vaga no buffer
        cv_nao_cheio.notify_one();

        return entrada;
    } // O lock é liberado automaticamente aqui (RAII)
};

#endif