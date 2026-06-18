import pygame
import time
import sys
import traceback
from interface_grafica import InterfaceGrafica
from simulador_fisico import SimuladorFisico
from detector_yolo import DetectorYOLO
from comunicacao import GerenciadorComunicacao

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

    print("[SIMULADOR] Loop principal iniciado. Aguardando conexao IPC do Robo C++...", flush=True)

    # Descarta eventos acumulados durante a inicialização (evita QUIT espúrio no SDL2/Windows)
    pygame.event.clear()

    # --- LOOP PRINCIPAL (50 Hz → 20 ms) ---
    while executando:
      try:
        # =====================================================================
        # A: EVENTOS E INTERFACE
        # =====================================================================
        botoes_ihm = interface.desenhar_painel_controle()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                print("[SIMULADOR] Evento QUIT recebido — janela fechada pelo usuário.", flush=True)
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
        if comunicacao.cpp_conectado:
            # Modo normal: PID do C++ comanda a física local
            aceleracao_real = simulador.atualizar_fisica(o_aceleracao, dt=0.020)
        else:
            # Modo demo autônomo: sem C++ conectado, move a 2 m/s constante
            # para demonstrar detecção de anomalias, YOLO e telemetria.
            simulador.velocidade_x = 2.0
            simulador.posicao_x   += simulador.velocidade_x * 0.020
            simulador.angulo_declive_graus = (
                12.0 if 20.0 <= simulador.posicao_x <= 40.0 else 0.0
            )
            if simulador.posicao_x >= 80.0:
                simulador.posicao_x = 0.0  # reinicia o túnel
            aceleracao_real = 0.0

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

      except Exception as e:
        print(f"[ERRO NO LOOP] {type(e).__name__}: {e}", flush=True)
        traceback.print_exc(file=sys.stdout)
        executando = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
