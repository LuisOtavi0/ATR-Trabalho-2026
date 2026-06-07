import pygame
import time
from interface_grafica import InterfaceGrafica
from simulador_fisico import SimuladorFisico
from detector_yolo import DetectorYOLO
from comunicacao import GerenciadorComunicacao
import sys

def main():
    interface = InterfaceGrafica()
    simulador = SimuladorFisico()
    yolo = DetectorYOLO()
    
    comunicacao = GerenciadorComunicacao(broker_mqtt="localhost", porta_mqtt=1883)
    comunicacao.conectar_mqtt()

    clock = pygame.time.Clock()
    executando = True
    
    # Variáveis de controle de estado local da IHM
    log_recente = None
    frame_camera = None
    objetos_ia = []
    e_inspecao_ativa = False

    print("[SIMULADOR] Loop principal iniciado. Aguardando conexão do Robô C++...")

    # --- LOOP PRINCIPAL DE TEMPO REAL (Executa a 50 Hz -> Período de 20ms) ---
    while executando:
        botoes_ihm = interface.desenhar_painel_controle()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False
                
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                pos_mouse = pygame.mouse.get_pos()
                
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

        # B. Coleta dados atuais dos sensores simulados
        leitura_lidar = simulador.ler_sensor_lidar()
        
        # C. IPC via ZeroMQ: Envia sensores ao robô C++ e recebe a atuação do motor (o_aceleracao)
        # Montamos o dicionário replicando exatamente as variáveis que o robô C++ espera ler
        dados_para_robo = {
            "i_lidar": leitura_lidar,
            "i_encoder": (int(simulador.posicao_x) % 2 == 0) # Simula variação de borda do encoder
        }
        
        # Troca síncrona bloqueante via ZMQ
        o_aceleracao = comunicacao.trocar_dados_ipc(dados_para_robo)

        # D. Atualiza a física do robô com a aceleração calculada pelo PID do C++
        aceleracao_real = simulador.atualizar_fisica(o_aceleracao, dt=0.020)
        
        # E. Processamento de Visão Computacional / YOLO (BÔNUS)
        # Simulamos que o robô C++ avisa via MQTT/ZMQ quando liga a câmera. 
        # No nosso laço, se o LIDAR detectar variação severa, ativamos a inspeção:
        variacao_teto = abs(simulador.altura_nominal_teto - leitura_lidar)
        if variacao_teto > 15.0: # Mesmo limite configurado no C++
            e_inspecao_ativa = True
            # Ativa a inferência pesada do YOLO
            frame_camera, objetos_ia = yolo.processar_inspecao_visual(simulador.posicao_x, leitura_lidar)
        else:
            e_inspecao_ativa = False
            frame_camera = None
            objetos_ia = []

        # F. Atualização Gráfica da IHM
        interface.desenhar_ambiente(simulador, leitura_lidar, e_inspecao_ativa)
        interface.renderizar_frame_yolo(frame_camera, objetos_ia)
        interface.atualizar_painel_dados(simulador, comunicacao.comandos_remotos, log_recente)
        interface.atualizar_tela()

        # G. Publica telemetria simulando o Coletor de Dados via MQTT para a central
        log_recente = {
            "timestamp": int(time.time() * 1000),
            "x": simulador.posicao_x,
            "y": float(leitura_lidar),
            "nivel_confianca": 0.95 if not e_inspecao_ativa else 0.50
        }
        comunicacao.publicar_telemetria(log_recente)

        # Força o laço a rodar rigidamente a 50 Hz (20ms por ciclo), garantindo estabilidade temporal
        clock.tick(50)

    # Finalização limpa do sistema ao sair do laço
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()