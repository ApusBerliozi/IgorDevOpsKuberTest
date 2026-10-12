#!/usr/bin/env bash
# Smoke-тест изнутри кластера: ходим в API через Service, как ходил бы любой клиент.
# Создаём заказ и ждём, пока воркер его обработает.
set -euo pipefail

NS="${NS:-shop}"
POD="smoke-$(date +%s)"

# shellcheck disable=SC2016  # скрипт намеренно в одинарных кавычках — выполняется внутри пода

kubectl -n "$NS" run "$POD" --rm -i --restart=Never --quiet \
  --image=curlimages/curl:8.11.1 --command -- sh -ec '
    base=http://orders-api
    echo "== GET /healthz";  curl -fsS --max-time 5 "$base/healthz"; echo
    echo "== GET /readyz";   curl -fsS --max-time 5 "$base/readyz";  echo
    echo "== POST /orders"
    resp=$(curl -fsS --max-time 5 -X POST "$base/orders" \
             -H "content-type: application/json" -d "{\"sku\":\"SKU-00042\",\"qty\":1}")
    echo "$resp"
    id=$(echo "$resp" | sed -n "s/.*\"id\":\"\([a-f0-9]*\)\".*/\1/p")
    [ -n "$id" ] || { echo "no order id in response"; exit 1; }
    echo "== waiting for worker to process order $id"
    for i in $(seq 1 30); do
      status=$(curl -fsS --max-time 5 "$base/orders/$id" | sed -n "s/.*\"status\":\"\([a-z]*\)\".*/\1/p")
      [ "$status" = "processed" ] && { echo "order $id processed"; exit 0; }
      sleep 1
    done
    echo "order $id is still \"$status\" after 30s"; exit 1
  '
