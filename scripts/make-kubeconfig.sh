#!/usr/bin/env bash
# Собирает kubeconfig для сервисного аккаунта gha-deployer и печатает его в base64
# (значение для секрета KUBECONFIG_B64 в GitHub environment "lab").
#
#   ./scripts/make-kubeconfig.sh https://203.0.113.10:6443 > /dev/null   # проверка
#   ./scripts/make-kubeconfig.sh https://203.0.113.10:6443 | gh secret set KUBECONFIG_B64 --env lab
set -euo pipefail

SERVER="${1:?usage: $0 https://<api-host>:6443}"
NS=ci
SA=gha-deployer

TOKEN=$(kubectl -n "$NS" get secret "${SA}-token" -o jsonpath='{.data.token}' | base64 -d)
CA=$(kubectl -n "$NS" get secret "${SA}-token" -o jsonpath='{.data.ca\.crt}')

cat <<EOF | base64 | tr -d '\n'
apiVersion: v1
kind: Config
clusters:
  - name: lab
    cluster:
      server: ${SERVER}
      certificate-authority-data: ${CA}
users:
  - name: ${SA}
    user:
      token: ${TOKEN}
contexts:
  - name: lab
    context:
      cluster: lab
      user: ${SA}
      namespace: shop
current-context: lab
EOF
echo
