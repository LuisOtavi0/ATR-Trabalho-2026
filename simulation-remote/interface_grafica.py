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
        
        self.COR_FUNDO = (18, 18, 20)
        self.COR_PAINEL = (28, 28, 32)
        self.COR_BORDA = (45, 45, 50)
        self.COR_CONCRETO = (120, 120, 125)
        self.COR_ROBO = (0, 180, 160)
        self.COR_LASER = (255, 50, 50)
        self.COR_ALERTA = (241, 196, 15)
        self.COR_TEXTO = (230, 235, 240)
        self.COR_TEXTO_MUTED = (140, 145, 150)
        self.COR_BOTAO = (40, 50, 65)
        
        self.COR_BOTAO_HOVER = (60, 75, 95)
        self.COR_BOTAO_ATIVO = (46, 204, 113)
        self.COR_BOTAO_STOP = (150, 40, 40)
        
        self.fonte_p = pygame.font.Font(None, 20)
        self.fonte_m = pygame.font.Font(None, 22)
        self.fonte_g = pygame.font.Font(None, 28)
        
        self.surface_camera = pygame.Surface((306, 125))
        
        self.X_P, self.Y_P = 640, 420
        self.botoes = {
            "AUTO":     pygame.Rect(self.X_P + 15,  self.Y_P + 48,  80, 32),
            "MANUAL":   pygame.Rect(self.X_P + 15,  self.Y_P + 95,  80, 32),
            "ESQUERDA": pygame.Rect(self.X_P + 115, self.Y_P + 72,  55, 32),
            "PARAR":    pygame.Rect(self.X_P + 177, self.Y_P + 72,  65, 32),
            "DIREITA":  pygame.Rect(self.X_P + 249, self.Y_P + 72,  55, 32),
            "SP_MAIS":  pygame.Rect(self.X_P + 312, self.Y_P + 48,  32, 32),
            "SP_MENOS": pygame.Rect(self.X_P + 312, self.Y_P + 95,  32, 32)
        }
        
    def desenhar_painel_controle(self, comandos_remotos):
        pygame.draw.rect(self.tela, self.COR_PAINEL, (self.X_P, self.Y_P, 360, 160), border_radius=8)
        pygame.draw.rect(self.tela, self.COR_BORDA, (self.X_P, self.Y_P, 360, 160), 1, border_radius=8)
        
        lbl = self.fonte_g.render("PAINEL DE COMANDO", True, self.COR_ROBO)
        self.tela.blit(lbl, (self.X_P + 15, self.Y_P + 12))
        
        pos_mouse = pygame.mouse.get_pos()
        
        for nome, ret in self.botoes.items():
            cor_fundo_btn = self.COR_BOTAO
            
            if nome == "AUTO" and comandos_remotos.get("c_automatico", False):
                cor_fundo_btn = self.COR_BOTAO_ATIVO
            elif nome == "MANUAL" and comandos_remotos.get("c_man", False):
                cor_fundo_btn = self.COR_BOTAO_ATIVO
            elif nome == "PARAR" and comandos_remotos.get("c_para", False):
                cor_fundo_btn = self.COR_BOTAO_STOP
            elif nome == "DIREITA" and comandos_remotos.get("c_direita", False):
                cor_fundo_btn = self.COR_BOTAO_ATIVO
            elif nome == "ESQUERDA" and comandos_remotos.get("c_esquerda", False):
                cor_fundo_btn = self.COR_BOTAO_ATIVO
                
            if ret.collidepoint(pos_mouse) and cor_fundo_btn not in [self.COR_BOTAO_ATIVO, self.COR_BOTAO_STOP]:
                cor_fundo_btn = self.COR_BOTAO_HOVER
                
            pygame.draw.rect(self.tela, cor_fundo_btn, ret, border_radius=6)
            pygame.draw.rect(self.tela, self.COR_BORDA, ret, 1, border_radius=6)
            
            label_texto = "+" if nome == "SP_MAIS" else "-" if nome == "SP_MENOS" else nome
            texto = self.fonte_p.render(label_texto, True, self.COR_TEXTO)
            text_rect = texto.get_rect(center=ret.center)
            self.tela.blit(texto, text_rect)
            
        return self.botoes

    def desenhar_ambiente(self, sim_fisico, leitura_lidar, e_inspecao):
        self.tela.fill(self.COR_FUNDO)
        
        pygame.draw.rect(self.tela, (24, 24, 27), (0, 0, self.largura, 400))
        pygame.draw.line(self.tela, self.COR_BORDA, (0, 400), (self.largura, 400), 2)
        
        escala_x = 15.0
        robo_tela_x = 200
        offset_visual_x = robo_tela_x - (sim_fisico.posicao_x * escala_x)
        
        deslocamento_solo_robo = 0
        if 20.0 <= sim_fisico.posicao_x <= 40.0:
            deslocamento_solo_robo = int((sim_fisico.posicao_x - 20.0) * 5.0)
        elif sim_fisico.posicao_x > 40.0:
            deslocamento_solo_robo = int((40.0 - 20.0) * 5.0)
            
        robo_tela_y = 275 + deslocamento_solo_robo
        
        pontos_solo = []
        pontos_solo.append((0, self.altura))
        for x_pixel in range(0, self.largura):
            x_fisico = (x_pixel - offset_visual_x) / escala_x
            y_pixel_solo = 300
            if 20.0 <= x_fisico <= 40.0:
                y_pixel_solo += int((x_fisico - 20.0) * 5.0)
            elif x_fisico > 40.0:
                y_pixel_solo += int((40.0 - 20.0) * 5.0)
            pontos_solo.append((x_pixel, y_pixel_solo))
        pontos_solo.append((self.largura, self.altura))
        
        pygame.draw.polygon(self.tela, (40, 40, 45), pontos_solo)
        linhas_superficie_solo = pontos_solo[1:-1]
        pygame.draw.lines(self.tela, (70, 70, 75), False, linhas_superficie_solo, 2)
        
        pontos_teto = []
        pontos_teto.append((0, 0))
        for x_pixel in range(0, self.largura):
            x_fisico = (x_pixel - offset_visual_x) / escala_x
            altura_teto_local = sim_fisico.altura_nominal_teto
            
            if 10.0 <= x_fisico <= 14.0:
                altura_teto_local = 150.0
            elif 45.0 <= x_fisico <= 48.0:
                altura_teto_local = 70.0
                
            y_pixel_teto = int(300 - altura_teto_local)
            if 20.0 <= x_fisico <= 40.0:
                y_pixel_teto += int((x_fisico - 20.0) * 5.0)
            elif x_fisico > 40.0:
                y_pixel_teto += int((40.0 - 20.0) * 5.0)
            pontos_teto.append((x_pixel, y_pixel_teto))
        pontos_teto.append((self.largura, 0))
        
        if len(pontos_teto) > 3:
            pygame.draw.polygon(self.tela, (35, 35, 38), pontos_teto)
            linhas_contorno = pontos_teto[1:-1]
            pygame.draw.lines(self.tela, self.COR_CONCRETO, False, linhas_contorno, 3)
            
        # Rover
        surf_robo = pygame.Surface((60, 40), pygame.SRCALPHA)
        pygame.draw.rect(surf_robo, (40, 45, 50), (4, 16, 52, 12), border_radius=2) 
        pygame.draw.rect(surf_robo, self.COR_ROBO, (8, 6, 44, 14), border_radius=4)
        pygame.draw.rect(surf_robo, (20, 30, 35), (14, 10, 32, 6))
        pygame.draw.circle(surf_robo, (10, 10, 12), (14, 28), 7)
        pygame.draw.circle(surf_robo, (10, 10, 12), (46, 28), 7)
        pygame.draw.circle(surf_robo, (50, 55, 60), (14, 28), 3)
        pygame.draw.circle(surf_robo, (50, 55, 60), (46, 28), 3)
        pygame.draw.rect(surf_robo, (80, 85, 90), (26, 0, 8, 8))
        pygame.draw.ellipse(surf_robo, (30, 30, 35), (22, -2, 16, 6))
        
        if sim_fisico.angulo_declive_graus > 0:
            surf_robo = pygame.transform.rotate(surf_robo, -sim_fisico.angulo_declive_graus)
            
        self.tela.blit(surf_robo, (robo_tela_x - 30, robo_tela_y - 20))
        
        y_teto_atual = 300 - leitura_lidar + deslocamento_solo_robo
        pygame.draw.line(self.tela, self.COR_LASER, (robo_tela_x, robo_tela_y - 14), (robo_tela_x, y_teto_atual), 2)
        pygame.draw.circle(self.tela, self.COR_LASER, (robo_tela_x, y_teto_atual), 4)
        
        if e_inspecao:
            pygame.draw.circle(self.tela, self.COR_ALERTA, (robo_tela_x, y_teto_atual), 18, 2)
            lbl_alt = self.fonte_g.render("SISTEMA EMBARCADO: CRÍTICO - FALHA DETECTADA", True, self.COR_ALERTA)
            self.tela.blit(lbl_alt, (30, 25))

    def atualizar_painel_dados(self, sim_fisico, comandos_remotos, log_recente):
        X_TAB, Y_TAB = 350, 420  # Centralizado no rodapé
        pygame.draw.rect(self.tela, self.COR_PAINEL, (X_TAB, Y_TAB, 270, 160), border_radius=8)
        pygame.draw.rect(self.tela, self.COR_BORDA, (X_TAB, Y_TAB, 270, 160), 1, border_radius=8)
        
        lbl_metrica = self.fonte_p.render("MÉTRICA TELEMETRIA", True, self.COR_TEXTO_MUTED)
        lbl_valor = self.fonte_p.render("VALOR", True, self.COR_TEXTO_MUTED)
        self.tela.blit(lbl_metrica, (X_TAB + 15, Y_TAB + 12))
        self.tela.blit(lbl_valor, (X_TAB + 190, Y_TAB + 12))
        pygame.draw.line(self.tela, self.COR_BORDA, (X_TAB, Y_TAB + 30), (X_TAB + 270, Y_TAB + 30), 1)
        
        leitura_atual_lidar = log_recente.get('y', sim_fisico.ler_sensor_lidar()) if log_recente else sim_fisico.ler_sensor_lidar()
        
        dados = [
            ("Posição Horizontal X", f"{sim_fisico.posicao_x:.2f} m"),
            ("Velocidade do Rover", f"{sim_fisico.velocidade_x:.2f} m/s"),
            ("Altura do Teto (LIDAR)", f"{leitura_atual_lidar:.1f} cm"),
            ("Inclinação IMU (Pitch)", f"{sim_fisico.angulo_declive_graus:.1f}°")
        ]
        
        linha_y = Y_TAB + 38
        for label, val in dados:
            t_lbl = self.fonte_p.render(label, True, self.COR_TEXTO)
            cor_valor = self.COR_ALERTA if label == "Altura do Teto (LIDAR)" and leitura_atual_lidar != 100.0 else self.COR_ROBO
            t_val = self.fonte_p.render(val, True, cor_valor)
            self.tela.blit(t_lbl, (X_TAB + 15, linha_y))
            self.tela.blit(t_val, (X_TAB + 190, linha_y))
            linha_y += 20
            
        if log_recente:
            pygame.draw.line(self.tela, self.COR_BORDA, (X_TAB, Y_TAB + 125), (X_TAB + 270, Y_TAB + 125), 1)
            conf = log_recente.get('nivel_confianca', 0.0) * 100
            cor_conf = (46, 204, 113) if conf > 70 else self.COR_ALERTA
            t_conf = self.fonte_p.render(f"Confiança Online: {conf:.1f}%", True, cor_conf)
            self.tela.blit(t_conf, (X_TAB + 15, Y_TAB + 135))

    def renderizar_frame_yolo(self, frame_opencv, objetos_detectados):
        X_CAM, Y_CAM = 690, 250
        pygame.draw.rect(self.tela, self.COR_PAINEL, (X_CAM, Y_CAM, 314, 160), border_radius=8)
        pygame.draw.rect(self.tela, self.COR_BORDA, (X_CAM, Y_CAM, 314, 160), 1, border_radius=8)
        
        if frame_opencv is not None:
            try:
                frame_pequeno = cv2.resize(frame_opencv, (306, 125))
                frame_rgb = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2RGB)
                frame_pygame = frame_rgb.swapaxes(0, 1)
                
                pygame.pixelcopy.array_to_surface(self.surface_camera, frame_pygame)
                
                if objetos_detectados:
                    for obj in objetos_detectados:
                        txt = self.fonte_p.render(f"YOLO: {obj['classe'].upper()} ({obj['confianca']*100:.0f}%)", True, (255, 60, 60))
                        self.surface_camera.blit(txt, (10, 10))
                        
                        if "BURACO" in obj['classe'].upper():
                            pygame.draw.rect(self.surface_camera, (255, 50, 50), (95, 20, 115, 85), 2)
                        elif "SALIENCIA" in obj['classe'].upper():
                            pygame.draw.rect(self.surface_camera, (255, 50, 50), (110, 45, 85, 35), 2)
                
                self.tela.blit(self.surface_camera, (X_CAM + 4, Y_CAM + 30))
                
            except Exception as e:
                print(f"[ERRO RENDERING CAM]: {e}")
            
            lbl_cam = self.fonte_p.render("FEED DA CÂMERA EM TEMPO REAL", True, self.COR_ALERTA)
            self.tela.blit(lbl_cam, (X_CAM + 12, Y_CAM + 8))
        else:
            self.surface_camera.fill((20, 20, 22))
            txt_standby = self.fonte_p.render("AGUARDANDO ATIVAÇÃO POR ANOMALIA", True, self.COR_TEXTO_MUTED)
            text_rect = txt_standby.get_rect(center=(153, 62))
            self.surface_camera.blit(txt_standby, text_rect)
            self.tela.blit(self.surface_camera, (X_CAM + 4, Y_CAM + 30))
            
            lbl_cam = self.fonte_p.render("FEED DA CÂMERA (STANDBY)", True, self.COR_TEXTO_MUTED)
            self.tela.blit(lbl_cam, (X_CAM + 12, Y_CAM + 10))

    def desenhar_grafico_lidar(self, historico_lidar):
        X_GRAF, Y_GRAF, LARG_G, ALT_G = 20, 420, 310, 160 # Mantido na base inferior esquerda
        
        pygame.draw.rect(self.tela, self.COR_PAINEL, (X_GRAF, Y_GRAF, LARG_G, ALT_G), border_radius=8)
        pygame.draw.rect(self.tela, self.COR_BORDA, (X_GRAF, Y_GRAF, LARG_G, ALT_G), 1, border_radius=8)
        
        lbl_titulo = self.fonte_p.render("MÁSCARA DE MAPEAMENTO DO TETO (2D)", True, self.COR_TEXTO_MUTED)
        self.tela.blit(lbl_titulo, (X_GRAF + 15, Y_GRAF + 10))
        
        X_INTERNO, Y_INTERNO = X_GRAF + 40, Y_GRAF + 35
        LARG_INTERNA, ALT_INTERNA = LARG_G - 55, ALT_G - 60
        pygame.draw.rect(self.tela, (15, 15, 18), (X_INTERNO, Y_INTERNO, LARG_INTERNA, ALT_INTERNA))
        
        for i in range(1, 4):
            y_linha = Y_INTERNO + (ALT_INTERNA // 4) * i
            pygame.draw.line(self.tela, (35, 35, 40), (X_INTERNO, y_linha), (X_INTERNO + LARG_INTERNA, y_linha), 1)
            x_linha = X_INTERNO + (LARG_INTERNA // 4) * i
            pygame.draw.line(self.tela, (35, 35, 40), (x_linha, Y_INTERNO), (x_linha, Y_INTERNO + ALT_INTERNA), 1)

        lbl_y1 = self.fonte_p.render("150", True, self.COR_TEXTO_MUTED)
        lbl_y2 = self.fonte_p.render("100", True, self.COR_TEXTO_MUTED)
        lbl_y3 = self.fonte_p.render("70", True, self.COR_TEXTO_MUTED)
        self.tela.blit(lbl_y1, (X_GRAF + 12, Y_INTERNO))
        self.tela.blit(lbl_y2, (X_GRAF + 12, Y_INTERNO + (ALT_INTERNA // 2) - 6))
        self.tela.blit(lbl_y3, (X_GRAF + 19, Y_INTERNO + ALT_INTERNA - 10))
        
        lbl_x = self.fonte_p.render("PERFIL DO TÚNEL (METROS)", True, self.COR_TEXTO_MUTED)
        self.tela.blit(lbl_x, (X_INTERNO + (LARG_INTERNA // 2) - 70, Y_INTERNO + ALT_INTERNA + 8))

        if len(historico_lidar) > 1:
            pontos_grafico = []
            for pos_x, leitura in historico_lidar:
                pixel_g_x = X_INTERNO + int((pos_x / 55.0) * LARG_INTERNA)
                porcentagem_y = (leitura - 50) / (170 - 50)
                pixel_g_y = Y_INTERNO + ALT_INTERNA - int(porcentagem_y * ALT_INTERNA)
                
                if X_INTERNO <= pixel_g_x <= X_INTERNO + LARG_INTERNA:
                    pontos_grafico.append((pixel_g_x, pixel_g_y))
            
            if len(pontos_grafico) > 1:
                pygame.draw.lines(self.tela, (46, 204, 113), False, pontos_grafico, 2)

    def atualizar_tela(self):
        pygame.display.flip()