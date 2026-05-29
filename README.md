# Transferência de Arquivos sobre TCP e R-UDP — Projeto de Redes de Computadores (2026-1)

**PPGCC/UFPI — Campus Senador Helvídio Nunes de Barros**
Autor: **Anthony Irlan Marques Luz** · Matrícula **20261011410**
Repositório: [github.com/Anth0nYM/redes-de-computadores-dccmapi](https://github.com/Anth0nYM/redes-de-computadores-dccmapi)
Enunciado completo: [`description.pdf`](description.pdf)

---

## 1. Visão geral

Este repositório implementa e avalia um sistema **cliente/servidor de transferência de
arquivos** em Python, executado dentro de containers Docker, com **dois modos de
transporte**:

1. **TCP nativo** — usa a pilha confiável do sistema operacional.
2. **R-UDP** (*Reliable UDP*) — protocolo confiável **implementado por nós sobre o UDP**,
   com **janela deslizante Go-Back-N** (janela = 8), números de sequência, ACKs,
   *timeout*/retransmissão e verificação de integridade.

O objetivo da **Fase 1** é comparar os dois protocolos sob três cenários de rede
degradada (emulados com `tc netem`) e **validar de forma cruzada** as métricas internas
da aplicação contra o tráfego real capturado com `tcpdump`. A Fase 2 (modelagem em SimPy)
ainda não foi iniciada.

> **Fluxo unidirecional (premissa de projeto).** O **cliente é sempre o remetente**
> (envia o arquivo) e o **servidor é sempre o receptor**. Por isso o cliente registra
> `throughput = bytes_enviados / tempo` e o servidor registra `bytes_recebidos / tempo`.

### Os três cenários de rede

| Cenário | Perda de pacotes | Atraso (one-way) | RTT aprox. |
|---------|------------------|------------------|------------|
| **A** | 0%  | 10 ms  | ~20 ms |
| **B** | 10% | 50 ms  | ~100 ms |
| **C** | 20% | 100 ms | ~200 ms |

---

### Entregáveis da Fase 1

| Entregável | Onde está |
|------------|-----------|
| 💻 **Código-fonte** | [github.com/Anth0nYM/redes-de-computadores-dccmapi](https://github.com/Anth0nYM/redes-de-computadores-dccmapi) (`src/`, `scripts/`, `docker/`) |
| 📓 **Análise + Colab** | `notebooks/main.ipynb` (8 figuras, executável no Google Colab) |
| 📄 **Relatório SBC** | [`paper/main.pdf`](paper/main.pdf) (fonte em `paper/main.tex`) |
| 🎥 **Vídeo demonstrativo** | **[assistir](https://drive.google.com/<inserir-link-do-video>)**|
| 🔎 **Evidências (pcap + X-Custom-Auth)** | `results/evidence/` |
| 🗂️ **Logs de captura (PCAP/CSV)** | Não versionados (binários grandes, ~155 MB) — **[pasta `logs/` no Google Drive](https://drive.google.com/drive/folders/12sBrG_SSxHayG23rZKkMgdw7EalQI_ml?usp=sharing)** (bateria completa: 60 pcaps + JSONL + CSV) |

## 2. Estrutura do repositório

```
redes_doutorado/
├── description.pdf            # Enunciado oficial do projeto (rubrica na seção 2.4)
├── README.md                  # Este arquivo
├── requirements.txt           # Dependências Python (scapy)
├── .gitignore / .dockerignore # Exclusões de versionamento e de build
│
├── docker/                    # Ambiente de execução (containers Ubuntu + rede isolada)
│   ├── docker-compose.yml     #   2 serviços (ft-server, ft-client) na sub-rede 172.20.0.0/24
│   ├── Dockerfile             #   Imagem Ubuntu 22.04 + python3, iproute2 (tc), tcpdump
│   └── .dockerignore
│
├── src/                       # Código-fonte do sistema cliente/servidor
│   ├── client.py              #   CLI do cliente: escolhe modo (tcp/rudp) e cenário
│   ├── server.py              #   Servidor concorrente: TCP (thread) + R-UDP (thread)
│   ├── tcp_transfer.py        #   Modo TCP + cabeçalho de aplicação "RDFT" de 256 B
│   ├── rudp.py                #   Modo R-UDP: Go-Back-N, ACKs, timeout, CRC por pacote
│   ├── checksum.py            #   MD5 do arquivo completo (prova de integridade)
│   └── logger.py              #   Coleta de métricas → JSONL (um registro por transferência)
│
├── scripts/                   # Orquestração dos experimentos e da inspeção
│   ├── apply_tc.sh            #   Aplica o cenário A/B/C com `tc netem`
│   ├── clear_tc.sh            #   Remove as regras de `tc` da interface
│   ├── capture_tcpdump.sh     #   Helper de baixo nível: inicia o tcpdump
│   ├── run_experiment.sh      #   Orquestra UMA execução: tc → tcpdump → transfer → teardown
│   ├── run_battery.sh         #   Roda a bateria inteira: N reps × 2 modos × 3 cenários
│   ├── export_pcap_to_csv.sh  #   Converte os .pcap em CSV por pacote + pcap_summary.csv
│   ├── extract_net_metrics.py #   Extrai o RTT medido dos pcaps → logs/csv/pcap_rtt.csv
│   ├── build_evidence.sh      #   Gera o pacote de evidências (pcaps + prova do X-Custom-Auth)
│   ├── run_tcp_test.sh        #   (stub) atalho histórico — superado por run_experiment.sh
│   └── run_rudp_test.sh       #   (stub) idem
│
├── notebooks/
│   └── main.ipynb             # Análise estatística completa (Plotly) — "artigo com código"
│
├── results/                   # Saídas versionadas da análise e as evidências
│   ├── figures/               #   Figuras 1–6 (HTML interativo; PNG quando rodado com kaleido)
│   ├── tables/
│   │   └── summary_stats.csv  #   Tabela consolidada de métricas (exportada pelo notebook)
│   └── evidence/              # ► PACOTE DE EVIDÊNCIAS (Validação TCPDump)
│       ├── README.md          #     Instruções específicas das evidências
│       ├── x_custom_auth_proof.txt  # Prova textual do X-Custom-Auth (hexdump + ASCII)
│       └── pcap/              #     6 capturas representativas (1 por modo × cenário)
│
├── paper/                     # Relatório SBC (artigo + fonte LaTeX)
│   ├── main.tex               #   Fonte do relatório (formato SBC)
│   ├── main.pdf               #   Relatório compilado (9 páginas, 8 figuras)
│   ├── references.bib         #   Referências bibliográficas
│   ├── sbc-template.sty …     #   Arquivos do template SBC (style.sty, sbc.bst)
│   └── imgs/                  #   Figuras (PNG) embutidas no relatório
│
├── logs/                      # GERADO em runtime (não versionado — ver .gitignore; disponível no GDrive da entrega)
│   ├── app/                   #   client_transfers.jsonl, server_transfers.jsonl, battery_*.log
│   ├── pcap/                  #   60 capturas da bateria completa (1 por execução)
│   └── csv/                   #   CSV por pacote + pcap_summary.csv
│
├── data/                      # GERADO/insumo (não versionado)
│   ├── input/test_1MB.bin     #   Arquivo de teste (1.048.576 B = 256 blocos de 4 KB)
│   └── received/              #   Arquivos recebidos pelo servidor
│
└── assignments/               # Listas de exercícios da disciplina (1.pdf, 2.pdf)
```

---

## 3. Descrição dos componentes

### 3.1 Código-fonte (`src/`)

| Arquivo | Responsabilidade |
|---------|------------------|
| **`client.py`** | Ponto de entrada do cliente. Lê `--mode {tcp,rudp}` e `--scenario {A,B,C}`, abre o socket apropriado e dispara o envio. Usa `CONNECT_TIMEOUT_S` (60 s) e `TCP_TIMEOUT_S` (600 s, configuráveis por env) — o timeout longo evita que execuções TCP lentas sob perda sejam descartadas e enviesem os resultados. |
| **`server.py`** | Servidor **concorrente**: uma thread escuta TCP (porta 5000) e outra escuta R-UDP (porta 5001), atendendo aos dois modos ao mesmo tempo. Grava os arquivos recebidos em `data/received/`. |
| **`tcp_transfer.py`** | Implementa o modo TCP e define o **cabeçalho de aplicação de 256 bytes** (magic `RDFT`, `file_size`, `transfer_id` (UUID), `scenario`, `mode` e o campo **`X-Custom-Auth`** de 226 B). É aqui que a string `matrícula + nome` é serializada no tráfego. |
| **`rudp.py`** | Núcleo do **R-UDP**. Cabeçalho próprio de 16 B (tipo de pacote, seq, ack, janela, `data_len`, **CRC-16**), *handshake* SYN/SYN-ACK, encerramento FIN/FIN-ACK, **Go-Back-N** com janela 8, `TIMEOUT_S = 0,5 s` e retransmissão da janela a partir do bloco perdido. Reutiliza o cabeçalho `RDFT` do `tcp_transfer.py` como metadado inicial — por isso o `X-Custom-Auth` também trafega no R-UDP. |
| **`checksum.py`** | Calcula o **MD5** do arquivo inteiro. Cliente e servidor o computam independentemente; a igualdade comprova a entrega íntegra. |
| **`logger.py`** | `TransferLogger`: coleta tempo, throughput, nº de blocos, retransmissões, ACKs, timeouts e checksum, e **anexa um registro JSON por transferência** (`client_transfers.jsonl` / `server_transfers.jsonl`). O `transfer_id` é compartilhado entre os dois lados, permitindo o *join* na análise. |

### 3.2 Ambiente (`docker/`)

- **`docker-compose.yml`** — cria a rede *bridge* isolada `172.20.0.0/24` com IPs fixos
  (`ft-server` = `172.20.0.10`, `ft-client` = `172.20.0.20`), concede `NET_ADMIN`/`NET_RAW`
  (necessários para `tc` e `tcpdump`) e monta `logs/` e `data/` como volumes compartilhados.
- **`Dockerfile`** — imagem **Ubuntu 22.04** com `python3`, `iproute2` (fornece o `tc`),
  `tcpdump` e utilitários de rede.

### 3.3 Orquestração e inspeção (`scripts/`)

- **`apply_tc.sh` / `clear_tc.sh`** — aplicam e removem o `tc netem` (a tradução direta dos
  cenários A/B/C em perda e atraso).
- **`run_experiment.sh`** — orquestra **uma** execução completa: aplica o `tc`, sobe o
  `tcpdump` (esperando o sinal real de "listening on", sem `sleep` fixo), executa a
  transferência e encerra o `tcpdump` com `SIGTERM` (para dar *flush* no buffer do pcap).
  A **perda fica no caminho de DADOS** (egress do cliente) e o **atraso nos dois sentidos**.
- **`run_battery.sh`** — repete o experimento para `N` repetições × 2 modos × 3 cenários,
  gravando um `.pcap` por execução e o transcript completo em `logs/app/battery_*.log`.
- **`export_pcap_to_csv.sh`** — converte cada `.pcap` em um CSV por pacote e gera o
  `pcap_summary.csv` agregado, base da **integração de dados** (app × rede).
- **`extract_net_metrics.py`** — lê os `.pcap` (host-side, via `tcpdump`) e extrai o
  **RTT medido** por execução em `logs/csv/pcap_rtt.csv` (insumo da Fig. 7 / Atrasos).
- **`build_evidence.sh`** — gera o pacote `results/evidence/` (ver §5).
- **`capture_tcpdump.sh`** — helper de baixo nível usado internamente.
- **`run_tcp_test.sh` / `run_rudp_test.sh`** — *stubs* históricos; o caminho oficial é o
  `run_experiment.sh`.

### 3.4 Análise (`notebooks/main.ipynb`)

Notebook em estilo **"artigo com código"**: cada seção explica o *porquê* do experimento,
*como ler* cada gráfico e *o que* concluir. Roda tanto localmente quanto no **Google
Colab**. Conteúdo:

- Carregamento e recorte da bateria; **validação de integridade** (checksums MD5).
- Tabela-resumo com **mediana + IC 95% por bootstrap** e **média ± desvio padrão**.
- **Fig. 1** Tempo de transferência · **Fig. 2** Throughput · **Fig. 3** Retransmissões
  do R-UDP · **Fig. 4** Overhead de dados · **Fig. 5** Pacotes na rede (`tcpdump`) ·
  **Fig. 6** Cross-validação de duração (app × rede) · **Fig. 7** Atrasos: RTT medido vs
  nominal · **Fig. 8** Perdas de pacotes: efetiva medida vs configurada vs teórica.
- Prova do `X-Custom-Auth` na captura e síntese dos achados.

---

## 4. Como reproduzir

```bash
# 1. Subir os containers (rebuild após alterar código em src/)
docker compose -f docker/docker-compose.yml -p redes_doutorado up -d --build

# 2. Rodar uma única execução (modo, cenário, repetição)
./scripts/run_experiment.sh tcp C 01
./scripts/run_experiment.sh rudp B 03

# 3. Rodar a bateria completa (ex.: 10 repetições)
./scripts/run_battery.sh 10

# 4. Exportar os pcaps para CSV (+ summary)
./scripts/export_pcap_to_csv.sh all

# 5. Executar a análise estatística
jupyter nbconvert --to notebook --execute --inplace notebooks/main.ipynb
#   (ou abrir notebooks/main.ipynb no Jupyter/Colab e "Executar tudo")

# 6. (Re)gerar o pacote de evidências
./scripts/build_evidence.sh
```

> **Análise no Google Colab.** Basta subir `notebooks/main.ipynb` + os dados
> (`logs/app/*.jsonl`, `logs/csv/pcap_summary.csv` e `logs/csv/pcap_rtt.csv`) e
> descomentar, na primeira célula,
> `!pip install -q plotly pandas numpy "kaleido==0.2.1"` (a versão 0.2.1 do kaleido é a
> compatível com o Plotly do Colab e permite exportar as figuras em PNG).

---

## 5. Evidências de tráfego e do `X-Custom-Auth` (Validação TCPDump)

O pacote em **`results/evidence/`** comprova (1) que o tráfego das transferências ocorreu
e (2) que o campo obrigatório **`X-Custom-Auth = matrícula + nome`** viajou nos pacotes,
**tanto no TCP quanto no R-UDP**. (Há um `README.md` próprio dentro da pasta para quando
ela for submetida isoladamente.)

### Conteúdo

```
results/evidence/
├── README.md                  # instruções específicas
├── x_custom_auth_proof.txt    # prova textual (tcpdump): a string no hexdump + ASCII
└── pcap/                       # 1 captura representativa por protocolo × cenário
    ├── capture_tcp_A_01.pcap   ├── capture_rudp_A_01.pcap
    ├── capture_tcp_B_01.pcap   ├── capture_rudp_B_01.pcap
    └── capture_tcp_C_01.pcap   └── capture_rudp_C_01.pcap
```

A bateria completa gera **60 pcaps** (em `logs/pcap/`); o pacote inclui um representativo
de cada cenário para ficar leve (~15 MB) e submissível.

### Prova textual (reprodução)

```bash
# a partir de qualquer pcap, a string aparece em claro após o magic "RDFT":
tcpdump -r results/evidence/pcap/capture_tcp_A_01.pcap  -A | grep -a 'ANTHONY'
tcpdump -r results/evidence/pcap/capture_rudp_A_01.pcap -X | grep -a -A4 RDFT
```

Trecho de `x_custom_auth_proof.txt` (hexdump do início do payload TCP):

```
0x0030:  2977 f920 5244 4654 0000 0000 0010 0000  )w..RDFT........
0x0050:  0000 3230 3236 3130 3131 3431 3020 414e  ..20261011410.AN
0x0060:  5448 4f4e 5920 4952 4c41 4e20 4d41 5251  THONY.IRLAN.MARQ
0x0070:  5545 5320 4c55 5a00 0000 0000 0000 0000  UES.LUZ.........
```

### Como gerar as capturas de tela no Wireshark

1. Abra um pcap: `wireshark results/evidence/pcap/capture_tcp_A_01.pcap`
2. No filtro de exibição, use:
   - `frame contains "ANTHONY"` — localiza o pacote que carrega o `X-Custom-Auth`.
   - `ip.src == 172.20.0.20` — isola o tráfego de dados cliente→servidor.
3. Selecione o pacote; no painel inferior (hex/ASCII) a string
   **`20261011410 ANTHONY IRLAN MARQUES LUZ`** aparece destacada. Capture a tela.
4. Repita para um pcap **R-UDP** (`capture_rudp_A_01.pcap`).

| Captura sugerida | Arquivo | O que mostra |
|------------------|---------|--------------|
| 1 | `capture_tcp_A_01.pcap`  | `X-Custom-Auth` no fluxo **TCP** |
| 2 | `capture_rudp_A_01.pcap` | `X-Custom-Auth` no fluxo **R-UDP** |
| 3 | `capture_rudp_C_01.pcap` | volume de pacotes sob perda (retransmissões do R-UDP) |

> Sem interface gráfica, a própria saída de `x_custom_auth_proof.txt` (ou dos comandos
> `tcpdump` acima) já serve como evidência.

---


## 6. Principais resultados (medianas, n = 10)

| | Tempo A / B / C (s) | Throughput A / B / C (KB/s) | Retransm. B / C | Overhead dados A / B / C |
|---|---|---|---|---|
| **TCP**  | 0,10 / 20,6 / 75,2 | 9.950 / 49,8 / 13,6 | — (kernel) | 1,0× (invisível à aplicação) |
| **R-UDP**| 0,68 / 51,9 / 144,9 | 1.516 / 19,7 / 7,1 | 90 / 240 | 1,0× / 3,8× / **8,4×** |

- **Integridade:** 60/60 transferências com `status=success` e **checksum MD5 idêntico**
  cliente↔servidor, nos dois protocolos e nos três cenários.
- **Cross-validação:** as durações app × `tcpdump` concordam (< 5%) nos cenários B e C;
  no cenário A o desvio é um **overhead fixo (~1,4 s)** da janela de captura, desprezível
  frente a transferências longas (detalhado na Fig. 6 do notebook).

---

## 7. Mapeamento com a rubrica (Fase 1 — `description.pdf`, §2.4)

| Critério | Descrição (enunciado) | Pontos | Onde foi atendido neste repositório |
|----------|-----------------------|:------:|-------------------------------------|
| **Ambiente Docker & TC** | Configuração de rede e scripts de simulação de falhas. | 1.0 | `docker/docker-compose.yml` (rede `172.20.0.0/24`, `NET_ADMIN`), `docker/Dockerfile`; `scripts/apply_tc.sh`, `clear_tc.sh`, `run_experiment.sh`, `run_battery.sh`. |
| **Protocolo R-UDP** | Eficácia do controle de erro e retransmissão sobre UDP. | 2.5 | `src/rudp.py` (Go-Back-N janela 8, seq/ACK, timeout/retransmissão, CRC-16) + `src/checksum.py`. **Eficácia comprovada:** integridade 60/60 e Figs. 3–4 do notebook (retransmissões/overhead crescendo com a perda). |
| **Validação TCPDump** | Capturas de tela e arquivos `.pcap` que comprovem o tráfego e o `X-Custom-Auth`. | 1.5 | `results/evidence/` (6 `.pcap` + `x_custom_auth_proof.txt` + roteiro de prints — §5); campo definido em `src/tcp_transfer.py`; captura via `scripts/capture_tcpdump.sh`. |
| **Análise Estatística** | Gráficos (Média/Desvio) TCP vs. R-UDP em cada cenário: **Vazão, Atrasos, Perdas, Retransmissões**. | 2.0 | `notebooks/main.ipynb`, cobrindo as quatro métricas do enunciado: **Vazão** → Fig. 2; **Atrasos** → Fig. 7 (RTT medido vs nominal); **Perdas** → Fig. 8 (perda efetiva vs configurada); **Retransmissões** → Figs. 3–4. Mais Fig. 1 (tempo) e a tabela §4 (mediana, IC 95% e **média ± DP**). Saídas em `results/figures/` e `results/tables/summary_stats.csv`. |
| **Integração de Dados** | Comparação entre o que a aplicação mediu e o que o TCPDump registrou. | 1.0 | `notebooks/main.ipynb` §5 — Fig. 5 (pacotes na rede) e Fig. 6 (duração app × rede) + tabela de cross-validação; pipeline `scripts/export_pcap_to_csv.sh` → `pcap_summary.csv`. |
| **Relatório (SBC)** | Documentação técnica, discussão e respostas às perguntas. | 1.0 | ✅ [`paper/main.pdf`](paper/main.pdf) — artigo no formato SBC (9 páginas, com as 8 figuras e a tabela de cenários), cobrindo metodologia, resultados, respostas às perguntas e trabalhos futuros. Fonte em `paper/main.tex`, referências em `paper/references.bib`. |
| **Vídeo Demonstrativo** | Explicação da implementação e demonstração dos testes de perda. | 1.0 | ✅ Disponível em **[\<inserir link do vídeo\>](https://drive.google.com/<inserir-link-do-video>)**. Conteúdo: implementação (`src/`) → bateria (`scripts/`) → retransmissões do R-UDP e `X-Custom-Auth` no `.pcap` (§5). |

**Total da Fase 1: 10 pontos.** Todos os critérios atendidos e evidenciados: ambiente
Docker/TC, protocolo R-UDP, validação TCPDump, análise estatística e integração de dados
(itens técnicos, **8,0 pts**), além do **Relatório SBC** ([`paper/main.pdf`](paper/main.pdf))
e do **Vídeo demonstrativo** (**2,0 pts**).

---

## 8. Roadmap — Fase 2 (entrega 25/06/2026)

Simulador de eventos discretos em **SimPy** espelhando o R-UDP, com as 10 tarefas de
validação do enunciado (modelagem de atraso/perda, curva de vazão, sensibilidade da
janela, validação de RTT, convergência estatística com IC 95% sobre ≥ 30 execuções) e a
análise comparativa **real × simulado**. Diretório `simulation/` a ser criado.
