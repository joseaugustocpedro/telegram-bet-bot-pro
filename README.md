# Telegram Bet Bot Pro

Projeto em Python para gestão e registro de operações via Telegram, desenvolvido como exercício de automação, persistência de dados e interação por bot.

O foco técnico do repositório está em **arquitetura de bot, processamento de comandos, persistência, validação de entradas e automação de fluxos**.

> Projeto educacional. Não constitui aconselhamento financeiro nem promessa de resultado.

## Tecnologias

- Python
- Telegram Bot API / python-telegram-bot
- persistência de dados conforme configuração do projeto

## Estrutura

```text
telegram-bet-bot-pro/
├── bot.py
├── requirements.txt
└── README.md
```

## Instalação

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure `BOT_TOKEN` e `DATABASE_URL` de forma privada, consultando o [modelo `.env.example`](.env.example). Em seguida, execute:

```bash
python bot.py
```

## Competências demonstradas

- automação de fluxos;
- integração com APIs;
- programação Python;
- validação de dados;
- desenvolvimento orientado a eventos;
- documentação e manutenção de software.

> **Escopo:** projeto educacional de automação e persistência. Não é apresentado como serviço auditado ou pronto para uso comercial. Não versionar tokens, URLs de banco com credenciais ou registros privados.

## Autor

**José Augusto Cevidanes Pedro**  
Estudante de Engenharia de Controle e Automação — IFSP
