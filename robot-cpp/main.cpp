#include <iostream>
#include <string>
#include <chrono>
#include <thread>
#include "mqtt/async_client.h"

const std::string SERVER_ADDRESS("tcp://mqtt-broker:1883");
const std::string CLIENT_ID("cpp_client");
const std::string TOPIC("topico/teste");

int main() {
    mqtt::async_client client(SERVER_ADDRESS, CLIENT_ID);
    
    try {
        mqtt::connect_options connOpts;
        connOpts.set_clean_session(true);

        std::cout << "C++ conectando ao broker..." << std::endl;
        client.connect(connOpts)->wait();
        std::cout << "C++ conectado!" << std::endl;

        while (true) {
            std::string payload = "Mensagem vinda do C++!";
            client.publish(TOPIC, payload, 1, false);
            std::this_thread::sleep_for(std::chrono::seconds(7));
        }
    } catch (const mqtt::exception& exc) {
        std::cerr << "Erro: " << exc.what() << std::endl;
        return 1;
    }
    return 0;
}