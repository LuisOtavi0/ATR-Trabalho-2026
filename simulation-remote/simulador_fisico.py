import math
import random

class SimuladorFisico:
    def __init__(self):
        self.massa       = 15.0
        self.posicao_x   = 0.0
        self.velocidade_x = 0.0
        self.atrito_k    = 0.5
        self.g           = 9.81

        self.angulo_declive_graus = 0.0

        self.altura_nominal_teto = 100.0

        self._encoder_state        = False
        self._encoder_ultimo_metro = int(self.posicao_x)

    def atualizar_fisica(self, comando_aceleracao_percentual, dt=0.020):
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
        metro_atual = int(self.posicao_x)
        if metro_atual != self._encoder_ultimo_metro:
            self._encoder_state       = not self._encoder_state
            self._encoder_ultimo_metro = metro_atual
        return self._encoder_state

    def ler_sensor_imu(self, aceleracao_real):
        ruido = random.gauss(0.0, 0.05)
        return aceleracao_real + ruido, self.angulo_declive_graus

    def ler_sensor_lidar(self):
        altura_teto = self.altura_nominal_teto

        if 10.0 <= self.posicao_x <= 14.0:
            altura_teto = 150.0
        elif 45.0 <= self.posicao_x <= 48.0:
            altura_teto = 70.0

        ruido = random.randint(-2, 2)
        return int(altura_teto + ruido)
