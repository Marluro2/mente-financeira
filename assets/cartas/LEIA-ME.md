# Ilustrações das cartas — Memória Financeira (Nível 1)

Ilustrações vetoriais (SVG) criadas para o projeto. Por serem vetoriais,
ficam nítidas em qualquer tela, do celular ao projetor.

| Arquivo | Conceito |
|---|---|
| `poupanca.svg` | Poupança (porquinho com moeda) |
| `orcamento.svg` | Orçamento (prancheta, lista e gráfico) |
| `juros_compostos.svg` | Juros compostos (planta que dá moedas) |
| `cartao_credito.svg` | Cartão de crédito (com alerta de juros) |
| `investimento.svg` | Investimento (gráfico em alta) |
| `reserva_emergencia.svg` | Reserva de emergência (guarda-chuva protegendo moedas) |
| `meta.svg` | Meta financeira (alvo) |
| `inflacao.svg` | Inflação (balão com etiqueta de preço) |
| `divida.svg` | Dívida (bola de ferro com corrente) |
| `consumo_consciente.svg` | Consumo consciente (sacola com folha) |
| `renda.svg` | Renda (carteira com notas) |
| `seguranca.svg` | Segurança digital (escudo e cadeado contra golpes) |
| `verso.svg` | Verso de todas as cartas: "?" amarelo sobre listras escuras, no estilo carta de baralho (escolhido em 07/10/2026). O verso anterior, meio cérebro e meio gráfico, está em `opcoes_verso/D_cerebro_grafico.svg` |

A pasta `opcoes_verso/` guarda as outras propostas de verso (A, B, C, D) e o
verso antigo com ponto de interrogação, caso se queira trocar no futuro.

## Como acrescentar uma carta

1. Crie um SVG quadrado com `viewBox="0 0 200 200"` e cantos arredondados
   (use um dos arquivos acima como modelo).
2. Salve nesta pasta.
3. Acrescente um bloco `[[concepts]]` em
   `mente_financeira/content/memoria.toml` com nome, imagem, cor e dica.
4. Rode `python -m pytest` — os testes conferem se a imagem existe e é um SVG
   válido.

## Ensino Fundamental 1

O baralho do Ensino Fundamental 1 fica em
`mente_financeira/content/memoria_fundamental1.toml` (12 conceitos, 8 sorteados
por partida). As ilustrações novas estão em `fundamental1/`; Cofrinho,
Orçamento e Objetivo reaproveitam `poupanca.svg`, `orcamento.svg` e `meta.svg`.

| Arquivo | Conceito |
|---|---|
| `fundamental1/dinheiro.svg` | Dinheiro (nota e moedas) |
| `fundamental1/necessidade.svg` | Necessidade (casa e gota d'água) |
| `fundamental1/desejo.svg` | Desejo (controle de videogame com coração) |
| `fundamental1/troco.svg` | Troco (nota que volta em moedas) |
| `fundamental1/esperar.svg` | Esperar vale a pena (ampulheta) |
| `fundamental1/tres_potes.svg` | Guardar, gastar e doar (três potes) |
| `fundamental1/preco.svg` | Preço (etiqueta e moeda) |
| `fundamental1/trabalho.svg` | Trabalho (maleta) |
| `fundamental1/cuidar.svg` | Cuidar das coisas (bola e coração) |

## Engenharia de Produção

O baralho da Engenharia de Produção fica em
`mente_financeira/content/memoria_engenharia.toml` (12 conceitos de engenharia
econômica, 8 sorteados por partida). As ilustrações estão em `engenharia/`:

| Arquivo | Conceito |
|---|---|
| `fluxo_caixa.svg` | Fluxo de caixa (barras que sobem e descem) |
| `vpl.svg` | VPL (dinheiro do futuro trazido para hoje) |
| `tir.svg` | TIR (mostrador no verde) |
| `tma.svg` | TMA (sarrafo do salto em altura) |
| `payback.svg` | Payback (ampulheta enchendo de moedas) |
| `custo_oportunidade.svg` | Custo de oportunidade (placas apontando dois caminhos) |
| `ponto_equilibrio.svg` | Ponto de equilíbrio (balança equilibrada) |
| `depreciacao.svg` | Depreciação (máquina e gráfico em queda) |
| `sac_price.svg` | SAC x Price (parcelas que caem e parcelas iguais) |
| `custos.svg` | Custo fixo e variável (galpão e caixas) |
| `valor_presente.svg` | Dinheiro no tempo (relógio e moedas) |
| `margem_contribuicao.svg` | Margem de contribuição (etiqueta com a fatia do lucro) |
