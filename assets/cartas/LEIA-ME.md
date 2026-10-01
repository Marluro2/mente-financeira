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
| `verso.svg` | Verso de todas as cartas: meio cérebro, meio gráfico em alta, com o nome "Mente Financeira" (opção D, escolhida em 28/09/2026) |

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
