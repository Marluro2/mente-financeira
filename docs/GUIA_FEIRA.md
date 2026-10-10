# Guia da feira: Duelo em sala e Quiz ao vivo

O notebook vira o servidor do jogo. Os celulares entram no Wi-Fi do estande e
jogam pelo navegador, **sem internet**. Uma pessoa cria a sala e recebe um
código, como `GATO-42`. A outra digita o código ou escaneia o QR code, e o
Duelo começa nos dois celulares.

O jogo pede só um apelido e não grava nada. O apelido pode aparecer no
ranking do cartaz até o servidor fechar; a partida some quando a pessoa sai.

## Antes da feira (em casa, com internet)

1. Rode **INSTALAR.bat** uma vez, ou só o **JOGAR_FEIRA.bat**, que instala o
   que faltar.
2. Faça um ensaio completo com o roteador e dois celulares, de preferência com
   o cabo de internet do roteador desligado.

## Roteador do estande

- **Sem cabo de internet:** o roteador só cria a rede local.
- **Isolamento de clientes desligado.** No painel do roteador, essa opção pode
  se chamar "AP Isolation", "Client Isolation" ou "Isolamento de clientes".
  Se ela estiver ligada, os celulares não enxergam o notebook.
  Rede de convidados ("Guest") costuma ter isolamento: use a rede principal.
- **IP fixo para o notebook.** No roteador, procure "Reserva de DHCP" ou
  "Address Reservation" e reserve um IP (ex.: `192.168.0.10`) para o
  notebook. Assim o endereço e o QR code não mudam entre um dia e outro.

## No dia, no notebook

1. Conecte o notebook no Wi-Fi do estande.
2. Clique duas vezes em **JOGAR_FEIRA.bat**.
3. Na primeira vez, o Windows pergunta sobre o Firewall: marque **Redes
   privadas** e clique em **Permitir acesso**. Se a rede do roteador estiver
   como "Pública", troque para "Privada" nas configurações de Wi-Fi.
4. A janela preta mostra o endereço para os celulares, por exemplo
   `http://192.168.0.10:8000`. Deixe essa janela aberta: fechar encerra o jogo.
5. O navegador abre o **cartaz com o QR code** (`http://localhost:8000/mesa`).
   Deixe na tela do notebook ou imprima (Ctrl+P) e coloque na mesa.

## No celular dos visitantes

1. Conectar no Wi-Fi do estande.
2. Escanear o QR code da mesa (ou digitar o endereço).
3. Digitar um apelido. Uma pessoa toca em **Criar sala**, escolhendo a
   trilha (Fundamental 1, Fundamental 2 ou Engenharia de Produção), e mostra
   o código ou o QR code da sala. A outra escaneia esse QR code ou digita o
   código e toca em **Entrar**.

## Quiz ao vivo (para o grupo todo)

Bom para turmas e grupos parados no estande: as perguntas aparecem na tela do
notebook (ou no projetor/TV ligado nele) e cada pessoa responde pelo celular.
Quem acerta mais rápido ganha mais pontos, e o placar aparece a cada pergunta.

1. No notebook, abra `http://localhost:8000/?quiz=apresentar` (a janela preta
   mostra esse endereço, e o cartaz da mesa tem o botão **Abrir o Quiz ao
   vivo**). Essa tela só abre no próprio notebook.
2. Escolha a trilha das perguntas (Fundamental 1, Fundamental 2 ou Engenharia
   de Produção).
3. O público conecta no Wi-Fi do estande, escaneia o QR code da tela e digita
   um apelido. Os apelidos aparecem na tela do notebook.
4. Clique em **Começar o quiz**. São 8 perguntas de 30 segundos. A resposta
   aparece quando o tempo acaba ou quando todos responderam (ou clique em
   **Mostrar a resposta agora**).
5. Depois de cada resposta, clique em **Próxima pergunta**. No fim aparece o
   **pódio**. **Novo quiz** começa outra rodada com as mesmas pessoas.

Quem chega atrasado pode entrar no meio do quiz. Como no Duelo, só pedimos um
apelido e nada é gravado.

## Ranking do dia

O cartaz do notebook (`http://localhost:8000/mesa`) mostra, ao lado do QR
code, os 5 melhores apelidos do **Duelo em sala** e do **Quiz ao vivo**. Ele
atualiza sozinho a cada partida que termina. Cada apelido aparece uma vez por
placar, com o melhor resultado.

- O ranking fica só na memória do notebook: some quando a janela preta fecha.
- Apelido ofensivo? No cartaz aberto no próprio notebook, clique no **✕** ao
  lado dele. **Limpar ranking** zera os dois placares. Esses botões não
  aparecem nem funcionam nos celulares.
- Na impressão (Ctrl+P) o ranking não sai, só o QR code.

## Sugestões dos visitantes

Na tela inicial do celular há o botão **Deixe sua sugestão**. A sugestão é
anônima (só o texto e, se a pessoa quiser, o nível de ensino e a idade) e fica
salva no notebook em `sugestoes\sugestoes.csv`, que abre no Excel. A janela
preta mostra esse caminho ao iniciar.

## Se algo der errado

| O que acontece | O que fazer |
|---|---|
| O celular diz "sem internet" ou volta para os dados móveis | Escolher **manter conectado** no Wi-Fi; se preciso, desligar os dados móveis |
| A página não abre no celular | Conferir se o celular está no Wi-Fi do estande, o isolamento de clientes e o Firewall (passo 3) |
| O endereço mudou | Reservar o IP no roteador; reabrir o JOGAR_FEIRA.bat e o cartaz |
| "Não achei a sala" | Conferir o código; quem criou a sala não pode ter saído dela |
| O endereço do quiz abre a tela de jogador no notebook | Abrir pelo próprio notebook com `localhost` (ou pelo IP do notebook), não por outro computador |
| Nada funciona | Plano B: **Duelo no mesmo aparelho**, que já existe no jogo normal (JOGAR.bat ou o site) |

Cada celular também pode abrir o jogo normal pelo site, se houver internet.
