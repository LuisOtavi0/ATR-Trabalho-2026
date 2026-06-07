import os
import cv2
import numpy as np

# Tratamento para importar a biblioteca YOLO sem travar caso não esteja instalada no primeiro teste
try:
    from ultralytics import YOLO
    YOLO_DISPONIVEL = True
except ImportError:
    YOLO_DISPONIVEL = False

class DetectorYOLO:
    def __init__(self):
        self.modelo = None
        if YOLO_DISPONIVEL:
            try:
                # Carrega o modelo YOLOv8 Nano pré-treinado (leve e ideal para Tempo Real)
                # Na primeira execução, a biblioteca baixa automaticamente o arquivo 'yolov8n.pt'
                self.modelo = YOLO("yolov8n.pt")
            except Exception as e:
                print(f"[AVISO YOLO] Erro ao carregar peso nativo: {e}. Operando em modo emulado.")
        else:
            print("[AVISO YOLO] Biblioteca 'ultralytics' não encontrada. Operando em modo emulado.")

    def gerar_imagem_teto_simulada(self, tipo_falha):
        """
        Gera uma matriz de imagem (numpy array) em tempo real representando o que a câmera do robô
        enxergaria no teto do túnel, dependendo da posição física.
        """
        # Cria uma imagem preta de 480x640 pixels com 3 canais de cor (RGB)
        img = np.zeros((480, 640, 3), dtype=np.uint8) + 50 # Fundo cinza escuro (teto de concreto)

        # Adiciona texturas simulando as paredes do túnel
        for _ in range(30):
            x = np.random.randint(0, 640)
            y = np.random.randint(0, 480)
            cv2.circle(img, (x, y), np.random.randint(1, 3), (20, 20, 20), -1)

        # Se houver uma falha estrutural na posição atual, desenha o obstáculo/objeto
        if tipo_falha == "BURACO":
            # Desenha um círculo irregular escuro simulando desmoronamento ou buraco profunda
            cv2.circle(img, (320, 240), 80, (10, 10, 10), -1)
            cv2.ellipse(img, (320, 240), (85, 75), 30, 0, 360, (30, 30, 30), 3)
        elif tipo_falha == "SALIENCIA":
            # Desenha uma rachadura ou obstáculo (ex: um bloco solto ou fiação caída)
            cv2.rectangle(img, (240, 200), (400, 280), (120, 90, 70), -1)
            cv2.line(img, (240, 200), (400, 280), (0, 0, 255), 4) # Linha vermelha simulando trinca estrutural
            
        return img

    def processar_inspecao_visual(self, posicao_x, leitura_lidar):
        """
        Determina o cenário com base na posição do mapa, gera a imagem e executa a inferência
        pesada da Inteligência Artificial (YOLO).
        """
        # 1. Identifica se geometricamente há anomalia na posição atual
        tipo_falha = "NENHUMA"
        if 10.0 <= posicao_x <= 14.0:
            tipo_falha = "BURACO"
        elif 45.0 <= posicao_x <= 48.0:
            tipo_falha = "SALIENCIA"

        # 2. Sintetiza o frame da câmera
        frame = self.gerar_imagem_teto_simulada(tipo_falha)

        # 3. Executa a inferência de IA (Processamento Pesado)
        objetos_detectados = []
        
        if self.modelo is not None and YOLO_DISPONIVEL:
            # Roda a imagem gerada dentro da rede neural convolucional da YOLO
            # if=False impede que o terminal seja inundado de logs a cada milissegundo
            resultados = self.modelo(frame, verbose=False)[0]
            
            # Extrai as caixas delimitadoras (Bounding Boxes) encontradas pela IA
            for box in resultados.boxes:
                cls_id = int(box.cls[0])
                label = self.modelo.names[cls_id]
                conf = float(box.conf[0])
                # Filtra apenas detecções com mais de 40% de certeza
                if conf > 0.4:
                    objetos_detectados.append({"classe": label, "confianca": conf})
        else:
            # Modo de contingência matemática (Gasta CPU calculando matriz para emular o delay da IA)
            # Se o ambiente não tiver a biblioteca instalada, esse laço garante o estresse de CPU exigido
            matriz_dummy = np.random.rand(300, 300)
            for _ in range(5):
                matriz_dummy = np.dot(matriz_dummy, matriz_dummy)
            
            if tipo_falha != "NENHUMA":
                objetos_detectados.append({"classe": f"Anomalia_{tipo_falha}", "confianca": 0.88})

        return frame, objetos_detectados