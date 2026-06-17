<h1 align="center"> Andador Inteligente </h1>

<p align="center">
Projeto desenvolvido durante a disciplina de Robótica Inclusiva.
</p>

<p align="center">
  <a href="#-documentação">Documentação</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-projeto">Projeto</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-tecnologias">Tecnologias</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#%EF%B8%8F-funcionalidades">Funcionalidades</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-componentes-de-hardware">Hardware</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-fluxo-do-sistema">Fluxo do Sistema</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#%EF%B8%8F-arquitetura-c4-model">Arquitetura (C4 Model)</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-estrutura-da-documentação">Estrutura da Documentação</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-integrantes">Integrantes</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;
  <a href="#-licença">Licença</a>
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/static/v1?label=license&message=MIT&color=49AA26&labelColor=000000">
</p>

<br>

<p align="center">
  <img alt="Logo do Andador Inteligente" src="assets/logo_c3.png" width="35%">
</p>

## 🌐 Documentação

- 📄 **Documentação em PDF**: [Clique aqui para acessar](Documentacao_Andador_Inteligente.pdf)

## 💻 Projeto

O **Andador Inteligente** é um sistema assistivo embarcado desenvolvido para auxiliar no monitoramento de idosos durante o uso de um andador. O projeto integra uma aplicação web com sensores conectados a um Raspberry Pi, permitindo detectar quedas, obter localização real por GPS, capturar imagens, identificar obstáculos, emitir alertas sonoros e enviar notificações ao cuidador pelo Telegram.

A proposta busca aumentar a segurança do idoso e facilitar o acompanhamento remoto pelo cuidador, oferecendo uma solução prática baseada em Internet das Coisas, sistemas embarcados e interface web.

## 🚀 Tecnologias

Esse projeto foi desenvolvido com as seguintes tecnologias:

- Python
- Flask
- SQLite
- HTML
- CSS
- Raspberry Pi OS
- Raspberry Pi
- Telegram Bot API
- OpenCV
- YOLO
- RPi.GPIO
- smbus2
- pyserial
- pynmea2
- rpicam/libcamera
- Git e GitHub

## 🛠️ Funcionalidades

- **Cadastro de Cuidadores:** permite criar uma conta para acessar o sistema de monitoramento.

- **Login de Usuário:** controla o acesso à aplicação, garantindo que cada cuidador visualize apenas seus dados.

- **Cadastro de Idosos:** permite registrar idosos com nome, telefone, endereço, observações e foto.

- **Gerenciamento de Medicamentos:** possibilita cadastrar medicamentos com nome, dosagem e horário.

- **Lembrete de Medicamentos:** quando chega o horário cadastrado, o sistema aciona o buzzer, emite aviso por voz e envia mensagem ao Telegram do cuidador.

- **Monitoramento de Idoso:** permite selecionar qual idoso está utilizando o andador no momento.

- **Detecção de Quedas:** utiliza o acelerômetro MPU6050 para identificar movimentos bruscos compatíveis com queda.

- **Localização Real por GPS:** utiliza o módulo GPS NEO-6M para obter latitude e longitude reais do usuário.

- **Registro de Quedas:** salva no sistema informações como idoso, data, horário, localização, observação e foto.

- **Captura de Foto na Queda:** utiliza a câmera OV5647 para registrar uma imagem no momento da ocorrência.

- **Envio de Alertas pelo Telegram:** envia ao cuidador mensagens com dados da queda, link do Google Maps e foto capturada.

- **Detecção de Obstáculos:** utiliza câmera e YOLO para identificar obstáculos próximos ao andador.

- **Alerta Sonoro com Buzzer:** emite sinais sonoros em eventos de queda, obstáculos e medicamentos.

## 🔌 Componentes de Hardware

O projeto utiliza os seguintes componentes físicos:

- Raspberry Pi
- GPS NEO-6M
- MPU6050
- Câmera OV5647
- Buzzer
- Caixa de som
- Jumpers
- Protoboard ou conexões diretas

### GPS NEO-6M

Responsável por obter a localização real do idoso.

| GPS NEO-6M | Raspberry Pi |
|-----------|--------------|
| VCC | 5V |
| GND | GND |
| TX | GPIO15 / RXD / pino físico 10 |
| RX | GPIO14 / TXD / pino físico 8 |

A comunicação ocorre por UART/Serial, utilizando dados NMEA para obter latitude e longitude.

### MPU6050

Responsável por detectar aceleração e possíveis quedas.

| MPU6050 | Raspberry Pi |
|--------|--------------|
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO2 / pino físico 3 |
| SCL | GPIO3 / pino físico 5 |
| AD0 | GND ou desconectado |

A comunicação ocorre por I2C, utilizando o endereço `0x68`.

### Buzzer

Responsável por emitir alertas sonoros.

| Buzzer | Raspberry Pi |
|--------|--------------|
| Positivo | GPIO18 / pino físico 12 |
| Negativo | GND |

### Câmera OV5647

Responsável pela captura de imagens e apoio à detecção de obstáculos. A câmera é acessada pelo Raspberry Pi por meio do `rpicam/libcamera`.

## 🧭 Fluxo do Sistema

```mermaid
flowchart LR

A[Cuidador acessa o sistema] --> B[Realiza login]
B --> C[Cadastra idoso]
C --> D[Cadastra medicamentos]
D --> E[Conecta Telegram]
E --> F[Seleciona idoso em monitoramento]
F --> G[Andador entra em operação]

G --> H{Evento detectado}

H --> I[Horário de medicamento]
I --> J[Buzzer e aviso de voz]
J --> K[Mensagem no Telegram]

H --> L[Queda detectada]
L --> M[Buzzer contínuo]
M --> N[Câmera captura foto]
N --> O[GPS obtém localização real]
O --> P[Sistema salva queda]
P --> Q[Telegram envia alerta e foto]

H --> R[Obstáculo detectado]
R --> S[YOLO identifica obstáculo]
S --> T[Buzzer alerta o usuário]
