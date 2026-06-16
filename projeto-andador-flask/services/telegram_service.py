import os

import requests


# =========================================================
# CONFIGURAÇÃO DO TELEGRAM
# =========================================================

# Lê o token da variável de ambiente TELEGRAM_TOKEN.
# Não coloque a URL nem o token diretamente aqui.
TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN",
    ""
).strip()

TELEGRAM_API = (
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
)

print(
    "[TELEGRAM] Token configurado:",
    bool(TELEGRAM_TOKEN)
)


def token_configurado():
    return bool(
        TELEGRAM_TOKEN
    )


# =========================================================
# ENVIO DE MENSAGEM
# =========================================================

def enviar_mensagem(chat_id, mensagem):

    if not token_configurado():

        print(
            "[TELEGRAM] Token não configurado."
        )

        return False

    if not chat_id:

        print(
            "[TELEGRAM] Chat ID vazio."
        )

        return False

    try:

        resposta = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={
                "chat_id": str(chat_id),
                "text": mensagem
            },
            timeout=15
        )

        if resposta.status_code != 200:

            print(
                "[TELEGRAM] Falha:",
                resposta.status_code,
                resposta.text
            )

            return False

        print(
            "[TELEGRAM] Mensagem enviada."
        )

        return True

    except requests.RequestException as erro:

        print(
            "[TELEGRAM] Erro ao enviar mensagem:",
            erro
        )

        return False


# =========================================================
# ENVIO DE FOTO
# =========================================================

def enviar_foto(
    chat_id,
    caminho_foto,
    legenda=""
):

    if not token_configurado():

        print(
            "[TELEGRAM] Token não configurado."
        )

        return False

    if not chat_id:

        print(
            "[TELEGRAM] Chat ID vazio."
        )

        return False

    try:

        with open(
            caminho_foto,
            "rb"
        ) as foto:

            resposta = requests.post(
                f"{TELEGRAM_API}/sendPhoto",
                data={
                    "chat_id": str(chat_id),
                    "caption": legenda
                },
                files={
                    "photo": foto
                },
                timeout=30
            )

        if resposta.status_code != 200:

            print(
                "[TELEGRAM FOTO] Falha:",
                resposta.status_code,
                resposta.text
            )

            return False

        print(
            "[TELEGRAM] Foto enviada."
        )

        return True

    except (
        requests.RequestException,
        OSError
    ) as erro:

        print(
            "[TELEGRAM] Erro ao enviar foto:",
            erro
        )

        return False


# =========================================================
# REMOÇÃO DE WEBHOOK
# =========================================================

def remover_webhook():

    if not token_configurado():

        print(
            "[TELEGRAM] Não foi possível remover o webhook: "
            "token ausente."
        )

        return False

    try:

        resposta = requests.post(
            f"{TELEGRAM_API}/deleteWebhook",
            data={
                "drop_pending_updates": False
            },
            timeout=15
        )

        if resposta.status_code == 200:

            dados = resposta.json()

            if dados.get("ok"):

                print(
                    "[TELEGRAM] Modo polling configurado."
                )

                return True

        print(
            "[TELEGRAM] Erro ao remover webhook:",
            resposta.status_code,
            resposta.text
        )

    except requests.RequestException as erro:

        print(
            "[TELEGRAM] Erro ao configurar polling:",
            erro
        )

    return False


# =========================================================
# RECEBIMENTO DAS ATUALIZAÇÕES
# =========================================================

def buscar_atualizacoes(
    offset=None,
    timeout=30
):

    if not token_configurado():

        print(
            "[TELEGRAM] Não foi possível buscar atualizações: "
            "token ausente."
        )

        return []

    parametros = {
        "timeout": timeout,
        "allowed_updates": '["message"]'
    }

    if offset is not None:

        parametros[
            "offset"
        ] = offset

    try:

        resposta = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params=parametros,
            timeout=timeout + 10
        )

        if resposta.status_code != 200:

            print(
                "[TELEGRAM] Erro no getUpdates:",
                resposta.status_code,
                resposta.text
            )

            return []

        dados = resposta.json()

        if not dados.get("ok"):

            print(
                "[TELEGRAM] Resposta inválida no getUpdates:",
                dados
            )

            return []

        return dados.get(
            "result",
            []
        )

    except requests.RequestException as erro:

        print(
            "[TELEGRAM] Erro ao buscar atualizações:",
            erro
        )

        return []