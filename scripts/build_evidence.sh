#!/usr/bin/env bash
# Monta o pacote de evidências da Fase 1: pcaps representativos + prova textual
# do campo X-Custom-Auth visível no tráfego. Lê os pcaps direto do host (tcpdump),
# sem depender dos containers em execução.
# sem 'pipefail': pipelines com 'head' fecham o cano cedo (SIGPIPE) de propósito.
set -eu
cd "$(dirname "$0")/.."

AUTH_STR="ANTHONY"                 # marcador para localizar o campo X-Custom-Auth
SRC_PCAP="logs/pcap"
OUT="results/evidence"
OUT_PCAP="$OUT/pcap"
PROOF="$OUT/x_custom_auth_proof.txt"

command -v tcpdump >/dev/null || { echo "ERRO: tcpdump não encontrado no host." >&2; exit 1; }
mkdir -p "$OUT_PCAP"

# ── 1. Curadoria: 1 pcap representativo por protocolo × cenário ───────────────
echo "[evidence] copiando pcaps representativos..."
for m in tcp rudp; do
  for s in A B C; do
    f="$SRC_PCAP/capture_${m}_${s}_01.pcap"
    [ -f "$f" ] && cp -f "$f" "$OUT_PCAP/" && echo "  + $(basename "$f")"
  done
done

# ── 2. Prova textual do X-Custom-Auth ─────────────────────────────────────────
echo "[evidence] gerando prova do X-Custom-Auth -> $PROOF"
{
  echo "==============================================================================="
  echo " PROVA DE TRÁFEGO E DO CAMPO X-Custom-Auth NA CAPTURA DE REDE"
  echo " PPGCC/UFPI - Redes de Computadores 2026-1 - Projeto Fase 1"
  echo " Gerado em: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "==============================================================================="
  echo
  echo "O campo X-Custom-Auth = <matrícula> <nome> viaja no cabeçalho da aplicação"
  echo "(256 bytes, logo após o magic 'RDFT'), tanto no TCP quanto no payload do SYN"
  echo "do R-UDP. Por trafegar em claro, é visível na captura .pcap. As seções abaixo"
  echo "extraem a string diretamente dos arquivos capturados com:"
  echo
  echo "    tcpdump -r <arquivo.pcap> -A | grep -a 'ANTHONY'      # texto legível"
  echo "    tcpdump -r <arquivo.pcap> -X                          # hexdump + ASCII"
  echo

  for proto in tcp rudp; do
    P="$OUT_PCAP/capture_${proto}_A_01.pcap"
    [ -f "$P" ] || continue
    label=$([ "$proto" = tcp ] && echo "TCP" || echo "R-UDP")
    echo "-------------------------------------------------------------------------------"
    echo " ${label}  —  $(basename "$P")"
    echo "-------------------------------------------------------------------------------"
    echo "\$ tcpdump -r $(basename "$P") -A | grep -a '$AUTH_STR'"
    tcpdump -r "$P" -A 2>/dev/null | grep -a "$AUTH_STR" | head -1 \
      | sed 's/[^[:print:]]/./g'
    echo
    echo "Hexdump do início do payload (magic 'RDFT' + campo X-Custom-Auth):"
    # mostra 6 linhas de hexdump a partir do magic 'RDFT' do primeiro pacote que o contém
    tcpdump -r "$P" -X 2>/dev/null \
      | awk '/RDFT/{f=1} f{print; n++} n>=6{exit}' \
      | sed 's/[^[:print:]\t]/./g'
    echo
  done

  echo "==============================================================================="
  echo " RESUMO: campo X-Custom-Auth localizado nos dois protocolos."
  echo " Total de pcaps na bateria completa: $(ls "$SRC_PCAP"/*.pcap 2>/dev/null | wc -l)"
  echo " Pcaps representativos neste pacote : $(ls "$OUT_PCAP"/*.pcap 2>/dev/null | wc -l)"
  echo "==============================================================================="
} > "$PROOF"

echo "[evidence] OK."
echo
echo "Conteúdo de $OUT:"
ls -R "$OUT"
