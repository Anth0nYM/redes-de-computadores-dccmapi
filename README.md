# Transferência de Arquivos sobre TCP e R-UDP — Projeto de Redes de Computadores (2026-1)

**PPGCC/UFPI — Campus Senador Helvídio Nunes de Barros**
Autor: **Anthony Irlan Marques Luz** · Matrícula **20261011410**
Repositório: [github.com/Anth0nYM/redes-de-computadores-dccmapi](https://github.com/Anth0nYM/redes-de-computadores-dccmapi)
Enunciado completo: [`description.pdf`](description.pdf)

---

## Visão geral

Este repositório cobre as **duas fases** do projeto de Redes de Computadores:

| Fase | Objetivo | Status |
|------|----------|--------|
| **Fase 1** | Sistema cliente/servidor R-UDP GBN sobre Docker + `tc/netem`; análise estatística real | ✅ Concluída |
| **Fase 2** | Modelo estocástico de eventos discretos (SimPy) espelhando o R-UDP real; 10 tarefas de validação | ✅ Concluída |

### O protocolo R-UDP Go-Back-N

O sistema implementa um protocolo confiável de transferência de arquivos **em espaço de usuário sobre UDP**, com:
- Janela deslizante **Go-Back-N** (N = 8)
- Cabeçalho próprio de 16 bytes (tipo, seq, ack, janela, comprimento, CRC-16)
- *Handshake* SYN/SYN-ACK e encerramento FIN/FIN-ACK
- Timeout fixo de 0,5 s com retransmissão a partir da base da janela
- Verificação de integridade MD5 fim-a-fim

### Os três cenários de rede

| Cenário | Perda bruta | Atraso (one-way) | RTT ≈ | Perda efetiva por bloco¹ |
|---------|-------------|------------------|--------|--------------------------|
| **A** | 0%  | 10 ms  | 20 ms  | 0,0% |
| **B** | 10% | 50 ms  | 100 ms | 27,1% |
| **C** | 20% | 100 ms | 200 ms | 48,8% |

¹ Cada datagrama DATA (4 112 B) é fragmentado em 3 pacotes IP pelo kernel; `p_ef = 1 − (1−p)³`.

---

## Fase 1 — Sistema Real

### Entregáveis

| Entregável | Onde está |
|------------|-----------|
| 💻 **Código-fonte** | `src/` — cliente, servidor, R-UDP, TCP, checksum, logger |
| 📓 **Análise + Colab** | `notebooks/main.ipynb` (8 figuras Plotly, executável no Google Colab) |
| 📄 **Relatório SBC** | [`paper/main.pdf`](paper/main.pdf) (fonte em `paper/main.tex`) |
| 🎥 **Vídeo demonstrativo** | **[youtu.be/3VaU2eYaHXo](https://youtu.be/3VaU2eYaHXo)** |
| 🔎 **Evidências (pcap + X-Custom-Auth)** | `results/evidence/` |
| 🗂️ **Logs de captura (PCAP/CSV)** | Não versionados (~155 MB) — **[pasta `logs/` no Google Drive](https://drive.google.com/drive/folders/12sBrG_SSxHayG23rZKkMgdw7EalQI_ml?usp=sharing)** |

### Principais resultados (medianas, n = 10)

| | Tempo A / B / C (s) | Throughput A / B / C (KB/s) | Retransm. B / C | Overhead dados A / B / C |
|---|---|---|---|---|
| **TCP**  | 0,10 / 20,6 / 75,2 | 9 950 / 49,8 / 13,6 | — (kernel) | 1,0× |
| **R-UDP**| 0,68 / 51,9 / 144,9 | 1 516 / 19,7 / 7,1 | 90 / 240 | 1,0× / 3,8× / **8,4×** |

- **Integridade:** 60/60 transferências com `status=success` e checksum MD5 idêntico.
- **Cross-validação:** durações app × `tcpdump` concordam < 5% nos cenários B e C.

### Mapeamento com a rubrica (Fase 1 — `description.pdf`, §2.4)

| Critério | Pts | Onde está |
|----------|:---:|-----------|
| **Ambiente Docker & TC** | 1,0 | `docker/`, `scripts/apply_tc.sh`, `run_experiment.sh`, `run_battery.sh` |
| **Protocolo R-UDP** | 2,5 | `src/rudp.py` (GBN janela 8, CRC-16, timeout/retx) + `src/checksum.py` |
| **Validação TCPDump** | 1,5 | `results/evidence/` (6 pcap + `x_custom_auth_proof.txt`) |
| **Análise Estatística** | 2,0 | `notebooks/main.ipynb` — Figs. 1–8 (vazão, atrasos, perdas, retransmissões) |
| **Integração de Dados** | 1,0 | `notebooks/main.ipynb` §5 — Fig. 5–6, `pcap_summary.csv` |
| **Relatório SBC** | 1,0 | [`paper/main.pdf`](paper/main.pdf) (9 pág., 8 figuras) |
| **Vídeo** | 1,0 | [youtu.be/3VaU2eYaHXo](https://youtu.be/3VaU2eYaHXo) |
| **Total** | **10,0** | |

---

## Fase 2 — Modelagem Estocástica (SimPy)

### O que foi feito

A Fase 2 constrói e valida um **modelo de eventos discretos em SimPy** que espelha o R-UDP real da Fase 1. O modelo é parametrizado apenas por grandezas físicas observáveis — sem fatores de ajuste. Ao longo de uma faixa de **200× nos tempos de transferência** (0,67 s a 145 s), o simulador reproduz as medições reais com **erro relativo entre 1,0% e 7,4%**.

**Canal simulado:**
- Atraso unidirecional `D ~ N(μ, σ²)` com ordem preservada no enlace
- Perda Bernoulli por bloco com probabilidade `p_ef = 1 − (1−p)³`
- ACKs entregues com confiabilidade (simplificação discutida no paper)

**Motor GBN orientado a eventos:**
- Três classes de eventos: chegada de DATA, chegada de ACK, disparo de timer
- Sem aproximação por rodadas síncronas — tempo e retransmissões emergem da dinâmica
- Suporte a enlace gargalo (`L/B` entre transmissões) para varredura de janela

### Entregáveis

| Entregável | Onde está |
|------------|-----------|
| 💻 **Simulador** | `src/sim/` — `channel.py`, `gbn.py`, `validate.py`, `converge.py`, `throughput.py`, `window_sweep.py`, `jitter_sweep.py`, `stress.py`, `efficiency.py` |
| 🧪 **Testes TDD** | `tests/` — 51 testes unitários; `pytest -q` → todos verdes |
| 📓 **Notebook Fase 2** | `notebooks/fase2_simpy.ipynb` (8 figuras Plotly; bootstrap Colab; executa em ~12 s) |
| 📄 **Artigo SBC Fase 2** | [`paper/fase2.pdf`](paper/fase2.pdf) (11 pág., 6 figuras, 4 tabelas; fonte em `paper/fase2.tex`) |
| 📊 **Slides** | [`paper/fase2_slides.pptx`](paper/fase2_slides.pptx) (36 slides para vídeo de 30 min) |
| 🎥 **Vídeo** | **[youtube.com/PLACEHOLDER-VIDEO](https://youtube.com/PLACEHOLDER-VIDEO)** |

### As 10 tarefas de validação

| # | Tarefa | Resultado | Referência analítica |
|---|--------|-----------|----------------------|
| 1 | Modelagem de atraso Normal | RTT simulado = 2μ ✓ | Por construção |
| 2 | Perda Bernoulli vs. `tc/netem` | taxa empírica ≈ p_ef ✓ | `p_ef = 1−(1−p)³` |
| 3 | Timeout e retransmissão | 0 retx sem perda; contagens ≈ real ✓ | GBN canônico |
| 4 | Curva de vazão 1–100 MB | Cen. A satura em 97% do teto; B limitado por perda ✓ | `S_max = N·L/RTT` |
| 5 | Sensibilidade à janela N | joelho em N = 12; satura em ≈ 1 986 KB/s ✓ | `N* = BDP/L` = 10 |
| 6 | Validação de RTT | mapeamento direto; validado por testes unitários ✓ | `RTT = 2μ` |
| 7 | Impacto do jitter | dispersão e média crescem monotônico com σ ✓ | `E[max]` cresce com σ |
| 8 | Estresse 25% de perda bruta | previsão 213 s (+47% sobre Cen. C) ✓ | p_ef = 57,8% |
| 9 | Eficiência DADOS/ACK | A 1,00 / B 1,38 / C 1,96 ✓ | `1/(1−p_ef)` |
| 10 | Convergência IC 95% bootstrap | C coberto; A e B com viés sistemático < 7,5% ✓ | Bootstrap percentílico |

### Calibração (30 repetições, semente fixa)

| Cenário | Real (s) | Simulado (s) | IC 95% (s) | Erro | Real no IC? |
|---------|----------|--------------|------------|------|-------------|
| A | 0,676 | 0,669 | [0,668 ; 0,671] | −1,0% | não |
| B | 53,165 | 57,088 | [55,197 ; 58,942] | +7,4% | não |
| C | 144,613 | 148,788 | [144,046 ; 153,388] | +2,9% | **sim** |

### Como reproduzir (Fase 2)

```bash
# Instalar dependências (SimPy, pytest, plotly, scipy, numpy)
pip install -r requirements.txt

# Rodar todos os testes (51 testes unitários)
pytest -q

# Calibração contra dados reais
python -m src.sim.validate

# Convergência estatística (IC 95% bootstrap)
python -m src.sim.converge

# Curva de vazão 1–100 MB
python -m src.sim.throughput

# Sensibilidade da janela (com enlace gargalo)
python -m src.sim.window_sweep

# Impacto do jitter
python -m src.sim.jitter_sweep

# Cenário de estresse 25% de perda bruta
python -m src.sim.stress

# Eficiência DADOS/ACK
python -m src.sim.efficiency

# Notebook completo (Fase 2)
jupyter nbconvert --to notebook --execute --inplace notebooks/fase2_simpy.ipynb
```

> **Google Colab.** Abra `notebooks/fase2_simpy.ipynb` — a primeira célula clona o repositório e instala as dependências automaticamente.

---

## Estrutura do repositório

```
redes-de-computadores-dccmapi/
├── description.pdf            # Enunciado oficial do projeto
├── README.md                  # Este arquivo
├── requirements.txt           # Dependências Python (scapy, simpy, pytest, plotly…)
├── .gitignore / .dockerignore
│
├── docker/                    # Ambiente de execução (Fase 1)
│   ├── docker-compose.yml     #   2 containers Ubuntu + rede bridge 172.20.0.0/24
│   ├── Dockerfile             #   Ubuntu 22.04 + python3, iproute2 (tc), tcpdump
│   └── .dockerignore
│
├── src/                       # Código-fonte
│   ├── client.py              #   CLI do cliente (tcp/rudp × cenário)
│   ├── server.py              #   Servidor concorrente TCP + R-UDP
│   ├── tcp_transfer.py        #   Modo TCP + cabeçalho RDFT (X-Custom-Auth)
│   ├── rudp.py                #   Modo R-UDP: GBN, ACKs, timeout, CRC-16
│   ├── checksum.py            #   MD5 do arquivo completo
│   ├── logger.py              #   Coleta de métricas → JSONL
│   └── sim/                   #   ► FASE 2: Simulador estocástico SimPy
│       ├── channel.py         #     Canal: atraso Normal + perda Bernoulli
│       ├── gbn.py             #     Motor Go-Back-N orientado a eventos
│       ├── validate.py        #     Calibração A/B/C vs. dados reais
│       ├── converge.py        #     Convergência IC 95% bootstrap (≥ 30 reps)
│       ├── throughput.py      #     Curva de vazão 1–100 MB (D4)
│       ├── window_sweep.py    #     Sensibilidade da janela N (D5)
│       ├── jitter_sweep.py    #     Impacto do jitter σ (D7)
│       ├── stress.py          #     Estresse 25% de perda bruta (D8)
│       └── efficiency.py      #     Eficiência DADOS/ACK (D9)
│
├── tests/                     # ► FASE 2: Testes TDD (51 testes unitários)
│   ├── test_channel.py        #   Canal: atraso≈μ, perda≈p_ef
│   ├── test_gbn.py            #   Motor: 256 blocos íntegros, 0 retx sem perda
│   ├── test_validate.py       #   Calibração dentro da faixa de erro esperada
│   ├── test_converge.py       #   IC 95% gerado; largura razoável
│   ├── test_throughput.py     #   A satura próximo do teto; B colapsa
│   ├── test_window.py         #   Joelho próximo de N* = BDP/L
│   ├── test_jitter.py         #   Dispersão monotônica com σ
│   ├── test_stress.py         #   Previsão coerente com cenário C
│   └── test_efficiency.py     #   Razão DADOS/ACK ≈ 1/(1−p_ef)
│
├── scripts/                   # Orquestração dos experimentos (Fase 1)
│   ├── apply_tc.sh / clear_tc.sh
│   ├── run_experiment.sh      #   Uma execução completa: tc → tcpdump → transfer
│   ├── run_battery.sh         #   Bateria N reps × 2 modos × 3 cenários
│   ├── export_pcap_to_csv.sh
│   ├── extract_net_metrics.py
│   └── build_evidence.sh
│
├── notebooks/
│   ├── main.ipynb             # Análise estatística Fase 1 (8 figuras Plotly)
│   └── fase2_simpy.ipynb      # ► FASE 2: integração D3–D9 (8 figuras, ~12 s)
│
├── paper/
│   ├── main.tex / main.pdf    # Relatório SBC Fase 1 (9 pág.)
│   ├── fase2.tex / fase2.pdf  # ► FASE 2: Artigo SBC standalone (11 pág.)
│   ├── fase2_slides.pptx      # ► FASE 2: Slides para vídeo (36 slides, 30 min)
│   ├── references.bib
│   ├── sbc-template.sty / sbc.bst
│   └── imgs/                  # Figuras fase1_* e fase2_* (PNG)
│
├── results/
│   ├── figures/               # Figuras HTML/PNG da Fase 1
│   ├── tables/summary_stats.csv
│   └── evidence/              # Pacote de evidências (pcap + X-Custom-Auth)
│
├── logs/                      # GERADO em runtime (não versionado; GDrive)
│   ├── app/                   #   *.jsonl, battery_*.log
│   ├── pcap/                  #   60 capturas da bateria
│   └── csv/                   #   CSV por pacote + pcap_summary.csv
│
├── data/                      # GERADO/insumo (não versionado)
│   ├── input/test_1MB.bin     #   1 MiB = 256 blocos de 4 KB
│   └── received/
│
└── assignments/               # Listas de exercícios da disciplina
```

---

## Como reproduzir (Fase 1)

```bash
# 1. Subir os containers
docker compose -f docker/docker-compose.yml -p redes_doutorado up -d --build

# 2. Uma execução (modo, cenário, repetição)
./scripts/run_experiment.sh tcp C 01
./scripts/run_experiment.sh rudp B 03

# 3. Bateria completa (ex.: 10 repetições)
./scripts/run_battery.sh 10

# 4. Exportar pcaps para CSV
./scripts/export_pcap_to_csv.sh all

# 5. Análise estatística
jupyter nbconvert --to notebook --execute --inplace notebooks/main.ipynb

# 6. Pacote de evidências
./scripts/build_evidence.sh
```

> **Análise no Google Colab.** Suba `notebooks/main.ipynb` + os dados em `logs/` e descomente `!pip install -q plotly pandas numpy "kaleido==0.2.1"` na primeira célula.

---

## Evidências de tráfego e do `X-Custom-Auth` (Fase 1)

O pacote em **`results/evidence/`** comprova que o campo `X-Custom-Auth = matrícula + nome` trafegou nos pacotes em **TCP e R-UDP**.

```bash
# A string aparece em claro após o magic "RDFT":
tcpdump -r results/evidence/pcap/capture_tcp_A_01.pcap  -A | grep -a 'ANTHONY'
tcpdump -r results/evidence/pcap/capture_rudp_A_01.pcap -X | grep -a -A4 RDFT
```

Trecho de `x_custom_auth_proof.txt`:

```
0x0030:  2977 f920 5244 4654 0000 0000 0010 0000  )w..RDFT........
0x0050:  0000 3230 3236 3130 3131 3431 3020 414e  ..20261011410.AN
0x0060:  5448 4f4e 5920 4952 4c41 4e20 4d41 5251  THONY.IRLAN.MARQ
0x0070:  5545 5320 4c55 5a00 0000 0000 0000 0000  UES.LUZ.........
```
