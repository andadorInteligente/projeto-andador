import cv2
import time
import requests
import random
from datetime import datetime
from pathlib import Path

try:
    from ultralytics import YOLO
    YOLO_DISPONIVEL = True
except ImportError:
    YOLO_DISPONIVEL = False


API_QUEDAS_URL = "http://127.0.0.1:5000/api/quedas"

API_IDOSO_MONITORADO_URL = "http://127.0.0.1:5000/api/monitoramento/idoso"

GPS_LAT = -8.0476
GPS_LON = -34.8770

PASTA_FOTOS_QUEDAS = Path("static/uploads/quedas")
PASTA_FOTOS_QUEDAS.mkdir(parents=True, exist_ok=True)

MODELO_YOLO = "yolo11n.pt"

OBSTACULOS = {
    "person",
    "chair",
    "bench",
    "bicycle",
    "motorcycle",
    "car",
    "truck",
    "dog",
    "cat",
    "backpack",
    "suitcase",
    "sports ball"
}

queda_em_andamento = False
tempo_inicio_queda = None
queda_ja_enviada = False


def buzzer(qtd=1):
    for _ in range(qtd):
        print("\a", end="", flush=True)
        time.sleep(0.2)


def display(mensagem):
    print(f"[DISPLAY] {mensagem}")


def ler_acelerometros_mock():
    acc1 = random.uniform(0.9, 1.1)
    acc2 = random.uniform(0.9, 1.1)
    acc3 = random.uniform(0.9, 1.1)

    return acc1, acc2, acc3


def detectar_impacto_mock():
    acc1, acc2, acc3 = ler_acelerometros_mock()
    media = (acc1 + acc2 + acc3) / 3

    return media > 2.5


def detectar_permanencia_no_chao():
    return True

def salvar_foto_queda(frame):
    nome_arquivo = datetime.now().strftime("queda_%Y%m%d_%H%M%S.jpg")
    caminho = PASTA_FOTOS_QUEDAS / nome_arquivo

    cv2.imwrite(str(caminho), frame)

    print(f"[FOTO] Foto da queda salva em: {caminho}")

    return caminho


def obter_idoso_monitorado():

    try:
        resposta = requests.get(
            API_IDOSO_MONITORADO_URL,
            timeout=5
        )

        if resposta.status_code != 200:
            print("[API] Nenhum idoso monitorado configurado.")
            print("[API] Resposta:", resposta.text)
            return None

        dados = resposta.json()

        print(
            f"[API] Idoso monitorado: {dados['idoso_nome']} "
            f"(ID {dados['idoso_id']})"
        )

        return dados["idoso_id"]

    except Exception as e:
        print(f"[API] Erro ao buscar idoso monitorado: {e}")
        return None


def enviar_queda_para_dashboard(foto_path):

    idoso_id = obter_idoso_monitorado()

    if not idoso_id:
        display("SEM IDOSO")
        print("[QUEDA] Configure um idoso na tela Monitoramento.")
        return False

    dados = {
        "idoso_id": str(idoso_id),
        "latitude": str(GPS_LAT),
        "longitude": str(GPS_LON),
        "observacao": "Queda confirmada pelo mock do andador com permanência no chão"
    }

    try:
        with open(foto_path, "rb") as foto:
            arquivos = {
                "foto": foto
            }

            resposta = requests.post(
                API_QUEDAS_URL,
                data=dados,
                files=arquivos,
                timeout=15
            )

        print("[API] Status:", resposta.status_code)
        print("[API] Resposta:", resposta.text)

        if resposta.status_code == 200:
            display("QUEDA ENVIADA")
            return True

        return False

    except Exception as e:
        print(f"[API] Erro ao enviar queda: {e}")
        return False

def carregar_yolo():
    if not YOLO_DISPONIVEL:
        print("[YOLO] Ultralytics não instalado.")
        print("[YOLO] Rode: pip install ultralytics")
        return None

    try:
        print(f"[YOLO] Carregando modelo {MODELO_YOLO}...")
        model = YOLO(MODELO_YOLO)
        print("[YOLO] Modelo carregado com sucesso.")
        return model

    except Exception as e:
        print(f"[YOLO] Erro ao carregar {MODELO_YOLO}: {e}")
        print("[YOLO] Tentando usar yolo11n.pt...")

        try:
            model = YOLO("yolo11n.pt")
            print("[YOLO] Modelo yolo11n.pt carregado.")
            return model

        except Exception as e2:
            print(f"[YOLO] Falha também no yolo11n.pt: {e2}")
            return None


def detectar_obstaculos(model, frame):
    if model is None:
        return frame, False

    resultados = model(
        frame,
        verbose=False
    )

    obstaculo_detectado = False

    for resultado in resultados:
        for box in resultado.boxes:

            classe_id = int(box.cls[0])
            nome_classe = model.names[classe_id]
            confianca = float(box.conf[0])

            if confianca < 0.50:
                continue

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            cor = (0, 255, 0)

            if nome_classe in OBSTACULOS:
                obstaculo_detectado = True
                cor = (0, 0, 255)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                cor,
                2
            )

            cv2.putText(
                frame,
                f"{nome_classe} {confianca:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                cor,
                2
            )

    return frame, obstaculo_detectado

def main():
    global queda_em_andamento
    global tempo_inicio_queda
    global queda_ja_enviada

    print("[SISTEMA] Mock do Andador Inteligente iniciado.")
    print("[SISTEMA] Pressione F para simular queda.")
    print("[SISTEMA] Pressione ESC para sair.")
    print(f"[SISTEMA] Enviando quedas para: {API_QUEDAS_URL}")
    print("[SISTEMA] Idoso monitorado será buscado pela API.")

    model = carregar_yolo()

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[CÂMERA] Câmera não encontrada.")
        return

    ultimo_alerta_obstaculo = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            print("[CÂMERA] Falha ao capturar frame.")
            continue

        frame, obstaculo = detectar_obstaculos(
            model,
            frame
        )

        if obstaculo:
            agora = time.time()

            if agora - ultimo_alerta_obstaculo > 3:
                print("[ALERTA] Obstáculo detectado pela câmera.")
                display("OBSTACULO")
                buzzer(1)
                ultimo_alerta_obstaculo = agora

            cv2.putText(
                frame,
                "OBSTACULO DETECTADO",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                3
            )

        if queda_em_andamento:
            segundos = int(time.time() - tempo_inicio_queda)

            cv2.putText(
                frame,
                f"Possivel queda: {segundos}s",
                (20, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),
                2
            )

            print(f"[QUEDA] Verificando permanência no chão... {segundos}s")

            if segundos >= 10 and not queda_ja_enviada:
                if detectar_permanencia_no_chao():
                    print("[QUEDA] Permanência no chão confirmada.")
                    display("QUEDA CONFIRMADA")
                    buzzer(5)

                    foto_path = salvar_foto_queda(frame)

                    enviado = enviar_queda_para_dashboard(
                        foto_path
                    )

                    if enviado:
                        print("[QUEDA] Evento enviado para dashboard e Telegram.")
                    else:
                        print("[QUEDA] Falha ao enviar evento.")

                    queda_ja_enviada = True

            if segundos >= 15:
                queda_em_andamento = False
                tempo_inicio_queda = None
                queda_ja_enviada = False
                print("[QUEDA] Monitoramento de queda encerrado.")

        cv2.imshow(
            "Mock Andador Inteligente - YOLO + Quedas",
            frame
        )

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("f"):
            if not queda_em_andamento:
                print("[TESTE] Queda simulada pela tecla F.")
                display("POSSIVEL QUEDA")
                buzzer(2)

                queda_em_andamento = True
                tempo_inicio_queda = time.time()
                queda_ja_enviada = False

        elif tecla == 27:
            print("[SISTEMA] Encerrando...")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()