cmake_minimum_required(VERSION 3.10)
project(RobotInspecaoEmbarcado CXX)

# Força o uso do padrão moderno C++11 ou superior para suporte nativo a std::thread e std::mutex
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Procura as dependências da biblioteca ZeroMQ (ZMQ) para a comunicação IPC
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

# Define onde estão os cabeçalhos (.hpp)
include_directories(${CMAKE_CURRENT_SOURCE_DIR} ${ZMQ_INCLUDE_DIRS})

# Mapeia todos os arquivos fontes do nosso robô
set(SOURCES
    main.cpp
    tarefas_robo.cpp
)

# Declara o executável final do robô
add_executable(robot_node ${SOURCES})

# Vincula as bibliotecas de threads do Linux (pthread) e do ZeroMQ ao executável
target_link_libraries(robot_node pthread ${ZMQ_LIBRARIES})