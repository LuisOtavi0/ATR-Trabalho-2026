import json
import paho.mqtt.client as mqtt

try:
    import zmq
    ZMQ_DISPONIVEL = True
except ImportError:
    import time
    ZMQ_DISPONIVEL = False

class GerenciadorComunicacao:
    def __init__(self, broker_mqtt="localhost", porta_mqtt=1883):
        # --- CONFIGURAÇÃO DO MQTT (OPERAÇÃO REMOTA) ---
        self.cliente_mqtt = mqtt.Client(protocol=mqtt.MQTTv311)
        self.broker_mqtt = broker_mqtt
        self.porta_mqtt = porta_mqtt
        
        # Estado compartilhado dos comandos recebidos via MQTT da Operação Remota
        self.comandos_remotos = {
            "c_automatico": False,
            "c_man": False,
            "j_sp_velocidade": 0,
            "c_direita": False,
            "c_esquerda": False,
            "c_para": False
        }

        # --- CONFIGURAÇÃO DO ZMQ (IPC LOCAL ENTRE SIMULADOR E ROBÔ) ---
        self.contexto_zmq = None
        self.socket_ipc = None
        if ZMQ_DISPONIVEL:
            self.contexto_zmq = zmq.Context()
            # Criamos um socket do tipo REP (Reply/Resposta). O robô C++ enviará uma REQ (Request)
            # pedindo os sensores e enviando a aceleração, e o simulador responderá.
            self.socket_ipc = self.contexto_zmq.socket(zmq.REP)
            self.socket_ipc.bind("tcp://*:5555") # Escuta na porta local 5555

    # --- MÉTODOS MQTT (PUBLISHER / SUBSCRIBER) ---
    
    def conectar_mqtt(self):
        """Inicializa a conexão com o Broker Mosquitto e assina os tópicos de comando."""
        self.cliente_mqtt.on_connect = self._on_connect
        self.cliente_mqtt.on_message = self._on_message
        try:
            self.cliente_mqtt.connect(self.broker_mqtt, self.porta_mqtt, 60)
            self.cliente_mqtt.loop_start() # Roda o loop de rede MQTT em uma thread separada do Python
            print("[COMUNICAÇÃO] Conectado ao Broker MQTT com sucesso.")
        except Exception as e:
            print(f"[COMUNICAÇÃO ERRO] Falha ao conectar no MQTT: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Conectado com código de retorno: {rc}")
        # Inscreve-se no tópico onde a interface gráfica de operação remota publica comandos
        client.subscribe("robo/comando/#")

    def _on_message(self, client, userdata, msg):
        """Callback acionado assincronamente quando um comando da Operação Remota chega."""
        try:
            topico = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Atualiza o dicionário de comandos com base no sub-tópico recebido
            if "c_automatico" in topico: self.comandos_remotos["c_automatico"] = bool(payload)
            elif "c_man" in topico: self.comandos_remotos["c_man"] = bool(payload)
            elif "j_sp_velocidade" in topico: self.comandos_remotos["j_sp_velocidade"] = int(payload)
            elif "direcao" in topico:
                self.comandos_remotos["c_direita"] = (payload == "direita")
                self.comandos_remotos["c_esquerda"] = (payload == "esquerda")
                self.comandos_remotos["c_para"] = (payload == "para")
        except Exception as e:
            print(f"[MQTT ERRO] Falha ao processar mensagem: {e}")

    def publicar_telemetria(self, log_entry):
        """Envia os dados consolidados do coletor de dados para a Operação Remota via MQTT."""
        # Transforma o dicionário/objeto do log em uma string JSON para transmissão na rede
        payload = json.dumps(log_entry)
        self.cliente_mqtt.publish("robo/telemetria", payload, qos=0)

    # --- MÉTODOS ZERO M_Q (IPC - COMUNICAÇÃO ENTRE PROCESSOS) ---

    def trocar_dados_ipc(self, dados_sensores):
        """
        Bloqueia a execução aguardando uma requisição do robô C++.
        Assim que recebe, envia os sensores e retorna o comando de aceleração do motor.
        """
        if not ZMQ_DISPONIVEL:
            return 0.0 

        try:
            # 1. Aguarda a mensagem do Robô C++ (Bloqueante)
            mensagem_recebida = self.socket_ipc.recv_string()
            requisicao_robo = json.loads(mensagem_recebida)
            
            # Extrai o sinal de atuação que o robô calculou no PID de C++
            aceleracao_calculada = float(requisicao_robo.get("o_aceleracao", 0.0))

            # 2. Responde imediatamente enviando o frame de sensores atuais do simulador
            payload_resposta = json.dumps(dados_sensores)
            self.socket_ipc.send_string(payload_resposta)

            return aceleracao_calculada
        except Exception as e:
            print(f"[IPC ERRO] Falha na troca de dados via ZeroMQ: {e}")
            return 0.0