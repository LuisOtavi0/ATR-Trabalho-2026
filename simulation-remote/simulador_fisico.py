import math
import random

class SimuladorFisico:
    def __init__(self):
        self.massa       = 15.0   # kg
        self.posicao_x   = 0.0    # metros
        self.velocidade_x = 0.0   # m/s
        self.atrito_k    = 0.5    # coeficiente de atrito viscoso
        self.g           = 9.81   # m/s²

        # --- BÔNUS: Declive ---
        self.angulo_declive_graus = 0.0

        # --- PERFIL DO TETO ---
        self.altura_nominal_teto = 100.0  # cm

        # --- ENCODER (estado lógico que alterna a cada metro percorrido) ---
        # Inicializado com o metro ATUAL da posição inicial para que a primeira
        # chamada a ler_sensor_encoder() em pos=0 NÃO provoque toggle espúrio.
        # (Inicializar com -1 causava toggle imediato porque int(0) != -1.)
        self._encoder_state        = False
        self._encoder_ultimo_metro = int(self.posicao_x)  # = 0 no startup

    def atualizar_fisica(self, comando_aceleracao_percentual, dt=0.020):
        """Aplica leis de Newton F=ma para simular a dinâmica do robô."""
        # Inclinação baseada em posição (BÔNUS Declive)
        if 20.0 <= self.posicao_x <= 40.0:
            self.angulo_declive_graus = 12.0
        else:
            self.angulo_declive_graus = 0.0

        angulo_rad = math.radians(self.angulo_declive_graus)

        F_motor    = (comando_aceleracao_percentual / 100.0) * 30.0  # N
        F_grav     = self.massa * self.g * math.sin(angulo_rad)
        F_atrito   = -self.atrito_k * self.velocidade_x
        F_total    = F_motor + F_grav + F_atrito

        aceleracao = F_total / self.massa
        self.velocidade_x += aceleracao * dt
        if self.posicao_x <= 0.0 and self.velocidade_x < 0:
            self.velocidade_x = 0.0
        self.posicao_x += self.velocidade_x * dt

        return aceleracao

    def ler_sensor_encoder(self):
        """
        Retorna o estado lógico do encoder.
        Alterna (0→1 ou 1→0) exatamente uma vez a cada metro percorrido.
        """
        metro_atual = int(self.posicao_x)
        if metro_atual != self._encoder_ultimo_metro:
            self._encoder_state       = not self._encoder_state
            self._encoder_ultimo_metro = metro_atual
        return self._encoder_state

    def ler_sensor_imu(self, aceleracao_real):
        """BÔNUS: Emula IMU com ruído gaussiano."""
        ruido = random.gauss(0.0, 0.05)
        return aceleracao_real + ruido, self.angulo_declive_graus

    def ler_sensor_lidar(self):
        """
        Simula LIDAR vertical (distância até o teto).
        Injeta anomalias: buraco (aumento de altura) e saliência (redução).
        """
        altura_teto = self.altura_nominal_teto

        if 10.0 <= self.posicao_x <= 14.0:
            altura_teto = 150.0   # Buraco: teto mais alto
        elif 45.0 <= self.posicao_x <= 48.0:
            altura_teto = 70.0    # Saliência: teto mais baixo

        ruido = random.randint(-2, 2)
        return int(altura_teto + ruido)
