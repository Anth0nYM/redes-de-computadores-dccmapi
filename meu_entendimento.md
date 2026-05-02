## Resumo rápido do trabalho

O objetivo central desta primeira fase é criar e testar um sistema Cliente/Servidor de transferência de arquivos em Python rodando em contêineres Docker (Ubuntu)

### O Código

O sistema operará em dois modos: TCP nativo e um R-UDP (UDP Confiável) construído por nós, que precisará ter controle de erros via janela deslizante, timeouts, retransmissões e validação de integridade.

### O Teste

Você usará o utilitário tc do Linux para degradar a rede artificialmente em três cenários específicos (variando perda de pacotes de 0% a 20% e atraso de 10ms a 100ms).

### A Validação Cruzada

É aqui que está o peso do trabalho. Vamos monitorar a aplicação internamente (medindo tempo e vazão) e externamente capturando o tráfego de rede com o tcpdump. O objetivo é provar que o que a aplicação acha que enviou/recebeu bate com o que realmente trafegou na interface de rede.

### Entregáveis

Além do código e dos logs de rede (.pcap e CSV/JSON), você precisará entregar um relatório no formato da SBC, um notebook no Colab com análise estatística usando Plotly ou Seaborn, e um vídeo demonstrativo.

## Minha implementação

A minha implementação será dividida em 3 caminhos lógicos:

1. O Ambiente (Docker & TC): Criar o Dockerfile (baseado no Ubuntu) e o docker-compose.yml para subir os contêineres do Cliente e do Servidor, já deixando o terreno pronto para os comandos do tc (controle de tráfego).

2. O Modo TCP (A Base): Começar pelos scripts Python (server.py e client.py) implementando apenas a transferência de arquivo via TCP padrão. Isso nos dá uma base sólida que já funciona antes de lidarmos com a perda de pacotes.

3. O R-UDP com Go-Back-N (O Núcleo Duro): Pular direto para a lógica do protocolo UDP confiável, estruturando como os pacotes serão divididos, como a janela deslizante vai funcionar e como os timeouts (ACKs) serão controlados em Python.