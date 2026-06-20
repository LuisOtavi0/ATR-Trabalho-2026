import json
import threading
import paho.mqtt.client as mqtt

try:
    import zmq
    ZMQ_DISPONIVEL = True
except ImportError:
    ZMQ_DISPONIVEL = False


class GerenciadorComunicacao:

    def __init__(self, broker_mqtt="localhost", porta_mqtt=1883):
        self.cliente_mqtt   = mqtt.Client(protocol=mqtt.MQTTv311)
        self.broker_mqtt    = broker_mqtt
        self.porta_mqtt     = porta_mqtt
        self._mqtt_ok       = False

        self.comandos_remotos = {
            "c_automatico": False,
            "c_man":        False,
            "j_sp_velocidade": 0,
            "c_direita":    False,
            "c_esquerda":   False,
            "c_para":       False,
        }

        self._lock                = threading.Lock()
        self._ultimo_aceleracao   = 0.0
        self._ultimos_sensores    = {
            "i_lidar": 100, "i_encoder": False, "velocidade": 0.0
        }
        self._zmq_ativo     = False
        self._cpp_conectado = False

        if ZMQ_DISPONIVEL:
            self._ctx_zmq   = zmq.Context()
            self._sock_ipc  = self._ctx_zmq.socket(zmq.REP)
            try:
                self._sock_ipc.bind("tcp://*:5555")
                self._zmq_ativo = True
                t = threading.Thread(
                    target=self._loop_ipc_background, daemon=True, name="zmq-rep")
                t.start()
                print("[IPC] Servidor ZMQ REP escutando em :5555 (thread background).")
            except zmq.ZMQError as e:
                print(f"[IPC AVISO] Porta 5555 indisponível: {e}")
                print("[IPC] Operando em modo visualizador (sem IPC ativo).")
                self._sock_ipc.close()

    def _loop_ipc_background(self):

        while self._zmq_ativo:
            try:
                if not self._sock_ipc.poll(timeout=100, flags=zmq.POLLIN):
                    continue

                msg = self._sock_ipc.recv_string()
                req = json.loads(msg)

                with self._lock:
                    self._cpp_conectado     = True
                    self._ultimo_aceleracao = float(req.get("o_aceleracao", 0.0))
                    sensores_snapshot = dict(self._ultimos_sensores)

                self._sock_ipc.send_string(json.dumps(sensores_snapshot))

            except zmq.ZMQError as e:
                if self._zmq_ativo:
                    print(f"[IPC ERRO ZMQ] {e}")
            except Exception as e:
                print(f"[IPC ERRO] {e}")

    def atualizar_sensores_ipc(self, dados_sensores: dict):
        with self._lock:
            self._ultimos_sensores = dados_sensores

    def obter_aceleracao_ipc(self) -> float:
        with self._lock:
            return self._ultimo_aceleracao

    @property
    def cpp_conectado(self) -> bool:
        with self._lock:
            return self._cpp_conectado

    def conectar_mqtt(self):
        self.cliente_mqtt.on_connect = self._on_connect
        self.cliente_mqtt.on_message = self._on_message
        try:
            self.cliente_mqtt.connect(self.broker_mqtt, self.porta_mqtt, keepalive=60)
            self.cliente_mqtt.loop_start()
            self._mqtt_ok = True
            print("[MQTT] Conectado ao broker com sucesso.")
        except Exception as e:
            print(f"[MQTT AVISO] Broker não acessível ({e}). MQTT desativado.")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("robo/comando/#")
            print("[MQTT] Inscrito em robo/comando/#")

    def _on_message(self, client, userdata, msg):
        try:
            topico  = msg.topic
            payload = json.loads(msg.payload.decode())

            if "c_automatico"    in topico: self.comandos_remotos["c_automatico"]    = bool(payload)
            elif "c_man"         in topico: self.comandos_remotos["c_man"]           = bool(payload)
            elif "j_sp_velocidade" in topico: self.comandos_remotos["j_sp_velocidade"] = int(payload)
            elif "direcao"       in topico:
                dir_str = payload if isinstance(payload, str) else str(payload)
                self.comandos_remotos["c_direita"]  = (dir_str == "direita")
                self.comandos_remotos["c_esquerda"] = (dir_str == "esquerda")
                self.comandos_remotos["c_para"]     = (dir_str == "para")
        except Exception as e:
            print(f"[MQTT ERRO] {e}")

    def publicar_telemetria(self, log_entry: dict):
        if not self._mqtt_ok:
            return
        try:
            self.cliente_mqtt.publish("robo/telemetria", json.dumps(log_entry), qos=0)
        except Exception:
            pass
