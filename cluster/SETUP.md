# Подготовка стенда (для наставника)

## 1. Кластер

На сервере нужны Docker, [kind](https://kind.sigs.k8s.io/) и kubectl.

```bash
kind create cluster --name lab --config cluster/kind-config.yaml
kubectl get nodes --show-labels     # 1 control-plane + 3 worker
kubectl apply -f cluster/bootstrap.yaml
```

Альтернатива — k3d (`k3d cluster create lab --agents 3`), тогда метки нод
из `kind-config.yaml` нужно повесить руками через `kubectl label node`.

## 2. Как GitHub Actions попадёт в кластер

**Вариант A (рекомендую): self-hosted runner на этом же сервере.**
API-сервер не торчит наружу. Установи runner (Settings → Actions → Runners),
затем Settings → Secrets and variables → Actions → *Variables*:
`DEPLOY_RUNNER = self-hosted`. Kubeconfig собирай с адресом `https://127.0.0.1:6443`.
Runner'у нужны `curl`, `tar`, `base64`.

**Вариант B: публичный API.** Пропиши IP сервера в `certSANs` в
`kind-config.yaml` (до создания кластера), открой 6443 только для
[диапазонов GitHub](https://api.github.com/meta) или через VPN.

## 3. Секрет для деплоя

Settings → Environments → создай `lab`, затем:

```bash
./scripts/make-kubeconfig.sh https://127.0.0.1:6443 | gh secret set KUBECONFIG_B64 --env lab
```

Токен даёт права `edit` только в `shop` и `data`.

## 4. Видимость образа

Кластер тянет образ из GHCR без авторизации, поэтому пакет должен быть
**публичным**. Пакет появляется после первого push, так что:

1. Запушь тег рабочего релиза: `git push origin v0.9.0`. Build пройдёт,
   а deploy упадёт с `ImagePullBackOff` (`401/403`) — пакет пока приватный.
2. GitHub → Packages → `k8s-debug-lab` → Package settings → Change visibility → Public.
3. В Actions открой этот запуск Release → **Re-run failed jobs**. Теперь
   deploy, smoke и создание GitHub Release должны пройти — в кластере
   работает v0.9.0, это стартовое состояние для ученика.

Иначе ученик получит `ImagePullBackOff` с причиной `401/403`, которая
не входит в задуманный сценарий.

## 5. Сброс стенда между учениками

```bash
kubectl delete ns shop data && kubectl apply -f cluster/bootstrap.yaml
```

Затем верни стартовое состояние: Actions → запуск Release для `v0.9.0` →
**Re-run all jobs**.

Если во время занятия ноды меняли руками (метки, taints) — проще всего
пересоздать кластер: `kind delete cluster --name lab` и шаг 1 заново.
