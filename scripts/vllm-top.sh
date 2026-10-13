#!/usr/bin/env bash
# vllm-top — podgląd pracy modelu vLLM na żywo w jednej linii terminala.
#
# Co pokazuje (odczyt /metrics co INTERWAŁ sekund):
#   w toku (+kolejka) · generowanie i prefill [tok/s] · trafienia prefix cache od startu skryptu
#   · zajęcie KV cache · tokeny wygenerowane od startu · odpowiedzi ucięte na limicie max_tokens
#   (od startu skryptu / od startu kontenera). Ucięcie w danym odczycie oznacza „← ucięta odpowiedź”.
#
# Użycie:
#   scripts/vllm-top.sh [PORT] [INTERWAŁ] [--log]
#   scripts/vllm-top.sh               # :8000 co 2 s, jedna odświeżana linia
#   scripts/vllm-top.sh 8002 5        # inny model, co 5 s
#   scripts/vllm-top.sh 8000 2 --log  # nowa linia przy każdym odczycie (np. > plik.log)
# Na Macu przez tunel `ssh -N spark`; na Sparku bezpośrednio (`make top P=8000`).
# Tylko odczyt; zależności: bash, curl, awk. Ctrl+C kończy.

set -u
port="${1:-8000}"
every="${2:-2}"
mode="${3:-}"
base="http://localhost:${port}"

model=$(curl -s -m 3 "${base}/v1/models" | grep -o '"id": *"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"$/\1/')
echo "vllm-top · ${model:-?} · ${base} · co ${every} s (Ctrl+C kończy)"

trap 'echo; exit 0' INT TERM

# wartości z poprzedniego odczytu i z pierwszego odczytu (punkt odniesienia)
p_t="" p_g="" p_p="" p_h="" p_l=""
s_g="" s_p="" s_h="" s_l=""

while true; do
  now=$(date +%s)
  m=$(curl -s -m 3 "${base}/metrics")
  if [ -z "$m" ]; then
    line="$(date +%T)  brak połączenia z ${base} — tunel otwarty? model działa?"
  else
    # run wait gen prompt hits kv length finished
    read -r run wait gen pr hit kv len fin <<EOF
$(echo "$m" | awk '
  /^vllm:num_requests_running[{ ]/   {run+=$NF}
  /^vllm:num_requests_waiting[{ ]/   {wait+=$NF}
  /^vllm:generation_tokens_total[{ ]/{gen+=$NF}
  /^vllm:prompt_tokens_total[{ ]/    {pr+=$NF}
  /^vllm:prefix_cache_hits_total[{ ]/{hit+=$NF}
  /^vllm:kv_cache_usage_perc[{ ]/    {kv+=$NF}
  /^vllm:request_success_total[{ ]/  {fin+=$NF; if ($0 ~ /finished_reason="length"/) len+=$NF}
  END {printf "%d %d %.0f %.0f %.0f %.4f %d %d\n", run, wait, gen, pr, hit, kv, len, fin}')
EOF
    [ -z "$s_g" ] && { s_g=$gen; s_p=$pr; s_h=$hit; s_l=$len; }
    if [ -n "$p_t" ] && [ "$now" -gt "$p_t" ]; then
      line=$(awk -v t="$(date +%T)" -v dt=$((now - p_t)) -v run="$run" -v wait="$wait" \
        -v g="$gen" -v pg="$p_g" -v sg="$s_g" -v p="$pr" -v pp="$p_p" -v sp="$s_p" \
        -v h="$hit" -v ph="$p_h" -v sh="$s_h" -v kv="$kv" -v l="$len" -v pl="$p_l" -v sl="$s_l" 'BEGIN{
          dp=(p-pp)-(h-ph); if (dp<0) dp=0
          cache=(p-sp)>0 ? sprintf("%3.0f%%", 100*(h-sh)/(p-sp)) : "  –"
          s=sprintf("%s  w toku %d (+%d)  gen %5.1f tok/s  prefill %6.0f tok/s  cache %s  KV %4.1f%%  wygen. %d  ucięte %d/%d",
            t, run, wait, (g-pg)/dt, dp/dt, cache, 100*kv, g-sg, l-sl, l)
          if (l>pl) s=s "  ← ucięta odpowiedź"
          print s}')
    else
      line="$(date +%T)  w toku ${run} (+${wait})  — pierwszy odczyt, prędkości od następnego"
    fi
    p_t=$now p_g=$gen p_p=$pr p_h=$hit p_l=$len
  fi
  if [ "$mode" = "--log" ]; then printf '%s\n' "$line"; else printf '\r\033[K%s' "$line"; fi
  sleep "$every"
done
