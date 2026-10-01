# Histórico de versões

Registro das alterações do software (seção 5.10 do projeto — rastreabilidade).

## 3.8.0 — 01/10/2026

### Repositório no GitHub e publicação na web
- Código versionado com Git e publicado em
  https://github.com/Marluro2/mentte-financeira (seção 5.10 do projeto).
- `.github/workflows/publicar-site.yml`: a cada envio, o GitHub roda os testes,
  constrói o site estático (`flet build web`, Python 3.14 no navegador) e
  publica no GitHub Pages.
- Preferências (som, paleta) guardadas no **armazenamento do navegador** quando
  o jogo roda como site (`storage.connect_browser_storage`).
- `pyproject.toml`: dependências do site sem o servidor local (que virou o
  extra `desktop`), e lista do que não entra no pacote publicado.
- O modo administrador existe só na versão de computador (no site público os
  gabaritos ficariam expostos).

## 3.7.0 — 30/09/2026

### Efeitos sonoros
- **Memória:** som ao virar carta, ao formar par ("acerto"), ao errar o par e
  fanfarra de vitória no fim da partida.
- **Desafio Relâmpago:** fanfarra de **incentivo** no acerto; som suave no erro.
- **Nível 2 (questões e resoluções):** som ao abrir carta, ao acertar o par, ao
  errar e ao concluir a fase.
- Botão **🔊/🔇** no jogo da memória e no Nível 2; a escolha é lembrada.
- Sons **gerados pelo próprio projeto** (`ferramentas/gerar_sons.py`, só
  biblioteca padrão): sem arquivos de terceiros nem direitos autorais.
- Nova dependência: `flet-audio==0.86.5` (instalada pelo INSTALAR.bat).

### Corrigido
- Trocar a paleta no Nível 2 apagava outras preferências salvas.

## 3.6.0 — 30/09/2026

### Desafio Relâmpago contextualizado, com imagem
- Novo visual (inspirado no Responda ou Estuda, nas cores do jogo): painel com
  a **imagem da situação** à esquerda e cartão com **tipo** ("DESCONTO À
  VISTA", "AUMENTO DE PREÇO", "PLANEJANDO A MESADA", "QUANTO POR CENTO?"),
  **item**, pergunta e alternativas em pílulas **A. B. C. D.**
- O painel da esquerda mostra a imagem, dá lugar à **lousa** quando aberta e à
  **comemoração/correção** após a resposta. No celular, tudo empilhado.
- **17 ilustrações novas** em `assets/desafios/`, incluindo situações do dia a
  dia: passe de ônibus, recarga de celular, conta de luz, presente de
  aniversário, curso online e pizza.
- Painel do professor (aba Desafios) mostra a imagem, o tipo e o item.

### Corrigido
- Concordância: "Uma camiseta… ficou 20% mais **cara**" (antes "mais caro").
- Conta de luz e passe de ônibus não recebem "desconto à vista".

## 3.5.0 — 28/09/2026

### Execução em 2 cliques (adaptado do "Responda ou Estuda")
- `iniciar_janela_app.py`: abre o jogo em **janela própria** (modo aplicativo
  do Edge/Chrome), maximizada, sem terminal e sem abas; impede duas cópias
  abertas; encerra tudo ao fechar a janela; registros em `registros/`.
- `JOGAR.bat` (instala sozinho na primeira vez), `JOGAR_ADMIN.bat`,
  `JOGAR_COM_DIAGNOSTICO.bat`, `INSTALAR.bat` e `CRIAR_ATALHOS.bat`.
- Atalhos **"Mente Financeira"** e **"Mente Financeira (Administrador)"** na
  pasta do jogo, com ícone próprio (`assets/icone.ico`, gerado do verso das
  cartas); `assets/icon.png` e `assets/favicon.png` dão o ícone da janela.

### Modo administrador (`MENTE_ADMIN=1`)
- Painel do professor: conceitos, Desafios Relâmpago com gabarito e questões do
  Nível 2 com resolução.
- Memória: "Mostrar gabarito" e cronômetro desligado; desafio com gabarito;
  Nível 2 sem cronômetro; preferências separadas.

### Ajustado
- Abertura compacta em telas de computador baixas (ex.: 1536×864 com barra de
  tarefas): o botão "JOGAR AGORA" cabe sem rolar.

## 3.4.0 — 28/09/2026

### Painel "Conceitos descobertos"
- No computador, o painel ocupa **todo o lado direito**, na altura do
  tabuleiro, e rola por dentro; no celular, fica abaixo do tabuleiro.
- **Destaque** do último conceito: imagem grande, nome, "✨ Novo conceito!",
  "💡 Você sabia?" e o novo bloco **"📌 Na prática"**, com um exemplo do dia a
  dia com números.
- **Lista dos já descobertos** (mais recente primeiro): tocar num item traz o
  conceito de volta para o destaque.
- Contador "3/8" com barra de progresso e aviso de quantos conceitos faltam.
- Novo campo obrigatório `example` em `content/memoria.toml`; as contas de todos
  os exemplos foram conferidas.

## 3.3.0 — 28/09/2026

### Novo verso das cartas
- Verso "meio cérebro, meio gráfico em alta" com o nome **Mente Financeira**
  (opção D, escolhida entre quatro propostas). As demais propostas e o verso
  antigo ficam em `assets/cartas/opcoes_verso/`.

### Ajustado
- Desafio Relâmpago no computador: antes de responder, com a lousa fechada, a
  pergunta usa a largura toda (a coluna da direita só aparece com a lousa ou
  com o resultado).

## 3.2.0 — 28/09/2026

### Desafio Relâmpago em tela inteira
- O desafio ocupa a **tela inteira**, com fundo próprio, pergunta e
  alternativas em letras grandes.
- **Acerto:** bloco de comemoração em destaque (🎉, degradê verde-ciano, brilho,
  frase de incentivo em letra grande e "a vez continua sua!"), que entra com
  animação de "pulo".
- **Erro:** bloco próprio com 💡, a resposta certa em destaque, a conta
  explicada e o aviso de quem joga a seguir.
- Computador: pergunta à esquerda; à direita, a lousa antes de responder e a
  comemoração/correção depois. Celular: tudo empilhado.

## 3.1.0 — 27/09/2026

### Desafio Relâmpago no Duelo (Nível 1)
- No modo Duelo, cada par encontrado (exceto o último) abre um **desafio de
  porcentagem** de múltipla escolha, com valores que dão para calcular de
  cabeça (mesada, descontos, aumentos, "quantos por cento").
- **Acertou:** frase de incentivo e o jogador continua. **Errou:** a resposta
  certa aparece com a conta explicada e a vez passa ao adversário. O ponto do
  par é mantido nos dois casos.
- As alternativas erradas imitam erros comuns (confundir desconto com preço
  final, somar em vez de subtrair, errar a casa decimal).
- Botão **Abrir lousa** dentro do desafio para fazer a conta.
- O resultado final do Duelo mostra quantos desafios cada jogador acertou.
- Gerador em `core/percent_challenge.py`, verificado em 1.600 sorteios
  (4 alternativas distintas, conta correta, resultado inteiro).

### Corrigido
- Lousa com título e ícones quase invisíveis quando aberta sobre o tema escuro;
  as cores da lousa agora são fixas.

## 3.0.0 — 27/09/2026

### Nova abertura e Nível 1 — Memória Financeira
O jogo agora começa por uma **tela de abertura** voltada a adolescentes
(fundo escuro com cores neon, título em degradê, cartas em leque e ícones
flutuantes) e por um **jogo da memória tradicional com 16 cartas**.

- 8 pares de cartas iguais por partida, sorteados entre **12 conceitos** de
  educação financeira, para que as partidas variem.
- **Ilustrações próprias** em `assets/cartas/` (12 conceitos + verso), em SVG.
- Cada par encontrado revela um **"Você sabia?"** sobre o conceito, e a faixa
  "Conceitos descobertos" mostra o progresso.
- **Solo** (cronômetro, jogadas e até 3 estrelas) ou **Duelo** (2 jogadores;
  quem acerta joga de novo, quem erra passa a vez).
- Conteúdo em `content/memoria.toml`, editável sem programar e validado pelos
  testes.
- O jogo anterior (questão ↔ resolução) virou o **Nível 2 — Desafio dos
  Cálculos**, acessível pela abertura, com botão "Menu inicial".

### Corrigido
- Janelas de explicação e de resultado ocupavam a tela inteira com espaço vazio;
  agora têm o tamanho do conteúdo e só rolam quando necessário.

### Testes
- 155 testes, incluindo o baralho (imagens existem e são SVG válidos), as regras
  da memória e o fluxo abertura → partida → resultado → Nível 2, no celular e no
  computador.

## 2.2.0 — 27/09/2026

### Layout para celular, tablet e computador
A interface se adapta a três faixas de largura (`ui/layout.py`) e se
redesenha ao girar o aparelho ou redimensionar a janela, **sem perder** placar,
cronômetro, cartas abertas ou o rascunho da lousa.

| | Celular (< 700 px) | Tablet (700–1099 px) | Computador (≥ 1100 px) |
|---|---|---|---|
| Cabeçalho | compacto, aparência em menu | compacto, aparência em menu | completo |
| Botões | só ícones | ícone + texto | ícone + texto |
| Lousa | painel deslizante com a questão aberta | painel deslizante | ao lado do tabuleiro |
| Enunciado | faixa "Questão aberta" com o texto inteiro | na carta | na carta |

Capturas em `docs/capturas/`.

### Adicionado
- Tocar num par já encontrado mostra questão, resposta e explicação (antes a
  carta ficava bloqueada e o texto só aparecia como dica do mouse, que não
  existe no celular).
- "Reiniciar jogo" pede confirmação.
- `SafeArea`: o conteúdo não fica sob o entalhe e as barras do celular.
- Explicações longas rolam dentro da janela.

### Alterado
- Lousa: amostragem do traço a cada 20 ms e descarte de movimentos < 2 px,
  reduzindo o tráfego entre Python e a tela no celular.
- Cartas fechadas ocupam toda a largura da coluna.
- Ícone de "Reiniciar jogo" passou a ser uma casa, distinto de "Repetir fase".

### Testes
- 100 testes. O fluxo completo roda nas três larguras; há testes para girar a
  tela no meio da fase, a lousa no celular, o menu de aparência e a revisão
  de pares.

## 2.1.0 — 27/09/2026

### Arquitetura modular (Quadro 3 do projeto)
O código foi separado no pacote `mente_financeira/`:

| Módulo | Responsabilidade |
|---|---|
| `finance.py` | Fórmulas financeiras e formatação em R$ |
| `content/*.toml` | Bancos de questões por trilha, editáveis sem programar |
| `content/calculators.py` | Cálculos que alimentam os modelos de texto |
| `core/session.py` | Motor do jogo: vez, pontuação, erros, cronômetro, progressão |
| `storage.py` | Preferências salvas localmente (paleta e modo escuro) |
| `ui/` | Telas, lousa e paletas em Flet |

- As questões geradas são idênticas às da versão 2.0.1 (comparadas em 200
  sorteios de cada fase).
- O banco TOML é validado ao ser carregado: um campo faltando ou uma fase com
  poucos cenários gera uma mensagem indicando a fase e o cenário.
- A paleta e o modo escuro escolhidos passam a ser lembrados entre sessões.

### Corrigido
- Tela inicial: o logotipo e o título apareciam como um **bloco cinza**
  (erro de layout do Flutter causado por `expand` dentro de uma linha com
  `wrap`). Presente desde a versão 2.0.0.

### Testes
- 66 testes: fórmulas, validação do banco de questões, regras da partida,
  armazenamento e o fluxo completo das telas com uma página simulada.

## 2.0.1 — 27/09/2026

### Corrigido
- **Fase 8 (total pago no PRICE):** o total era calculado com a prestação sem
  arredondamento, enquanto a explicação exibia a prestação arredondada. Exemplo:
  "R$ 53,56 × 6 = R$ 321,35" (o correto é R$ 321,36). O total agora parte da
  prestação arredondada ao centavo, como ocorre em um carnê real.
- **Concordância dos enunciados:** removidos "Um(a)", "financiado(a)",
  "do(a)" e construções como "Em uma desconto à vista" ou "Em uma investimento
  em CDB". Cada cenário passa a trazer o artigo correto.
- "por 1 meses" → "por 1 mês" na Fase 4.

### Adicionado
- Testes que conferem, em todos os cenários de todas as fases, se o valor da
  resolução aparece na explicação, se a conta da Fase 8 fecha e se os enunciados
  não têm marcas de gênero genéricas.

### Ambiente
- Ambiente virtual `.venv` com Python 3.14, Flet 0.86.5 e pytest 9.

## 2.0.0 — 23/08/2026
- Reconstrução em Python 3.14 + Flet a partir da versão HTML/CSS/JavaScript.
