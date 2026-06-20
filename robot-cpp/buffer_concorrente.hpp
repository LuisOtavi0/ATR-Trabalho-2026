#ifndef BUFFER_CONCORRENTE_HPP
#define BUFFER_CONCORRENTE_HPP

#include <mutex>
#include <condition_variable>
#include <vector>
#include <stdexcept>
#include "shared_data.hpp"

class BufferConcorrente {
private:
    std::vector<LogEntry> buffer;
    size_t capacidade;
    size_t head = 0;
    size_t tail = 0;
    size_t tamanho_atual = 0;

    std::mutex mtx;
    std::condition_variable cv_nao_cheio;
    std::condition_variable cv_nao_vazio;

public:
    explicit BufferConcorrente(size_t cap) : capacidade(cap) {
        buffer.resize(capacidade);
    }

    void produzir(const LogEntry& entrada) {
        std::unique_lock<std::mutex> lock(mtx);

        cv_nao_cheio.wait(lock, [this]() { return tamanho_atual < capacidade; });

        buffer[head] = entrada;
        head = (head + 1) % capacidade;
        tamanho_atual++;

        cv_nao_vazio.notify_one();
    }

    LogEntry consumir() {
        std::unique_lock<std::mutex> lock(mtx);

        cv_nao_vazio.wait(lock, [this]() { return tamanho_atual > 0; });

        LogEntry entrada = buffer[tail];
        tail = (tail + 1) % capacidade;
        tamanho_atual--;

        cv_nao_cheio.notify_one();

        return entrada;
    }
};

#endif