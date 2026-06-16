from datetime import datetime, timedelta, timezone
from pathlib import Path

import os
import secrets
import threading
import time

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=True
)

print(
    "[APP] Arquivo .env:",
    BASE_DIR / ".env"
)

print(
    "[APP] TELEGRAM_TOKEN encontrada:",
    bool(os.getenv("TELEGRAM_TOKEN"))
)


from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from werkzeug.utils import secure_filename

from config import Config

from models import (
    db,
    Usuario,
    Idoso,
    Medicamento,
    Queda,
    MonitoramentoConfig,
    TelegramVinculo
)

from services.telegram_service import (
    enviar_mensagem,
    enviar_foto,
    remover_webhook,
    buscar_atualizacoes,
    token_configurado
)

from services.buzzer_service import (
    iniciar_buzzer,
    tocar_buzzer_por_10_segundos,
    ligar_buzzer_continuo,
    parar_buzzer
)

from services.voz_service import (
    falar_medicamento
)

from services.acelerometro_service import (
    monitorar_mpu6050
)

from services.gps_service import (
    obter_localizacao
)


app = Flask(__name__)

app.config.from_object(Config)

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"

UPLOAD_QUEDAS_FOLDER = (
    BASE_DIR
    / "static"
    / "uploads"
    / "quedas"
)

app.config["UPLOAD_FOLDER"] = str(
    UPLOAD_FOLDER
)

app.config["UPLOAD_QUEDAS_FOLDER"] = str(
    UPLOAD_QUEDAS_FOLDER
)

db.init_app(app)

UPLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

UPLOAD_QUEDAS_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

with app.app_context():
    db.create_all()


TELEGRAM_BOT_USERNAME = "andador_next_bot"

TEMPO_EXPIRACAO_VINCULO = 15


def agora_utc():

    return datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def obter_ou_criar_vinculo_telegram(usuario_id):

    agora = agora_utc()

    vinculo = TelegramVinculo.query.filter_by(
        usuario_id=usuario_id
    ).first()

    vinculo_valido = (
        vinculo is not None
        and not vinculo.usado
        and vinculo.expira_em > agora
    )

    if vinculo_valido:
        return vinculo

    novo_token = secrets.token_hex(
        16
    )

    expiracao = agora + timedelta(
        minutes=TEMPO_EXPIRACAO_VINCULO
    )

    if vinculo:

        vinculo.token = novo_token
        vinculo.expira_em = expiracao
        vinculo.usado = False
        vinculo.criado_em = agora

    else:

        vinculo = TelegramVinculo(
            usuario_id=usuario_id,
            token=novo_token,
            expira_em=expiracao,
            usado=False,
            criado_em=agora
        )

        db.session.add(
            vinculo
        )

    db.session.commit()

    return vinculo


def processar_inicio_telegram(atualizacao):

    mensagem = atualizacao.get(
        "message"
    )

    if not mensagem:
        return

    texto = mensagem.get(
        "text",
        ""
    ).strip()

    chat = mensagem.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    nome_telegram = (
        mensagem
        .get("from", {})
        .get("first_name", "")
    )

    if not chat_id:
        return

    if not texto.startswith(
        "/start"
    ):
        return

    partes = texto.split(
        maxsplit=1
    )

    if len(partes) != 2:

        enviar_mensagem(
            chat_id,
            (
                "Para conectar sua conta, entre na "
                "dashboard do Andador Inteligente e "
                "clique em “Conectar Telegram”."
            )
        )

        return

    token = partes[1].strip()

    vinculo = TelegramVinculo.query.filter_by(
        token=token,
        usado=False
    ).first()

    if not vinculo:

        enviar_mensagem(
            chat_id,
            (
                "❌ Este link é inválido ou já foi utilizado.\n\n"
                "Volte à dashboard e gere um novo link."
            )
        )

        return

    if vinculo.expira_em <= agora_utc():

        vinculo.usado = True

        db.session.commit()

        enviar_mensagem(
            chat_id,
            (
                "⌛ Este link expirou.\n\n"
                "Volte à dashboard e gere um novo link."
            )
        )

        return

    usuario = db.session.get(
        Usuario,
        vinculo.usuario_id
    )

    if not usuario:

        vinculo.usado = True

        db.session.commit()

        enviar_mensagem(
            chat_id,
            "❌ Cuidador não encontrado."
        )

        return

    chat_id_texto = str(
        chat_id
    )

    outros_usuarios = Usuario.query.filter(
        Usuario.telegram_chat_id == chat_id_texto,
        Usuario.id != usuario.id
    ).all()

    for outro_usuario in outros_usuarios:
        outro_usuario.telegram_chat_id = None

    usuario.telegram_chat_id = chat_id_texto

    vinculo.usado = True

    db.session.commit()

    mensagem_sucesso = f"""
✅ TELEGRAM CONECTADO!

Olá, {usuario.nome or nome_telegram}!

Sua conta foi vinculada com sucesso ao Andador Inteligente.

A partir de agora você receberá:

🚨 Alertas de queda
📍 Localização do idoso
💊 Horários de medicamentos
"""

    enviar_mensagem(
        chat_id,
        mensagem_sucesso
    )

    print(
        "[TELEGRAM] Cuidador vinculado:",
        usuario.nome,
        chat_id
    )


def monitorar_conexoes_telegram():

    if not token_configurado():

        print(
            "[TELEGRAM] Monitor não iniciado: "
            "token não configurado."
        )

        return

    with app.app_context():

        remover_webhook()

        offset = None

        print(
            "[TELEGRAM] Monitor de vinculação iniciado."
        )

        while True:

            try:

                atualizacoes = buscar_atualizacoes(
                    offset=offset,
                    timeout=30
                )

                for atualizacao in atualizacoes:

                    update_id = atualizacao.get(
                        "update_id"
                    )

                    if update_id is not None:
                        offset = update_id + 1

                    try:

                        processar_inicio_telegram(
                            atualizacao
                        )

                    except Exception as erro:

                        db.session.rollback()

                        print(
                            "[TELEGRAM] Erro ao processar atualização:",
                            erro
                        )

                db.session.remove()

            except Exception as erro:

                db.session.rollback()

                print(
                    "[TELEGRAM] Erro no monitor de vinculação:",
                    erro
                )

                time.sleep(
                    5
                )

            time.sleep(
                1
            )


def processar_queda_mpu6050(dados):

    with app.app_context():

        ligar_buzzer_continuo()

        try:

            config = (
                MonitoramentoConfig.query
                .filter(
                    MonitoramentoConfig.idoso_id.isnot(
                        None
                    )
                )
                .first()
            )

            if not config or not config.idoso_id:

                print(
                    "[QUEDA] Nenhum idoso configurado para monitoramento."
                )

                return

            idoso = db.session.get(
                Idoso,
                config.idoso_id
            )

            if not idoso:

                print(
                    "[QUEDA] Idoso não encontrado."
                )

                return

            usuario = db.session.get(
                Usuario,
                idoso.usuario_id
            )

            latitude = None
            longitude = None

            try:

                latitude, longitude = obter_localizacao()

            except Exception as erro:

                print(
                    "[GPS] Erro ao obter localização:",
                    erro
                )

            if latitude is None or longitude is None:

                print(
                    "[GPS] Localização indisponível."
                )

                latitude = -8.0476
                longitude = -34.8770

            queda = Queda(
                idoso_id=idoso.id,
                foto=None,
                latitude=latitude,
                longitude=longitude,
                observacao=(
                    "Queda detectada pelo acelerômetro MPU6050. "
                    f"Aceleração={dados['magnitude']:.2f}g"
                )
            )

            db.session.add(
                queda
            )

            db.session.commit()

            link_maps = (
                "https://maps.google.com/?q="
                f"{latitude},"
                f"{longitude}"
            )

            mensagem = f"""
🚨 QUEDA DETECTADA!

👵 Idoso: {idoso.nome}
⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

📊 Acelerômetro: {dados['magnitude']:.2f}g

📍 Localização:
{link_maps}

⚠️ Verifique imediatamente.
"""

            if usuario and usuario.telegram_chat_id:

                enviar_mensagem(
                    usuario.telegram_chat_id,
                    mensagem
                )

                print(
                    "[QUEDA] Alerta enviado para o cuidador:",
                    usuario.nome
                )

            else:

                print(
                    "[QUEDA] Cuidador sem Telegram configurado."
                )

        except Exception as erro:

            db.session.rollback()

            print(
                "[QUEDA] Erro ao processar queda:",
                erro
            )

        finally:

            parar_buzzer()

            db.session.remove()


@app.route("/")
def home():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    usuario_id = session[
        "usuario_id"
    ]

    usuario = db.session.get(
        Usuario,
        usuario_id
    )

    if not usuario:

        session.clear()

        return redirect(
            "/login"
        )

    idosos_do_cuidador = Idoso.query.filter_by(
        usuario_id=usuario_id
    ).all()

    ids_idosos = [
        idoso.id
        for idoso in idosos_do_cuidador
    ]

    total_idosos = len(
        idosos_do_cuidador
    )

    total_medicamentos = (
        Medicamento.query
        .filter(
            Medicamento.idoso_id.in_(
                ids_idosos
            )
        )
        .count()
        if ids_idosos
        else 0
    )

    total_quedas = (
        Queda.query
        .filter(
            Queda.idoso_id.in_(
                ids_idosos
            )
        )
        .count()
        if ids_idosos
        else 0
    )

    ultimas_quedas = (
        Queda.query
        .filter(
            Queda.idoso_id.in_(
                ids_idosos
            )
        )
        .order_by(
            Queda.data_hora.desc()
        )
        .limit(
            5
        )
        .all()
        if ids_idosos
        else []
    )

    return render_template(
        "dashboard.html",
        usuario=usuario,
        total_idosos=total_idosos,
        total_medicamentos=total_medicamentos,
        total_quedas=total_quedas,
        ultimas_quedas=ultimas_quedas
    )


@app.route(
    "/cadastro",
    methods=[
        "GET",
        "POST"
    ]
)
def cadastro():

    if request.method == "POST":

        nome = request.form[
            "nome"
        ].strip()

        email = request.form[
            "email"
        ].strip().lower()

        senha = request.form[
            "senha"
        ]

        existente = Usuario.query.filter_by(
            email=email
        ).first()

        if existente:

            flash(
                "Email já cadastrado."
            )

            return redirect(
                "/cadastro"
            )

        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=generate_password_hash(
                senha
            )
        )

        db.session.add(
            usuario
        )

        db.session.commit()

        flash(
            "Conta criada com sucesso."
        )

        return redirect(
            "/login"
        )

    return render_template(
        "cadastro.html"
    )


@app.route(
    "/login",
    methods=[
        "GET",
        "POST"
    ]
)
def login():

    if request.method == "POST":

        email = request.form[
            "email"
        ].strip().lower()

        senha = request.form[
            "senha"
        ]

        usuario = Usuario.query.filter_by(
            email=email
        ).first()

        if (
            usuario
            and check_password_hash(
                usuario.senha_hash,
                senha
            )
        ):

            session[
                "usuario_id"
            ] = usuario.id

            return redirect(
                "/"
            )

        flash(
            "Credenciais inválidas."
        )

    return render_template(
        "login.html"
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/login"
    )


@app.route("/idosos")
def idosos():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    lista = Idoso.query.filter_by(
        usuario_id=session[
            "usuario_id"
        ]
    ).all()

    return render_template(
        "idosos.html",
        idosos=lista
    )


@app.route(
    "/idosos/novo",
    methods=[
        "GET",
        "POST"
    ]
)
def novo_idoso():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    if request.method == "POST":

        foto_nome = None

        arquivo = request.files.get(
            "foto"
        )

        if arquivo and arquivo.filename:

            foto_nome = secure_filename(
                arquivo.filename
            )

            arquivo.save(
                str(
                    UPLOAD_FOLDER
                    / foto_nome
                )
            )

        idoso = Idoso(
            usuario_id=session[
                "usuario_id"
            ],
            nome=request.form[
                "nome"
            ],
            telefone=request.form[
                "telefone"
            ],
            endereco=request.form[
                "endereco"
            ],
            observacoes=request.form[
                "observacoes"
            ],
            foto=foto_nome
        )

        db.session.add(
            idoso
        )

        db.session.commit()

        flash(
            "Idoso cadastrado."
        )

        return redirect(
            "/idosos"
        )

    return render_template(
        "novo_idoso.html"
    )


@app.route(
    "/idosos/editar/<int:idoso_id>",
    methods=[
        "GET",
        "POST"
    ]
)
def editar_idoso(idoso_id):

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    idoso = Idoso.query.filter_by(
        id=idoso_id,
        usuario_id=session[
            "usuario_id"
        ]
    ).first_or_404()

    if request.method == "POST":

        idoso.nome = request.form[
            "nome"
        ]

        idoso.telefone = request.form[
            "telefone"
        ]

        idoso.endereco = request.form[
            "endereco"
        ]

        idoso.observacoes = request.form[
            "observacoes"
        ]

        arquivo = request.files.get(
            "foto"
        )

        if arquivo and arquivo.filename:

            foto_nome = secure_filename(
                arquivo.filename
            )

            arquivo.save(
                str(
                    UPLOAD_FOLDER
                    / foto_nome
                )
            )

            idoso.foto = foto_nome

        db.session.commit()

        flash(
            "Idoso atualizado."
        )

        return redirect(
            "/idosos"
        )

    return render_template(
        "editar_idoso.html",
        idoso=idoso
    )


@app.route(
    "/idosos/excluir/<int:idoso_id>"
)
def excluir_idoso(idoso_id):

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    idoso = Idoso.query.filter_by(
        id=idoso_id,
        usuario_id=session[
            "usuario_id"
        ]
    ).first_or_404()

    configuracoes_monitoramento = (
        MonitoramentoConfig.query
        .filter_by(
            idoso_id=idoso.id
        )
        .all()
    )

    for configuracao in configuracoes_monitoramento:
        configuracao.idoso_id = None

    medicamentos = Medicamento.query.filter_by(
        idoso_id=idoso.id
    ).all()

    quedas = Queda.query.filter_by(
        idoso_id=idoso.id
    ).all()

    for medicamento in medicamentos:

        db.session.delete(
            medicamento
        )

    for queda in quedas:

        db.session.delete(
            queda
        )

    db.session.delete(
        idoso
    )

    db.session.commit()

    flash(
        "Idoso removido."
    )

    return redirect(
        "/idosos"
    )


@app.route(
    "/idosos/<int:idoso_id>"
)
def visualizar_idoso(idoso_id):

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    idoso = Idoso.query.filter_by(
        id=idoso_id,
        usuario_id=session[
            "usuario_id"
        ]
    ).first_or_404()

    medicamentos = Medicamento.query.filter_by(
        idoso_id=idoso.id
    ).all()

    quedas = (
        Queda.query
        .filter_by(
            idoso_id=idoso.id
        )
        .order_by(
            Queda.data_hora.desc()
        )
        .all()
    )

    return render_template(
        "idoso_detalhes.html",
        idoso=idoso,
        medicamentos=medicamentos,
        quedas=quedas
    )


@app.route(
    "/idosos/<int:idoso_id>/medicamentos/novo",
    methods=[
        "GET",
        "POST"
    ]
)
def novo_medicamento(idoso_id):

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    idoso = Idoso.query.filter_by(
        id=idoso_id,
        usuario_id=session[
            "usuario_id"
        ]
    ).first_or_404()

    if request.method == "POST":

        medicamento = Medicamento(
            idoso_id=idoso.id,
            nome=request.form[
                "nome"
            ],
            dosagem=request.form[
                "dosagem"
            ],
            horario=request.form[
                "horario"
            ]
        )

        db.session.add(
            medicamento
        )

        db.session.commit()

        flash(
            "Medicamento cadastrado."
        )

        return redirect(
            f"/idosos/{idoso.id}"
        )

    return render_template(
        "novo_medicamento.html",
        idoso=idoso
    )


@app.route(
    "/idosos/<int:idoso_id>/simular-queda"
)
def simular_queda(idoso_id):

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    idoso = Idoso.query.filter_by(
        id=idoso_id,
        usuario_id=session[
            "usuario_id"
        ]
    ).first_or_404()

    dados = {
        "ax": 0,
        "ay": 0,
        "az": 3.2,
        "magnitude": 3.2
    }

    processar_queda_mpu6050(
        dados
    )

    flash(
        "Queda simulada pelo sistema."
    )

    return redirect(
        f"/idosos/{idoso.id}"
    )


@app.route(
    "/quedas/<int:queda_id>"
)
def detalhes_queda(queda_id):

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    queda = db.session.get(
        Queda,
        queda_id
    )

    if not queda:

        return (
            "Queda não encontrada.",
            404
        )

    idoso = Idoso.query.filter_by(
        id=queda.idoso_id,
        usuario_id=session[
            "usuario_id"
        ]
    ).first_or_404()

    return render_template(
        "queda_detalhes.html",
        queda=queda,
        idoso=idoso
    )


@app.route(
    "/api/quedas",
    methods=[
        "POST"
    ]
)
def api_registrar_queda():

    idoso_id = request.form.get(
        "idoso_id"
    )

    latitude = request.form.get(
        "latitude"
    )

    longitude = request.form.get(
        "longitude"
    )

    observacao = request.form.get(
        "observacao",
        "Queda detectada pelo sistema"
    )

    if (
        not idoso_id
        or not latitude
        or not longitude
    ):

        return {
            "status": "erro",
            "mensagem": (
                "idoso_id, latitude e longitude "
                "são obrigatórios."
            )
        }, 400

    try:

        idoso_id = int(
            idoso_id
        )

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

    except ValueError:

        return {
            "status": "erro",
            "mensagem": (
                "ID, latitude ou longitude inválidos."
            )
        }, 400

    idoso = db.session.get(
        Idoso,
        idoso_id
    )

    if not idoso:

        return {
            "status": "erro",
            "mensagem": "Idoso não encontrado."
        }, 404

    foto_nome = None

    arquivo = request.files.get(
        "foto"
    )

    if arquivo and arquivo.filename:

        foto_nome = datetime.now().strftime(
            "queda_%Y%m%d_%H%M%S.jpg"
        )

        caminho = (
            UPLOAD_QUEDAS_FOLDER
            / foto_nome
        )

        arquivo.save(
            str(
                caminho
            )
        )

    queda = Queda(
        idoso_id=idoso.id,
        foto=foto_nome,
        latitude=latitude,
        longitude=longitude,
        observacao=observacao
    )

    db.session.add(
        queda
    )

    db.session.commit()

    usuario = db.session.get(
        Usuario,
        idoso.usuario_id
    )

    link_maps = (
        "https://maps.google.com/?q="
        f"{latitude},"
        f"{longitude}"
    )

    mensagem = f"""
🚨 QUEDA DETECTADA!

👵 Idoso: {idoso.nome}
⏰ Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

📍 Localização:
{link_maps}

⚠️ Verifique imediatamente.
"""

    if usuario and usuario.telegram_chat_id:

        enviar_mensagem(
            usuario.telegram_chat_id,
            mensagem
        )

        if foto_nome:

            enviar_foto(
                usuario.telegram_chat_id,
                str(
                    UPLOAD_QUEDAS_FOLDER
                    / foto_nome
                ),
                "📸 Foto registrada no momento da queda."
            )

    return {
        "status": "ok",
        "mensagem": "Queda registrada com sucesso.",
        "queda_id": queda.id
    }


@app.route(
    "/configuracoes",
    methods=[
        "GET",
        "POST"
    ]
)
def configuracoes():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    usuario = db.session.get(
        Usuario,
        session[
            "usuario_id"
        ]
    )

    if not usuario:

        session.clear()

        return redirect(
            "/login"
        )

    if request.method == "POST":

        usuario.nome = request.form.get(
            "nome",
            usuario.nome
        ).strip()

        usuario.telefone = request.form.get(
            "telefone",
            ""
        ).strip()

        db.session.commit()

        flash(
            "Configurações atualizadas com sucesso."
        )

        return redirect(
            "/configuracoes"
        )

    telegram_link = None
    vinculo = None

    if not usuario.telegram_chat_id:

        vinculo = obter_ou_criar_vinculo_telegram(
            usuario.id
        )

        telegram_link = (
            f"https://t.me/"
            f"{TELEGRAM_BOT_USERNAME}"
            f"?start={vinculo.token}"
        )

    return render_template(
        "configuracoes.html",
        usuario=usuario,
        telegram_link=telegram_link,
        vinculo=vinculo
    )


@app.route(
    "/telegram/desconectar",
    methods=[
        "POST"
    ]
)
def desconectar_telegram():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    usuario = db.session.get(
        Usuario,
        session[
            "usuario_id"
        ]
    )

    if not usuario:

        session.clear()

        return redirect(
            "/login"
        )

    usuario.telegram_chat_id = None

    vinculo = TelegramVinculo.query.filter_by(
        usuario_id=usuario.id
    ).first()

    if vinculo:
        vinculo.usado = True

    db.session.commit()

    flash(
        "Telegram desconectado com sucesso."
    )

    return redirect(
        "/configuracoes"
    )


@app.route(
    "/teste-telegram"
)
def teste_telegram():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    usuario = db.session.get(
        Usuario,
        session[
            "usuario_id"
        ]
    )

    if not usuario:

        session.clear()

        return redirect(
            "/login"
        )

    if not usuario.telegram_chat_id:

        flash(
            "Conecte sua conta do Telegram primeiro."
        )

        return redirect(
            "/configuracoes"
        )

    mensagem = f"""
✅ TESTE DO TELEGRAM

Olá, {usuario.nome}!

Se você recebeu esta mensagem, o Telegram está configurado corretamente.
"""

    enviado = enviar_mensagem(
        usuario.telegram_chat_id,
        mensagem
    )

    if enviado:

        flash(
            "Mensagem de teste enviada."
        )

    else:

        flash(
            "Não foi possível enviar a mensagem de teste."
        )

    return redirect(
        "/configuracoes"
    )


@app.route(
    "/monitoramento",
    methods=[
        "GET",
        "POST"
    ]
)
def monitoramento():

    if "usuario_id" not in session:
        return redirect(
            "/login"
        )

    usuario_id = session[
        "usuario_id"
    ]

    idosos_do_usuario = Idoso.query.filter_by(
        usuario_id=usuario_id
    ).all()

    config = MonitoramentoConfig.query.filter_by(
        usuario_id=usuario_id
    ).first()

    if not config:

        config = MonitoramentoConfig(
            usuario_id=usuario_id,
            idoso_id=None
        )

        db.session.add(
            config
        )

        db.session.commit()

    if request.method == "POST":

        idoso_id = request.form.get(
            "idoso_id"
        )

        todas_configs = MonitoramentoConfig.query.all()

        for outra_config in todas_configs:
            outra_config.idoso_id = None

        if idoso_id:

            try:

                idoso_id = int(
                    idoso_id
                )

            except ValueError:

                flash(
                    "Idoso inválido."
                )

                return redirect(
                    "/monitoramento"
                )

            idoso = Idoso.query.filter_by(
                id=idoso_id,
                usuario_id=usuario_id
            ).first_or_404()

            config.idoso_id = idoso.id

        else:

            config.idoso_id = None

        db.session.commit()

        flash(
            "Idoso monitorado atualizado com sucesso."
        )

        return redirect(
            "/monitoramento"
        )

    idoso_monitorado = None

    if config.idoso_id:

        idoso_monitorado = Idoso.query.filter_by(
            id=config.idoso_id,
            usuario_id=usuario_id
        ).first()

    return render_template(
        "monitoramento.html",
        idosos=idosos_do_usuario,
        config=config,
        idoso_monitorado=idoso_monitorado
    )


@app.route(
    "/api/monitoramento/idoso"
)
def api_idoso_monitorado():

    config = (
        MonitoramentoConfig.query
        .filter(
            MonitoramentoConfig.idoso_id.isnot(
                None
            )
        )
        .first()
    )

    if not config or not config.idoso_id:

        return {
            "status": "erro",
            "mensagem": (
                "Nenhum idoso configurado "
                "para monitoramento."
            )
        }, 404

    idoso = db.session.get(
        Idoso,
        config.idoso_id
    )

    if not idoso:

        return {
            "status": "erro",
            "mensagem": "Idoso não encontrado."
        }, 404

    usuario = db.session.get(
        Usuario,
        idoso.usuario_id
    )

    if not usuario:

        return {
            "status": "erro",
            "mensagem": "Cuidador não encontrado."
        }, 404

    return {
        "status": "ok",
        "idoso_id": idoso.id,
        "idoso_nome": idoso.nome,
        "cuidador_id": usuario.id,
        "cuidador_nome": usuario.nome
    }


remedios_avisados = set()


def monitorar_medicamentos():

    with app.app_context():

        while True:

            agora = datetime.now().strftime(
                "%H:%M"
            )

            hoje = datetime.now().strftime(
                "%Y-%m-%d"
            )

            medicamentos = Medicamento.query.all()

            for medicamento in medicamentos:

                if medicamento.horario != agora:
                    continue

                chave = (
                    f"{hoje}_"
                    f"{medicamento.id}_"
                    f"{agora}"
                )

                if chave in remedios_avisados:
                    continue

                idoso = db.session.get(
                    Idoso,
                    medicamento.idoso_id
                )

                if not idoso:

                    remedios_avisados.add(
                        chave
                    )

                    continue

                usuario = db.session.get(
                    Usuario,
                    idoso.usuario_id
                )

                mensagem = f"""
💊 HORÁRIO DE MEDICAÇÃO

👵 Idoso: {idoso.nome}

💊 Medicamento: {medicamento.nome}
📋 Dosagem: {medicamento.dosagem}
⏰ Horário: {medicamento.horario}

Por favor, verifique a administração do medicamento.
"""

                tocar_buzzer_por_10_segundos()

                falar_medicamento(
                    idoso,
                    medicamento
                )

                enviado = False

                if usuario and usuario.telegram_chat_id:

                    enviado = enviar_mensagem(
                        usuario.telegram_chat_id,
                        mensagem
                    )

                else:

                    print(
                        "[REMÉDIO] Cuidador sem Telegram:",
                        usuario.nome if usuario else "Não encontrado"
                    )

                remedios_avisados.add(
                    chave
                )

                if enviado:

                    print(
                        "[REMÉDIO] Buzzer tocou, voz falou e alerta enviado:",
                        medicamento.nome,
                        "-",
                        idoso.nome
                    )

                else:

                    print(
                        "[REMÉDIO] Buzzer tocou e voz falou, mas Telegram não foi enviado:",
                        medicamento.nome,
                        "-",
                        idoso.nome
                    )

            db.session.remove()

            time.sleep(
                30
            )


if __name__ == "__main__":

    iniciar_buzzer()

    thread_medicamentos = threading.Thread(
        target=monitorar_medicamentos,
        daemon=True,
        name="monitor-medicamentos"
    )

    thread_medicamentos.start()

    thread_acelerometro = threading.Thread(
        target=monitorar_mpu6050,
        args=(
            processar_queda_mpu6050,
        ),
        daemon=True,
        name="monitor-acelerometro"
    )

    thread_acelerometro.start()

    if token_configurado():

        thread_telegram = threading.Thread(
            target=monitorar_conexoes_telegram,
            daemon=True,
            name="monitor-telegram"
        )

        thread_telegram.start()

    else:

        print(
            "[TELEGRAM] Thread não iniciada: "
            "configure TELEGRAM_TOKEN no arquivo .env."
        )

    app.run(
        host="0.0.0.0",
        port=5010,
        debug=True,
        use_reloader=False
    )