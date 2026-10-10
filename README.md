# Mente Financeira — Flet

Versão reconstruída em Python 3.14 e Flet 0.86.5 a partir do projeto HTML/CSS/JavaScript original.

## Jogar pela web

Site (GitHub Pages): https://marluro2.github.io/mente-financeira/

Abre em qualquer computador ou celular, sem instalar nada. Na primeira vez o
navegador baixa o jogo (alguns segundos a mais); depois fica em cache. O site
é reconstruído e publicado automaticamente a cada envio para a branch `main`
(veja `.github/workflows/publicar-site.yml`). O modo administrador só existe
na versão de computador.

## Duelo em sala (feira, sem internet)

O notebook vira o servidor do jogo (`JOGAR_FEIRA.bat` ou `python servidor_sala.py`).
Os celulares no mesmo Wi-Fi abrem o endereço do notebook. Uma pessoa cria a
sala e recebe um código (ex.: `GATO-42`) com QR code, e a outra entra com o
código. Tudo vem do notebook, inclusive os emojis (`assets/fontes/emoji.woff2`),
então funciona sem internet. O cartaz com o QR code da mesa fica em
`http://localhost:8000/mesa`. Só pedimos um apelido, e nada é gravado.

**Quiz ao vivo:** o notebook abre `http://localhost:8000/?quiz=apresentar` e
vira o telão (QR code, perguntas, relógio, placar e pódio). O público entra
pelo QR code e responde pelo celular; quem acerta mais rápido ganha mais
pontos. As perguntas vêm do Desafio Relâmpago da trilha escolhida.

O botão **Deixe sua sugestão** salva sugestões anônimas em
`sugestoes/sugestoes.csv` no notebook. No site, o mesmo botão abre o Formulário
Google cujo endereço estiver em `FORM_URL` (`mente_financeira/sugestoes.py`).

Passo a passo para o estande, com roteador, Firewall e IP fixo, em
[docs/GUIA_FEIRA.md](docs/GUIA_FEIRA.md).

## Como jogar (Windows) — 2 cliques

| Arquivo | Para quê |
|---|---|
| **Mente Financeira** (atalho) ou **JOGAR.bat** | Abre o jogo em janela própria, maximizada, sem terminal e sem abas do navegador |
| **Mente Financeira (Administrador)** ou **JOGAR_ADMIN.bat** | Modo do professor (veja abaixo) |
| INSTALAR.bat | Prepara tudo (ambiente `.venv`, Flet e atalhos). O JOGAR.bat chama sozinho na primeira vez |
| JOGAR_COM_DIAGNOSTICO.bat | Use se o jogo não abrir: mostra os registros (`registros\iniciador.log`) |
| CRIAR_ATALHOS.bat | Recria os dois atalhos desta pasta (se a pasta mudar de lugar) |

Requisitos: Windows 10/11, Python 3.14 (python.org) e Microsoft Edge ou Google
Chrome. A janela usa o **modo aplicativo** do Edge, o que evita o bloqueio do
`flet.exe` pelo Controle Inteligente de Aplicativos (WinError 4551). O jogo não
abre duas vezes ao mesmo tempo; o modo administrador pode ficar aberto junto.

### Modo administrador (para o professor)

- Faixa amarela **MODO ADMINISTRADOR** nas telas.
- **Painel do professor** na abertura, com três abas: os 12 **conceitos** (dica
  e exemplo, na ordem do banco), **Desafios Relâmpago** de cada tipo com
  gabarito e explicação, e todas as **questões do Nível 2** com resolução.
- Jogo da memória: botão **Mostrar gabarito** (não conta como jogada) e
  cronômetro desligado. Desafio Relâmpago: gabarito visível.
- Nível 2: cronômetro desligado.
- Preferências gravadas à parte (pasta `admin`), sem misturar com os alunos.

## Como o jogo está organizado

| Tela | O que é |
|---|---|
| **Abertura** | Título, escolha Solo/Duelo, nomes e acesso aos níveis |
| **Nível 1 — Memória Financeira** | Jogo da memória tradicional: 16 cartas (8 pares iguais) sorteadas entre 12 conceitos; cada par revela um "Você sabia?". No Duelo, cada par traz um **Desafio Relâmpago** de porcentagem (com lousa): acertou, continua; errou, passa a vez |
| **Nível 2 — Desafio dos Cálculos** | Pares questão ↔ resolução com porcentagem, juros, inflação e financiamentos (8 fases) |

Efeitos sonoros (virar carta, acerto, erro, incentivo e vitória) ficam em
`assets/sons/` e são gerados por `ferramentas/gerar_sons.py`. O botão 🔊/🔇
liga e desliga os sons.

As ilustrações das cartas ficam em `assets/cartas/` (veja o `LEIA-ME.md` da
pasta) e os textos em `mente_financeira/content/memoria.toml`. Capturas de
tela em `docs/capturas/`.

## Nível 2 — principais melhorias

- Tabuleiro dividido: apenas **questões à esquerda** e apenas **resoluções à direita**.
- As oito cartas usam a altura disponível da janela e permanecem visíveis na mesma tela, sem rolagem durante a partida.
- Layout adaptado a **celular, tablet e computador**; no celular a lousa abre em painel deslizante e a questão aberta aparece por inteiro (capturas em `docs/capturas/`).
- O jogador deve abrir primeiro uma questão e depois procurar a resolução correspondente.
- Oito fases de educação financeira, com cálculos feitos por `Decimal` e arredondamento monetário consistente.
- Explicação passo a passo após cada acerto.
- Cronômetro seguro, com pausa durante a leitura das explicações.
- Repetição da fase sem permitir acúmulo artificial de pontos.
- Bloqueio correto do tabuleiro durante a comparação das cartas.
- Layout compacto e flexível, três paletas, modo escuro e lousa vetorial lateral com desfazer e limpar.
- A lousa inicia recolhida e pode ser aberta pelo botão **Abrir lousa**, sem empurrar as cartas para baixo.
- Correção do erro de gestos: no Flet 0.86.5, as coordenadas são lidas de `event.local_position.x` e `event.local_position.y`.
- Inicialização automática no navegador no Windows, evitando o `WinError 4551` quando uma política institucional bloqueia o cliente desktop do Flet.
- Arquitetura modular: cálculos, banco de questões (TOML), motor do jogo, armazenamento e interface separados.
- Paleta e modo escuro lembrados entre sessões.
- Testes automatizados para fórmulas, banco de questões, regras da partida e fluxo das telas.

## Estrutura

```text
mente_financeira_flet/
├── main.py                      # ponto de entrada (também usado pelo flet build)
├── assets/cartas/               # ilustrações SVG das cartas do Nível 1
├── mente_financeira/
│   ├── finance.py               # fórmulas financeiras e formatação em R$
│   ├── content/
│   │   ├── memoria.toml         # baralho do Nível 1 (conceitos e dicas)
│   │   ├── memory_deck.py       # leitura e validação do baralho
│   │   ├── medio.toml           # banco de questões do Nível 2
│   │   ├── calculators.py       # cálculos usados pelos modelos de texto
│   │   └── __init__.py          # leitura e validação dos bancos
│   ├── core/
│   │   ├── memory_game.py       # regras do Nível 1 (memória)
│   │   └── session.py           # regras do Nível 2 (cálculos)
│   ├── storage.py               # preferências salvas localmente
│   └── ui/
│       ├── shell.py             # navegação entre as telas
│       ├── home.py              # tela de abertura
│       ├── memory_screen.py     # Nível 1
│       ├── app.py               # Nível 2
│       └── ...                  # estilo, layout, lousa, paletas
├── tests/                       # testes automatizados (pytest)
├── CHANGELOG.md                 # histórico de versões
├── requirements.txt
└── pyproject.toml
```

## Editar o banco de questões

As questões ficam em `mente_financeira/content/medio.toml`. Para acrescentar
um cenário, copie uma linha da lista `scenarios` da fase e altere os valores:

```toml
{ id = "fone", kind = "discount", context = "Um fone sem fio", base = 180, rate = "0.25" },
```

Escreva as taxas entre aspas (`"0.25"` = 25%) e use um `id` que ainda não
exista na fase. Em seguida rode os testes: eles geram todas as questões e
apontam a fase e o cenário de qualquer campo faltando ou conta inconsistente.

## Executar com Python 3.14

No terminal, entre na pasta do projeto e execute:

```bash
python3.14 -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
flet run main.py
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

No Windows, `python main.py` abre automaticamente o navegador e mantém o servidor restrito a `127.0.0.1` (somente o computador local). Em Linux e macOS, o modo desktop continua sendo o padrão.

Para abrir explicitamente no navegador em qualquer sistema:

```bash
flet run --web main.py
```

## Windows: política de Controle de Aplicativos

O erro abaixo não é causado pelos cálculos ou pela interface do jogo:

```text
OSError: [WinError 4551] Uma política de Controle de Aplicativo bloqueou este arquivo
```

Ele ocorre quando o Windows impede a execução do cliente nativo auxiliar do Flet. Esta versão evita o arquivo bloqueado e usa `ft.AppView.WEB_BROWSER` automaticamente no Windows.

Também é possível executar com o caminho completo do Python, como no exemplo:

```powershell
& "C:\Users\USUARIO\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pip install -r requirements.txt
& "C:\Users\USUARIO\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py
```

Não é necessário desativar a política de segurança. Se o modo desktop for posteriormente autorizado pelo administrador, ele pode ser ativado antes da execução:

```powershell
$env:MENTE_FINANCEIRA_VIEW = "desktop"
python main.py
```

## Testes

Instale as dependências de desenvolvimento e execute:

```bash
python -m pip install -e ".[dev]"
pytest
```

## Regra da rodada

1. O jogador da vez abre uma carta no painel **Questões**.
2. Em seguida, abre uma carta no painel **Resoluções**.
3. Se as cartas formarem um par, ele marca um ponto, lê a explicação e joga novamente.
4. Se não formarem um par, ambas são fechadas e a vez passa ao outro jogador.
5. A fase termina somente após os quatro pares serem encontrados.
