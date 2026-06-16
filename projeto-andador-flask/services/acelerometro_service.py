import math
import time

try:
    from smbus2 import SMBus

    SMBUS_DISPONIVEL = True

except ImportError:
    SMBUS_DISPONIVEL = False


ENDERECO_MPU = 0x68

REG_POWER = 0x6B
REG_ACCEL_XOUT_H = 0x3B

LIMITE_QUEDA_G = 2.5


def inicializar_mpu(bus, endereco):

    bus.write_byte_data(
        endereco,
        REG_POWER,
        0
    )


def ler_word_2c(bus, endereco, registrador):

    high = bus.read_byte_data(
        endereco,
        registrador
    )

    low = bus.read_byte_data(
        endereco,
        registrador + 1
    )

    valor = (
        high << 8
    ) + low

    if valor >= 0x8000:
        valor = -(
            65536 - valor
        )

    return valor


def ler_aceleracao(bus, endereco):

    accel_x = ler_word_2c(
        bus,
        endereco,
        REG_ACCEL_XOUT_H
    )

    accel_y = ler_word_2c(
        bus,
        endereco,
        REG_ACCEL_XOUT_H + 2
    )

    accel_z = ler_word_2c(
        bus,
        endereco,
        REG_ACCEL_XOUT_H + 4
    )

    ax = accel_x / 16384.0
    ay = accel_y / 16384.0
    az = accel_z / 16384.0

    magnitude = math.sqrt(
        ax ** 2
        + ay ** 2
        + az ** 2
    )

    return {
        "ax": ax,
        "ay": ay,
        "az": az,
        "magnitude": magnitude
    }


def verificar_queda(dados):

    return dados[
        "magnitude"
    ] >= LIMITE_QUEDA_G


def monitorar_mpu6050(callback_queda):

    if not SMBUS_DISPONIVEL:

        print(
            "[MPU6050] smbus2 não instalado."
        )

        return

    try:

        with SMBus(1) as bus:

            inicializar_mpu(
                bus,
                ENDERECO_MPU
            )

            print(
                "[MPU6050] Monitoramento iniciado no endereço 0x68."
            )

            queda_em_andamento = False

            while True:

                dados = ler_aceleracao(
                    bus,
                    ENDERECO_MPU
                )

                queda = verificar_queda(
                    dados
                )

                if queda and not queda_em_andamento:

                    queda_em_andamento = True

                    print(
                        "[MPU6050] Possível queda detectada:",
                        f"{dados['magnitude']:.2f}g"
                    )

                    callback_queda(
                        dados
                    )

                    time.sleep(
                        10
                    )

                    queda_em_andamento = False

                time.sleep(
                    0.2
                )

    except Exception as erro:

        print(
            "[MPU6050] Erro no monitoramento:",
            erro
        )