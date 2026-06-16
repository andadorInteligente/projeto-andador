from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Usuario(db.Model):

    __tablename__ = "usuarios"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    senha_hash = db.Column(
        db.String(255),
        nullable=False
    )

    telefone = db.Column(
        db.String(30)
    )

    telegram_chat_id = db.Column(
        db.String(50)
    )

    foto_perfil = db.Column(
        db.String(255)
    )

    data_criacao = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Idoso(db.Model):

    __tablename__ = "idosos"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    data_nascimento = db.Column(
        db.Date
    )

    telefone = db.Column(
        db.String(20)
    )

    endereco = db.Column(
        db.String(255)
    )

    foto = db.Column(
        db.String(255)
    )

    observacoes = db.Column(
        db.Text
    )

    ativo = db.Column(
        db.Boolean,
        default=True
    )


class Medicamento(db.Model):

    __tablename__ = "medicamentos"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    idoso_id = db.Column(
        db.Integer,
        db.ForeignKey("idosos.id"),
        nullable=False
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    dosagem = db.Column(
        db.String(50)
    )

    horario = db.Column(
        db.String(10)
    )


class Queda(db.Model):

    __tablename__ = "quedas"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    idoso_id = db.Column(
        db.Integer,
        db.ForeignKey("idosos.id"),
        nullable=False
    )

    foto = db.Column(
        db.String(255)
    )

    latitude = db.Column(
        db.Float
    )

    longitude = db.Column(
        db.Float
    )

    observacao = db.Column(
        db.Text
    )

    data_hora = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class MonitoramentoConfig(db.Model):
    __tablename__ = "monitoramento_config"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    idoso_id = db.Column(
        db.Integer,
        db.ForeignKey("idosos.id"),
        nullable=True
    )

from datetime import datetime


class TelegramVinculo(db.Model):

    __tablename__ = "telegram_vinculos"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False,
        unique=True
    )

    token = db.Column(
        db.String(64),
        nullable=False,
        unique=True,
        index=True
    )

    expira_em = db.Column(
        db.DateTime,
        nullable=False
    )

    usado = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    criado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )