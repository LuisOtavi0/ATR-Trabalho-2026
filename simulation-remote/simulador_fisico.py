import math
import random
import time

class SimuladorFisico:
    def __init__(self):
        self.massa = 15.0          # Massa do robô em kg
        self.posicao_x = 0.0       # Posição horizontal real (metros)
        self.velocidade_x = 0.0    # Velocidade horizontal real (m/s)
        self.atrito_k = 0.5        # Coeficiente de atrito/resistência do ar
        self.g = 9.81              # Aceleração da gravidade (m/s²)
        
        # --- MODELAGEM DO TÚNEL E DECLIVE (BÔNUS) ---
        # Definimos o ângulo de inclinação do túnel (em radianos) baseado em trechos
        # Exemplo: de 0 a 20m é plano, de 20m a 40m é um declive de 10 graus, depois volta a ser plano.
        self.angulo_declive_graus = 0.0
        
        # --- PERFIL DO TETO DO TÚNEL (LIDAR) ---
        self.altura_nominal_teto = 100.0  # Altura padrão do teto em cm
        
    def atualizar_fisica(self, comando_aceleracao_percentual, dt=0.020):
        """
        Aplica as Leis da Mecânica Clássica de Newton para atualizar a dinâmica do robô.
        Executado periodicamente para simular o tempo real.
        """
        # 1. Determina a inclinação do terreno baseado na posição X (BÔNUS Declive)
        if 20.0 <= self.posicao_x <= 40.0:
            self.angulo_declive_graus = 12.0  # Declive de 12 graus
        else:
            self.angulo_declive_graus = 0.0   # Terreno plano
            
        angulo_rad = math.radians(self.angulo_declive_graus)
        
        # 2. Cálculo das Forças atuando no robô (F = m * a)
        F_motor = (comando_aceleracao_percentual / 100.0) * 30.0 
        
        F_gravidade = self.massa * self.g * math.sin(angulo_rad)
        
        F_atrito = -self.atrito_k * self.velocidade_x
        
        F_total = F_motor + F_gravidade + F_atrito
        
        aceleracao = F_total / self.massa
        
        self.velocidade_x += aceleracao * dt
        # Garante que o robô não ande de ré além do início do túnel
        if self.posicao_x == 0.0 and self.velocidade_x < 0:
            self.velocidade_x = 0.0
            
        self.posicao_x += self.velocidade_x * dt
        
        # Retorna a aceleração linear real para alimentar o sensor IMU
        return aceleracao

    def ler_sensor_imu(self, aceleracao_real):
        """
        BÔNUS: Emula um sensor IMU (Unidade de Medição Inercial).
        Retorna a aceleração linear com ruído e o ângulo de inclinação (Pitch).
        """
        ruido_imu = random.gauss(0.0, 0.05) # Ruído branco gaussiano típico de sensores físicos
        imu_ax = aceleracao_real + ruido_imu
        imu_pitch = self.angulo_declive_graus # Ângulo de inclinação
        
        return imu_ax, imu_pitch

    def ler_sensor_lidar(self):
        """
        Simula a leitura do sensor LIDAR vertical baseado no perfil geométrico do túnel.
        Adiciona anomalias (buracos e saliências) e ruído de medição.
        """
        altura_teto = self.altura_nominal_teto
        
        # Injeta uma falha do tipo BURACO (Aumento de altura) entre os metros 10 e 14
        if 10.0 <= self.posicao_x <= 14.0:
            altura_teto = 150.0  # Buraco de 50 cm no teto
            
        # Injeta uma falha do tipo SALIÊNCIA (Redução de altura) entre os metros 45 e 48
        elif 45.0 <= self.posicao_x <= 48.0:
            altura_teto = 70.0   # Saliência/Rachadura que estufa o teto para baixo
            
        # Adiciona ruído de medição do sensor (LIDAR real oscila alguns centímetros)
        ruido_lidar = random.randint(-2, 2)
        leitura_final = int(altura_teto + ruido_lidar)
        
        return leitura_final