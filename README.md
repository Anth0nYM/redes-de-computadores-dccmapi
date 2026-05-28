# redes-de-computadores-dccmapi
Repository for the Computer Networks graduate course.

## Assignments

`att1.pdf` covers the first assignment: a solved exercise list on Chapter 1 of *Computer Networks* by Andrew S. Tanenbaum.

`att2.pdf` covers the second assignment: a solved exercise list on Chapter 2 of the same book.

## Computer Networks Course Project (2026-1)

This is the final project for the Computer Networks course. The full problem statement and guidelines are available in `roteiro.pdf`.

### Phase 1 — File Transfer System over TCP and Reliable UDP

The goal of this phase is to design, implement, and evaluate a Client/Server file transfer system in Python, running inside containers. The system supports two transport modes — native TCP and a custom Reliable UDP (R-UDP) — allowing a direct performance comparison between a standard protocol and a hand-crafted one under controlled network degradation.

#### The Code

> **Note on Traffic Direction:** For the purpose of the cross-validation in Phase 1, the transfer architecture assumes a strict unidirectional flow: the Client always acts as the sender (uploading the file) and the Server always acts as the receiver. Throughput calculations and logs are designed around this assumption, meaning the Client records transmission metrics (`bytes_sent / time`) and the Server records reception metrics (`bytes_received / time`).

### Experiment

- Arquivo: test_1MB.bin (1 MB fixo) — hardcoded como default em client.py
- Repetições: 30 por combinação
- Modos: TCP e R-UDP
- Cenários: A (0% loss / 10ms), B (10% loss / 50ms), C (20% loss / 100ms)
- Total de transferências: 30 × 2 × 3 = 180 runs
- Pcaps: 180 arquivos individuais (capture_tcp_A_01.pcap … capture_rudp_C_30.pcap)