import pygame
import time
from interface_grafica import InterfaceGrafica
from simulador_fisico import SimuladorFisico
from detector_yolo import DetectorYOLO
from comunicacao import GerenciadorComunicacao
import sys

def main():
    interface   = InterfaceGrafica()
    simulador   = SimuladorFisico()
    yolo        = DetectorYOLO()
    comunicacao = GerenciadorComunicacao(broker_mqtt="localhost", porta_mqtt=1883)
    comunicacao.conectar_mqtt()

    clock        = pygame.time.Clock()
    executando   = True

    # Estado local para a IHM
    log_recente      = None
    frame_camera     = None
    objetos_ia       = []
    e_inspecao_ativa = False

    print("[SIMULADOR] Loop principal iniciado. Aguardando conexao IPC do Robo C++...")

    # --- LOOP PRINCIPAL (50 Hz → 20 ms) ---
    while executando:
        # =====================================================================
        # A: EVENTOS E INTERFACE
        # =====================================================================
        botoes_ihm = interface.desenhar_painel_controle()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False

            elif evento.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                def pub(topico, payload):
                    """Publica MQTT somente se conectado — sem exceção."""
                    if comunicacao._mqtt_ok:
                        try:
                            comunicacao.cliente_mqtt.publish(topico, payload)
                        except Exception:
                            pass

                if botoes_ihm["AUTO"].collidepoint(pos):
                    comunicacao.comandos_remotos["c_automatico"] = True
                    comunicacao.comandos_remotos["c_man"]        = False
                    pub("robo/comando/c_automatico", "true")

                elif botoes_ihm["MANUAL"].collidepoint(pos):
                    comunicacao.comandos_remotos["c_automatico"] = False
                    comunicacao.comandos_remotos["c_man"]        = True
                    pub("robo/comando/c_man", "true")

                elif botoes_ihm["DIREITA"].collidepoint(pos):
                    pub("robo/comando/direcao", '"direita"')

                elif botoes_ihm["ESQUERDA"].collidepoint(pos):
                    pub("robo/comando/direcao", '"esquerda"')

                elif botoes_ihm["PARAR"].collidepoint(pos):
                    pub("robo/comando/direcao", '"para"')

                elif botoes_ihm["SP_MAIS"].collidepoint(pos):
                    comunicacao.comandos_remotos["j_sp_velocidade"] += 1
                    pub("robo/comando/j_sp_velocidade",
                        str(comunicacao.comandos_remotos["j_sp_velocidade"]))

                elif botoes_ihm["SP_MENOS"].collidepoint(pos):
                    sp = max(0, comunicacao.comandos_remotos["j_sp_velocidade"] - 1)
                    comunicacao.comandos_remotos["j_sp_velocidade"] = sp
                    pub("robo/comando/j_sp_velocidade", str(sp))

        # =====================================================================
        # B: RENDERIZAÇÃO (antes do IPC para não travar a tela)
        # =====================================================================
        leitura_lidar = simulador.ler_sensor_lidar()

        interface.desenhar_ambiente(simulador, leitura_lidar, e_inspecao_ativa)
        interface.renderizar_frame_yolo(frame_camera, objetos_ia)
        interface.atualizar_painel_dados(simulador, comunicacao.comandos_remotos, log_recente)
        interface.atualizar_tela()

        # =====================================================================
        # C: TROCA DE DADOS IPC COM O ROBÔ C++ (ZeroMQ REP/REQ — não-bloqueante)
        #
        # CORREÇÃO: trocar_dados_ipc() era bloqueante (recv_string() infinito).
        # Agora a thread ZMQ de background lê/escreve no socket de forma
        # assíncrona. A main thread apenas publica os sensores atuais e lê
        # a última aceleração recebida — sem nenhum risco de congelamento.
        # =====================================================================
        comunicacao.atualizar_sensores_ipc({
            "i_lidar":    leitura_lidar,
            "i_encoder":  simulador.ler_sensor_encoder(),
            "velocidade": simulador.velocidade_x,
        })
        o_aceleracao = comunicacao.obter_aceleracao_ipc()

        # =====================================================================
        # D: DINÂMICA FÍSICA E IA
        # =====================================================================
        aceleracao_real = simulador.atualizar_fisica(o_aceleracao, dt=0.020)

        # BÔNUS: IMU
        imu_ax, imu_pitch = simulador.ler_sensor_imu(aceleracao_real)

        # YOLO: dispara sob demanda quando há anomalia detectável
        variacao_teto = abs(simulador.altura_nominal_teto - leitura_lidar)
        if variacao_teto > 15.0:
            e_inspecao_ativa = True
            frame_camera, objetos_ia = yolo.processar_inspecao_visual(
                simulador.posicao_x, leitura_lidar)
        else:
            e_inspecao_ativa = False
            frame_camera     = None
            objetos_ia       = []

        # =====================================================================
        # E: TELEMETRIA MQTT (dados consolidados para Operação Remota)
        # =====================================================================
        log_recente = {
            "timestamp":       int(time.time() * 1000),
            "x":               simulador.posicao_x,
            "y":               float(leitura_lidar),
            "velocidade":      simulador.velocidade_x,
            "imu_pitch":       imu_pitch,
            "nivel_confianca": 0.95 if not e_inspecao_ativa else 0.50
        }
        comunicacao.publicar_telemetria(log_recente)

        clock.tick(50)  # limita a 50 Hz

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
