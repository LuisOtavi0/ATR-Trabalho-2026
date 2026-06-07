import pygame
import cv2

class InterfaceGrafica:
    def __init__(self, largura=1024, altura=600):
        pygame.init()
        pygame.font.init()
        
        self.largura = largura
        self.altura = altura
        self.tela = pygame.display.set_mode((self.largura, self.altura))
        pygame.display.set_caption("Centro de Operação Remota & Simulação de Túneis - ATR 2026")
        
        # --- CORES DO SISTEMA ---
        self.COR_FUNDO = (30, 30, 35)
        self.COR_CONCRETO = (100, 100, 105)
        self.COR_ROBO = (46, 204, 113)
        self.COR_LASER = (231, 76, 60)
        self.COR_ALERTA = (241, 196, 15)
        self.COR_TEXTO = (236, 240, 241)
        self.COR_BOTAO = (52, 152, 219)
        
        # --- FONTES ---
        self.fonte_p = pygame.font.SysFont("Arial", 14)
        self.fonte_m = pygame.font.SysFont("Arial", 18, bold=True)
        self.fonte_g = pygame.font.SysFont("Arial", 24, bold=True)
        
        # --- ÁREA DA CÂMERA (SURFACE DO PYGAME) ---
        self.surface_camera = pygame.Surface((320, 240))
        
    def desenhar_painel_controle(self):
        # Fundo do painel inferior
        pygame.draw.rect(self.tela, (20, 20, 25), (0, 420, self.largura, 180))
        
        # Definição geométrica dos botões [cite: 123, 127, 129]
        botoes = {
            "AUTO": pygame.Rect(50, 450, 120, 40),
            "MANUAL": pygame.Rect(50, 510, 120, 40),
            "ESQUERDA": pygame.Rect(200, 480, 60, 40),
            "PARAR": pygame.Rect(270, 480, 70, 40),
            "DIREITA": pygame.Rect(350, 480, 60, 40),
            "SP_MAIS": pygame.Rect(450, 450, 50, 40),
            "SP_MENOS": pygame.Rect(450, 510, 50, 40)
        }
        
        # Renderização visual dos botões
        for nome, ret in botoes.items():
            pygame.draw.rect(self.tela, self.COR_BOTAO, ret, border_radius=5)
            texto = self.fonte_p.render(nome, True, self.COR_TEXTO)
            text_rect = texto.get_rect(center=ret.center)
            self.tela.blit(texto, text_rect)
            
        return botoes

    def desenhar_ambiente(self, sim_fisico, leitura_lidar, e_inspecao):
        """Renderiza graficamente o túnel com base na posição física do simulador[cite: 30, 103]."""
        self.tela.fill(self.COR_FUNDO)
        
        # Desenha a linha de centro do túnel (Pista de rolagem)
        # 1 metro = 15 pixels
        escala_x = 15.0
        offset_visual_x = 100 - (sim_fisico.posicao_x * escala_x)
        
        # Pista
        pygame.draw.rect(self.tela, (50, 50, 50), (0, 300, self.largura, 20))
        
        # --- DESENHO GEOMÉTRICO DO TETO ---
        pontos_teto = []
        for x_pixel in range(0, self.largura):
            x_fisico = (x_pixel - offset_visual_x) / escala_x
            
            altura_teto_local = sim_fisico.altura_nominal_teto
            
            if 10.0 <= x_fisico <= 14.0:
                altura_teto_local = 150.0
            elif 45.0 <= x_fisico <= 48.0:
                altura_teto_local = 70.0
                
            y_pixel_teto = int(300 - altura_teto_local)
            
            if 20.0 <= x_fisico <= 40.0:
                deslocamento_declive = (x_fisico - 20.0) * 5.0
                y_pixel_teto += int(deslocamento_declive)
                if x_pixel == int(100 + sim_fisico.posicao_x * escala_x + offset_visual_x):
                    pass
                    
            pontos_teto.append((x_pixel, y_pixel_teto))
            
        if len(pontos_teto) > 1:
            pygame.draw.lines(self.tela, self.COR_CONCRETO, False, pontos_teto, 5)
            
        # --- DESENHO DO ROBÔ DE INSPEÇÃO ---
        robo_tela_x = int(100 + sim_fisico.posicao_x * escala_x + offset_visual_x)
        robo_tela_y = 270
        
        # Ajusta a inclinação do robô se ele estiver no declive (IMU)
        surface_robo = pygame.Surface((50, 30), pygame.SRCALPHA)
        pygame.draw.rect(surface_robo, self.COR_ROBO, (0, 10, 50, 15), border_radius=3)
        pygame.draw.circle(surface_robo, (10, 10, 10), (12, 25), 6)
        pygame.draw.circle(surface_robo, (10, 10, 10), (38, 25), 6)
        pygame.draw.rect(surface_robo, (80, 80, 80), (20, 0, 8, 10))
        
        if sim_fisico.angulo_declive_graus > 0:
            surface_robo = pygame.transform.rotate(surface_robo, -sim_fisico.angulo_declive_graus)
            
        self.tela.blit(surface_robo, (robo_tela_x - 25, robo_tela_y - 15))
        
        # --- DESENHO DO FEIXE LASER DO LIDAR ---
        y_teto_atual = 300 - leitura_lidar
        if 20.0 <= sim_fisico.posicao_x <= 40.0:
            y_teto_atual += int((sim_fisico.posicao_x - 20.0) * 5.0)
            
        pygame.draw.line(self.tela, self.COR_LASER, (robo_tela_x, robo_tela_y - 15), (robo_tela_x, y_teto_atual), 2)
        
        # --- SINALIZADOR DE ALERTA DE INSPEÇÃO EM TEMPO REAL ---
        if e_inspecao:
            pygame.draw.circle(self.tela, self.COR_ALERTA, (robo_tela_x, y_teto_atual), 15, 2)
            texto_alerta = self.fonte_m.render("ALERTA: INSPEÇÃO VISUAL ATIVA (YOLO)", True, self.COR_ALERTA)
            self.tela.blit(texto_alerta, (self.largura // 2 - 150, 40))

    def atualizar_painel_dados(self, sim_fisico, comandos_remotos, log_recente):
        """Imprime na tela as variáveis de estado de tempo real recebidas da telemetria[cite: 98]."""
        txt_pos = self.fonte_p.render(f"Posição X: {sim_fisico.posicao_x:.2f} m", True, self.COR_TEXTO)
        txt_vel = self.fonte_p.render(f"Velocidade Real: {sim_fisico.velocidade_x:.2f} m/s", True, self.COR_TEXTO)
        txt_sp  = self.fonte_p.render(f"Setpoint Velocidade: {comandos_remotos['j_sp_velocidade']:.1f} m/s", True, self.COR_TEXTO)
        txt_imu = self.fonte_p.render(f"IMU Pitch (Inclinação): {sim_fisico.angulo_declive_graus:.1f}°", True, self.COR_TEXTO)
        
        self.tela.blit(txt_pos, (550, 440))
        self.tela.blit(txt_vel, (550, 465))
        self.tela.blit(txt_sp,  (550, 490))
        self.tela.blit(txt_imu, (550, 515))

        # Dados vindos do Robô C++ processados
        if log_recente:
            txt_conf = self.fonte_p.render(f"Confiança de Mapeamento: {log_recente.get('nivel_confianca', 0.0)*100:.1f}%", True, (46, 204, 113))
            txt_teto = self.fonte_p.render(f"Média Móvel Teto (C++): {log_recente.get('y', 0.0):.1f} cm", True, self.COR_TEXTO)
            self.tela.blit(txt_conf, (550, 545))
            self.tela.blit(txt_teto, (550, 570))

    def renderizar_frame_yolo(self, frame_opencv, objetos_detectados):
        """BÔNUS: Desenha o frame processado pela rede neural YOLO na área designada da interface."""
        if frame_opencv is not None:
            frame_rgb = cv2.cvtColor(frame_opencv, cv2.COLOR_BGR2RGB)
            frame_redimensionado = cv2.resize(frame_rgb, (320, 240))
            
            surface_frame = pygame.surfarray.make_surface(frame_redimensionado.swapaxes(0, 1))
            self.surface_camera.blit(surface_frame, (0, 0))
            
            if objetos_detectados:
                for obj in objetos_detectados:
                    txt_classe = self.fonte_p.render(f"{obj['classe'].upper()} ({obj['confianca']*100:.0f}%)", True, (255, 0, 0))
                    self.surface_camera.blit(txt_classe, (10, 10))
        else:
            self.surface_camera.fill((40, 40, 45))
            txt_standby = self.fonte_p.render("CÂMERA EM STANDBY (SEM FALHAS)", True, (150, 150, 150))
            self.surface_camera.blit(txt_standby, (40, 110))
            
        self.tela.blit(self.surface_camera, (680, 430))

    def atualizar_tela(self):
        """Atualiza o buffer duplo do Pygame para renderizar os gráficos sem flicker."""
        pygame.display.flip()