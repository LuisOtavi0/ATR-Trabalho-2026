import pygame
import time
from interface_grafica import InterfaceGrafica
from simulador_fisico import SimuladorFisico
from detector_yolo import DetectorYOLO
from comunicacao import GerenciadorComunicacao
import sys

def main():
    # 1. Inicializa os módulos do simulador, interface e visão
    interface = InterfaceGrafica()
    simulador = SimuladorFisico()
    yolo = DetectorYOLO()
    
    # Conecta ao broker MQTT local para a operação remota
    comunicacao = GerenciadorComunicacao(broker_mqtt="localhost", porta_mqtt=1883)
    comunicacao.conectar_mqtt()

    clock = pygame.time.Clock()
    executando = True
    
    # Variáveis de controle de estado local da IHM
    log_recente = None
    frame_camera = None
    objetos_ia = []
    e_inspecao_ativa = False

    print("[SIMULADOR] Loop principal iniciado. Conectando via IPC ao Robô C++...")

    # --- LOOP PRINCIPAL DE TEMPO REAL (Executa a 50 Hz -> Período de 20ms) ---
    while executando:
        # =========================================================================
        # PASSO A: PROCESSAMENTO DE EVENTOS E INTERACTION (IHM)
        # =========================================================================
        botoes_ihm = interface.desenhar_painel_controle()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                pos_mouse = pygame.mouse.get_pos()
                
                # Encaminhamento de comandos via Broker MQTT
                if botoes_ihm["AUTO"].collidepoint(pos_mouse):
                    comunicacao.comandos_remotos["c_automatico"] = True
                    comunicacao.comandos_remotos["c_man"] = False
                    comunicacao.cliente_mqtt.publish("robo/comando/c_automatico", "true")
                elif botoes_ihm["MANUAL"].collidepoint(pos_mouse):
                    comunicacao.comandos_remotos["c_automatico"] = False
                    comunicacao.comandos_remotos["c_man"] = True
                    comunicacao.cliente_mqtt.publish("robo/comando/c_man", "true")
                elif botoes_ihm["DIREITA"].collidepoint(pos_mouse):
                    comunicacao.cliente_mqtt.publish("robo/comando/direcao", '"direita"')
                elif botoes_ihm["ESQUERDA"].collidepoint(pos_mouse):
                    comunicacao.cliente_mqtt.publish("robo/comando/direcao", '"esquerda"')
                elif botoes_ihm["PARAR"].collidepoint(pos_mouse):
                    comunicacao.cliente_mqtt.publish("robo/comando/direcao", '"para"')
                elif botoes_ihm["SP_MAIS"].collidepoint(pos_mouse):
                    comunicacao.comandos_remotos["j_sp_velocidade"] += 1
                    comunicacao.cliente_mqtt.publish("robo/comando/j_sp_velocidade", str(comunicacao.comandos_remotos["j_sp_velocidade"]))
                elif botoes_ihm["SP_MENOS"].collidepoint(pos_mouse):
                    comunicacao.comandos_remotos["j_sp_velocidade"] = max(0, comunicacao.comandos_remotos["j_sp_velocidade"] - 1)
                    comunicacao.cliente_mqtt.publish("robo/comando/j_sp_velocidade", str(comunicacao.comandos_remotos["j_sp_velocidade"]))

        # =========================================================================
        # PASSO B: RENDERIZAÇÃO GRÁFICA IMEDIATA (Evita o congelamento de tela)
        # =========================================================================
        # Coleta a última leitura estática para desenhar o frame atual
        leitura_lidar = simulador.ler_sensor_lidar()
        
        # Atualiza a tela gráfica antes de travar no socket de rede
        interface.desenhar_ambiente(simulador, leitura_lidar, e_inspecao_ativa)
        interface.renderizar_frame_yolo(frame_camera, objetos_ia)
        interface.atualizar_painel_dados(simulador, comunicacao.comandos_remotos, log_recente)
        interface.atualizar_tela() # Inverte os buffers (Double Buffering) na GPU do host

        # =========================================================================
        # PASSO C: COMUNICAÇÃO DE TEMPO REAL SÍNCRONA (Duto IPC via ZeroMQ)
        # =========================================================================
        dados_para_robo = {
            "i_lidar": leitura_lidar,
            "i_encoder": (int(simulador.posicao_x) % 2 == 0)
        }
        
        # Ponto de sincronismo bloqueante: Aguarda a execução da tarefa cíclica do C++
        o_aceleracao = comunicacao.trocar_dados_ipc(dados_para_robo)

        # =========================================================================
        # PASSO D: DINÂMICA FÍSICA E INTELICÊNCIA ARTIFICIAL INCORPORADA
        # =========================================================================
        # Atualiza o modelo matemático de estados base com a atuação calculada pelo C++
        aceleracao_real = simulador.atualizar_fisica(o_aceleracao, dt=0.020)
        
        # Dispara a inferência computacional pesada (YOLOv8) sob demanda geométrica
        variacao_teto = abs(simulador.altura_nominal_teto - leitura_lidar)
        if variacao_teto > 15.0:
            e_inspecao_ativa = True
            frame_camera, objetos_ia = yolo.processar_inspecao_visual(simulador.posicao_x, leitura_lidar)
        else:
            e_inspecao_ativa = False
            frame_camera = None
            objetos_ia = []

        # =========================================================================
        # PASSO E: SÍNTESE E ENVIO DE TELEMETRIA (Monitoramento Remoto)
        # =========================================================================
        log_recente = {
            "timestamp": int(time.time() * 1000),
            "x": simulador.posicao_x,
            "y": float(leitura_lidar),
            "nivel_confianca": 0.95 if not e_inspecao_ativa else 0.50
        }
        comunicacao.publicar_telemetria(log_recente)

        # Restringe rigidamente a taxa de amostragem do simulador a 50 Hz
        clock.tick(50)

    # Finalização limpa e devolução de recursos para o kernel do sistema operacional
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()