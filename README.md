# redes-de-computadores-dccmapi
Repository for the Computer Networks graduate course.

## Assignments

`att1.pdf` covers the first assignment: a solved exercise list on Chapter 1 of *Computer Networks* by Andrew S. Tanenbaum.

`att2.pdf` covers the second assignment: a solved exercise list on Chapter 2 of the same book.

## Computer Networks Course Project (2026-1)

This is the final project for the Computer Networks course. The full problem statement and guidelines are available in `description.pdf`.

### Phase 1 — File Transfer System over TCP and Reliable UDP

The goal of this phase is to design, implement, and evaluate a Client/Server file transfer system in Python, running inside containers. The system supports two transport modes — native TCP and a custom Reliable UDP (R-UDP) — allowing a direct performance comparison between a standard protocol and a hand-crafted one under controlled network degradation.

#### The Code

> **Note on Traffic Direction:** For the purpose of the cross-validation in Phase 1, the transfer architecture assumes a strict unidirectional flow: the Client always acts as the sender (uploading the file) and the Server always acts as the receiver. Throughput calculations and logs are designed around this assumption, meaning the Client records transmission metrics (`bytes_sent / time`) and the Server records reception metrics (`bytes_received / time`).

### Experiment

- Arquivo: `test_1MB.bin` (1 MB fixo) — default em `client.py`
- Repetições: 10 por combinação (modo × cenário)
- Modos: TCP nativo e R-UDP (Go-Back-N, janela 8)
- Cenários: A (0% loss / 10 ms), B (10% loss / 50 ms), C (20% loss / 100 ms)
- Total de transferências: 10 × 2 × 3 = 60 runs
- Pcaps: 60 arquivos individuais (`capture_<modo>_<cenário>_01.pcap` … `_10.pcap`)

**Emulação de rede (`tc netem`).** A perda é aplicada no *egress* do **cliente**
(caminho de DADOS, cliente→servidor) e o **atraso** em ambos os sentidos
(`RTT ≈ 2 × atraso`). Assim os pacotes de dados sofrem perda — exercitando a
retransmissão do R-UDP — sem submeter o TCP às tempestades de RTO da perda
bidirecional de 20% (que levava uma transferência de 1 MB a ~5 min). A análise
estatística está em `notebooks/main.ipynb`.