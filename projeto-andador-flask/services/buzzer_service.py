import time

try:
    import RPi.GPIO as GPIO

    GPIO_DISPONIVEL = True

except ImportError:
    GPIO_DISPONIVEL = False


PINO_BUZZER = 18

FREQUENCIA_BUZZER = 4000
DUTY_CYCLE = 50

QUANTIDADE_BIPS = 3
TEMPO_DO_BIP = 0.3
TEMPO_TOTAL_ALERTA = 10

pwm_buzzer = None
buzzer_iniciado = False


def iniciar_buzzer():

    global pwm_buzzer
    global buzzer_iniciado

    if not GPIO_DISPONIVEL:

        print(
            "[BUZZER] RPi.GPIO não instalado. "
            "Usando beep do terminal."
        )

        return False

    try:

        GPIO.setwarnings(
            False
        )

        GPIO.setmode(
            GPIO.BCM
        )

        GPIO.setup(
            PINO_BUZZER,
            GPIO.OUT
        )

        GPIO.output(
            PINO_BUZZER,
            GPIO.LOW
        )

        pwm_buzzer = GPIO.PWM(
            PINO_BUZZER,
            FREQUENCIA_BUZZER
        )

        buzzer_iniciado = True

        print(
            f"[BUZZER] Inicializado no GPIO {PINO_BUZZER} "
            f"com {FREQUENCIA_BUZZER}Hz."
        )

        return True

    except Exception as erro:

        print(
            "[BUZZER] Erro ao iniciar:",
            erro
        )

        pwm_buzzer = None
        buzzer_iniciado = False

        return False


def ligar_buzzer():

    if pwm_buzzer:

        try:

            pwm_buzzer.start(
                DUTY_CYCLE
            )

        except Exception:

            try:

                pwm_buzzer.ChangeDutyCycle(
                    DUTY_CYCLE
                )

            except Exception:

                pass

    else:

        print(
            "\a",
            end="",
            flush=True
        )


def desligar_som_buzzer():

    if pwm_buzzer:

        try:

            pwm_buzzer.stop()

        except Exception:

            pass


def tocar_buzzer_por_10_segundos():

    print(
        "[BUZZER] Alerta de medicamento iniciado por 10 segundos."
    )

    if not buzzer_iniciado:
        iniciar_buzzer()

    tempo_total_bips = QUANTIDADE_BIPS * TEMPO_DO_BIP

    tempo_espera_total = TEMPO_TOTAL_ALERTA - tempo_total_bips

    intervalo_entre_bips = tempo_espera_total / (
        QUANTIDADE_BIPS - 1
    )

    inicio = time.time()

    for indice in range(
        QUANTIDADE_BIPS
    ):

        ligar_buzzer()

        time.sleep(
            TEMPO_DO_BIP
        )

        desligar_som_buzzer()

        if indice < QUANTIDADE_BIPS - 1:

            time.sleep(
                intervalo_entre_bips
            )

    tempo_passado = time.time() - inicio

    if tempo_passado < TEMPO_TOTAL_ALERTA:

        time.sleep(
            TEMPO_TOTAL_ALERTA - tempo_passado
        )

    print(
        "[BUZZER] Alerta de medicamento finalizado."
    )


def ligar_buzzer_continuo():

    print(
        "[BUZZER] Alerta contínuo iniciado."
    )

    if not buzzer_iniciado:
        iniciar_buzzer()

    ligar_buzzer()


def parar_buzzer():

    desligar_som_buzzer()

    print(
        "[BUZZER] Alerta contínuo parado."
    )


def desligar_buzzer():

    global pwm_buzzer
    global buzzer_iniciado

    if pwm_buzzer:

        try:

            pwm_buzzer.stop()

        except Exception:

            pass

        pwm_buzzer = None

    if GPIO_DISPONIVEL:

        try:

            GPIO.output(
                PINO_BUZZER,
                GPIO.LOW
            )

            GPIO.cleanup(
                PINO_BUZZER
            )

        except Exception:

            pass

    buzzer_iniciado = False

    print(
        "[BUZZER] Desligado."
    )
