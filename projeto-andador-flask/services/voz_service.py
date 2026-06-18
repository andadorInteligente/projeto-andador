import os
import shutil


def voz_disponivel():

    return shutil.which(
        "espeak"
    ) is not None


def falar(texto):

    if not voz_disponivel():

        print(
            "[VOZ] espeak não instalado."
        )

        return False

    texto_seguro = (
        texto
        .replace('"', "")
        .replace("'", "")
    )

    comando = f'espeak -v pt-br "{texto_seguro}"'

    retorno = os.system(
        comando
    )

    return retorno == 0


def falar_medicamento(idoso, medicamento):

    mensagem = (
        f"Atenção, {idoso.nome}. "
        f"Está na hora do remédio. "
        f"Tome {medicamento.nome}. "
        f"Dosagem: {medicamento.dosagem}."
    )

    print(
        "[VOZ] Falando:",
        mensagem
    )

    return falar(
        mensagem
    )
