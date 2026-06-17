import time

import serial
import pynmea2


PORTA_GPS = "/dev/ttyS0"

BAUDRATE_GPS = 9600

TIMEOUT_GPS = 20


def obter_localizacao():

    inicio = time.time()

    with serial.Serial(
        PORTA_GPS,
        BAUDRATE_GPS,
        timeout=1
    ) as gps:

        while time.time() - inicio < TIMEOUT_GPS:

            linha = gps.readline().decode(
                "ascii",
                errors="ignore"
            ).strip()

            if not linha.startswith(
                "$GPRMC"
            ) and not linha.startswith(
                "$GNRMC"
            ):

                continue

            try:

                mensagem = pynmea2.parse(
                    linha
                )

                if mensagem.status != "A":
                    continue

                latitude = float(
                    mensagem.latitude
                )

                longitude = float(
                    mensagem.longitude
                )

                return latitude, longitude

            except Exception:

                continue

    return None, None
