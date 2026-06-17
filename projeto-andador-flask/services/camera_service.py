from datetime import datetime
from pathlib import Path
import subprocess
import time
import shutil

try:
    import cv2
    OPENCV_DISPONIVEL = True
except ImportError:
    OPENCV_DISPONIVEL = False

try:
    from ultralytics import YOLO
    YOLO_DISPONIVEL = True
except ImportError:
    YOLO_DISPONIVEL = False


BASE_DIR = Path(__file__).resolve().parent.parent

PASTA_FOTOS_QUEDAS = BASE_DIR / "static" / "uploads" / "quedas"
PASTA_FOTOS_QUEDAS.mkdir(parents=True, exist_ok=True)

MODELO_YOLO = "yolo11n.pt"

TEMPO_ENTRE_ALERTAS_OBSTACULO = 3

OBSTACULOS_PORTUGUES = {
    "person": "Pessoa",
    "chair": "Cadeira",
    "bench": "Banco",
    "bicycle": "Bicicleta",
    "motorcycle": "Moto",
    "car": "Carro",
    "truck": "Caminhão",
    "bus": "Ônibus",
    "dog": "Cachorro",
    "cat": "Gato",
    "backpack": "Mochila",
    "suitcase": "Mala",
    "sports ball": "Bola",
    "bottle": "Garrafa",
    "cup": "Copo",
    "handbag": "Bolsa",
    "umbrella": "Guarda-chuva"
}


def comando_camera_disponivel():

    if shutil.which("rpicam-still"):
        return "rpicam-still"

    if shutil.which("libcamera-still"):
        return "libcamera-still"

    return None


def capturar_imagem_rpicam(caminho, timeout="1000"):

    comando_camera = comando_camera_disponivel()

    if not comando_camera:
        print("[CÂMERA] rpicam-still/libcamera-still não encontrado.")
        return False

    try:
        subprocess.run(
            [
                comando_camera,
                "-o",
                str(caminho),
                "--timeout",
                timeout,
                "--nopreview"
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return caminho.exists()

    except Exception as erro:
        print("[CÂMERA] Erro ao capturar imagem:", erro)
        return False


def capturar_foto_queda():

    nome_arquivo = datetime.now().strftime("queda_%Y%m%d_%H%M%S.jpg")
    caminho = PASTA_FOTOS_QUEDAS / nome_arquivo

    sucesso = capturar_imagem_rpicam(caminho, timeout="1000")

    if not sucesso:
        print("[CÂMERA] Falha ao capturar foto da queda.")
        return None, None

    print("[CÂMERA] Foto da queda salva em:", caminho)

    return nome_arquivo, str(caminho)


def carregar_modelo_yolo():

    if not YOLO_DISPONIVEL:
        print("[YOLO] Ultralytics não instalado.")
        return None

    try:
        print("[YOLO] Carregando modelo:", MODELO_YOLO)

        modelo = YOLO(MODELO_YOLO)

        print("[YOLO] Modelo carregado com sucesso.")

        return modelo

    except Exception as erro:
        print("[YOLO] Erro ao carregar modelo:", erro)
        return None


def detectar_obstaculos_no_frame(modelo, frame):

    if modelo is None:
        return []

    resultados = modelo(frame, verbose=False)

    obstaculos_detectados = []

    for resultado in resultados:

        for box in resultado.boxes:

            classe_id = int(box.cls[0])
            nome_ingles = modelo.names[classe_id]
            confianca = float(box.conf[0])

            if confianca < 0.50:
                continue

            if nome_ingles not in OBSTACULOS_PORTUGUES:
                continue

            nome_portugues = OBSTACULOS_PORTUGUES[nome_ingles]

            obstaculos_detectados.append(nome_portugues)

    return obstaculos_detectados


def capturar_frame():

    if not OPENCV_DISPONIVEL:
        print("[CÂMERA] OpenCV não instalado.")
        return None

    caminho_temp = PASTA_FOTOS_QUEDAS / "camera_temp.jpg"

    sucesso = capturar_imagem_rpicam(caminho_temp, timeout="500")

    if not sucesso:
        return None

    frame = cv2.imread(str(caminho_temp))

    return frame


def monitorar_obstaculos(callback_obstaculo=None):

    if not OPENCV_DISPONIVEL:
        print("[CÂMERA] OpenCV não instalado.")
        return

    modelo = carregar_modelo_yolo()

    if modelo is None:
        print("[CÂMERA] Monitoramento de obstáculos não iniciado.")
        return

    print("[CÂMERA] Monitoramento de obstáculos iniciado.")

    ultimo_alerta = 0

    while True:

        frame = capturar_frame()

        if frame is None:
            print("[CÂMERA] Falha ao capturar frame.")
            time.sleep(2)
            continue

        obstaculos = detectar_obstaculos_no_frame(modelo, frame)

        if obstaculos:

            agora = time.time()

            if agora - ultimo_alerta >= TEMPO_ENTRE_ALERTAS_OBSTACULO:

                obstaculos_unicos = list(dict.fromkeys(obstaculos))

                texto_obstaculos = ", ".join(obstaculos_unicos)

                print("[CÂMERA] Obstáculo detectado:", texto_obstaculos)

                if callback_obstaculo:
                    callback_obstaculo(texto_obstaculos)

                ultimo_alerta = agora

        time.sleep(1)
