import os
import cv2
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_DISPONIVEL = True
except ImportError:
    YOLO_DISPONIVEL = False

class DetectorYOLO:
    def __init__(self):
        self.modelo = None
        
        self._img_base = np.zeros((480, 640, 3), dtype=np.uint8) + 50
        for _ in range(30):
            x = np.random.randint(0, 640)
            y = np.random.randint(0, 480)
            cv2.circle(self._img_base, (x, y), np.random.randint(1, 3), (20, 20, 20), -1)
            
        self._img_buraco = self._img_base.copy()
        cv2.circle(self._img_buraco, (320, 240), 80, (10, 10, 10), -1)
        cv2.ellipse(self._img_buraco, (320, 240), (85, 75), 30, 0, 360, (30, 30, 30), 3)
        
        self._img_saliencia = self._img_base.copy()
        cv2.rectangle(self._img_saliencia, (240, 200), (400, 280), (120, 90, 70), -1)
        cv2.line(self._img_saliencia, (240, 200), (400, 280), (0, 0, 255), 4)
        
        if YOLO_DISPONIVEL:
            try:
                self.modelo = YOLO("yolov8n.pt")
            except Exception as e:
                print(f"[AVISO YOLO] Erro ao carregar peso nativo: {e}. Operando em modo emulado.")
        else:
            print("[AVISO YOLO] Biblioteca 'ultralytics' não encontrada. Operando em modo emulado.")

    def gerar_imagem_teto_simulada(self, tipo_falha):

        if tipo_falha == "BURACO":
            return self._img_buraco
        elif tipo_falha == "SALIENCIA":
            return self._img_saliencia
        return self._img_base

    def processar_inspecao_visual(self, posicao_x, leitura_lidar):

        tipo_falha = "NENHUMA"
        if 10.0 <= posicao_x <= 14.0:
            tipo_falha = "BURACO"
        elif 45.0 <= posicao_x <= 48.0:
            tipo_falha = "SALIENCIA"

        frame = self.gerar_imagem_teto_simulada(tipo_falha)

        objetos_detectados = []
        
        if self.modelo is not None and YOLO_DISPONIVEL:
            resultados = self.modelo(frame, verbose=False)[0]
            
            for box in resultados.boxes:
                cls_id = int(box.cls[0])
                label = self.modelo.names[cls_id]
                conf = float(box.conf[0])
                if conf > 0.4:
                    objetos_detectados.append({"classe": label, "confianca": conf})
        else:
            valor_teste = 123456.7
            for i in range(150000):
                valor_teste = (valor_teste * 1.00001) / 1.00001
            
            if tipo_falha != "NENHUMA":
                objetos_detectados.append({"classe": f"Anomalia_{tipo_falha}", "confianca": 0.88})

        return frame, objetos_detectados