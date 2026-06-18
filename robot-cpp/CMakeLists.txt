cmake_minimum_required(VERSION 3.10)
project(RobotInspecaoEmbarcado CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ZeroMQ
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZMQ REQUIRED libzmq)

# Mosquitto MQTT (libmosquitto-dev)
find_library(MOSQUITTO_LIB mosquitto REQUIRED)

include_directories(${CMAKE_CURRENT_SOURCE_DIR} ${ZMQ_INCLUDE_DIRS})

set(SOURCES
    main.cpp
    tarefas_robo.cpp
)

add_executable(robot_node ${SOURCES})

target_link_libraries(robot_node
    pthread
    ${ZMQ_LIBRARIES}
    ${MOSQUITTO_LIB}
)
