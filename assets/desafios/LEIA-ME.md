# Ilustrações das situações do Desafio Relâmpago

Ilustrações vetoriais (SVG, 200 × 200) criadas para o projeto, no mesmo
estilo das cartas. Cada pergunta do Desafio Relâmpago mostra a imagem da sua
situação.

| Arquivo | Situação | Aparece em |
|---|---|---|
| `tenis.svg` | Tênis de corrida | desconto, aumento |
| `fone.svg` | Fone de ouvido | desconto, aumento |
| `ingresso_show.svg` | Ingresso de show | desconto, aumento, quanto % |
| `camiseta.svg` | Camiseta | desconto, aumento |
| `videogame.svg` | Jogo de videogame | desconto, aumento |
| `mochila.svg` | Mochila | desconto, aumento |
| `lanche.svg` | Lanche | desconto, aumento, quanto % |
| `livro.svg` | Livro | desconto, aumento, quanto % |
| `streaming.svg` | Assinatura de streaming | desconto, aumento |
| `skate.svg` | Skate | desconto, aumento |
| `onibus.svg` | Passe mensal de ônibus | aumento |
| `recarga_celular.svg` | Recarga de celular | desconto, aumento, quanto % |
| `conta_luz.svg` | Conta de luz | aumento |
| `presente.svg` | Presente de aniversário | desconto, aumento, quanto % |
| `curso_online.svg` | Curso online | desconto, aumento |
| `pizza.svg` | Pizza | desconto, aumento, quanto % |
| `mesada.svg` | Mesada | planejando a mesada |

Os itens, preços e frases ficam em `mente_financeira/core/percent_challenge.py`
(lista `ITEMS`). Para acrescentar uma situação: crie o SVG aqui, acrescente um
`Item(...)` na lista e rode `python -m pytest` (os testes conferem se toda
imagem existe e é usada).
