# orders — k8s debug lab

Небольшой сервис заказов в Kubernetes. В кластере сейчас крутится
последний удачный релиз — **v0.9.0**. С тех пор команда влила в `main`
несколько изменений, и следующий релиз **не доезжает**: `Release` workflow
красный, и никто не успел разобраться почему.

**Твоя задача — выпустить v1.0.0 из текущего `main` и довести релиз до
зелёного состояния**: все Deployment'ы раскатились на новую версию,
smoke-тест прошёл, GitHub Release создан.

Откатиться на v0.9.0 (`kubectl rollout undo`, revert всех коммитов) —
не решение: изменения в `main` нужны бизнесу, их надо довезти, а не выкинуть.

## Архитектура

```
              namespace: shop                          namespace: data
 ┌────────────────────────────────────────┐      ┌──────────────────────┐
 │  Service orders-api :80                │      │  Service redis :6379 │
 │        │                               │      │        │             │
 │  Deployment orders-api (x2)  ──────────┼──────┼──▶ Deployment redis  │
 │    POST /orders → LPUSH queue          │      │                      │
 │                                        │      └──────────────────────┘
 │  Deployment orders-worker (x1) ────────┼──────────▲
 │    BRPOP queue → status=processed      │
 └────────────────────────────────────────┘
```

Один Docker-образ (`app/`), api и worker отличаются командой запуска.
Манифесты — kustomize: `deploy/base` + оверлей `deploy/overlays/lab`.

| Workflow | Когда | Что делает |
|---|---|---|
| `CI` | push в `main`, PR | pytest, сборка образа без push, `kustomize build` + `kubeconform` |
| `Release` | push тега `vX.Y.Z` | build & push в GHCR → deploy в lab-кластер → rollout status → smoke-тест → GitHub Release |

## Правила игры

1. **Код в `app/orders` не трогаем** — проблемы в инфраструктуре: манифестах, конфигурации, пайплайне.
2. Первый релиз — `git tag v1.0.0 && git push origin v1.0.0`. Каждое исправление —
   отдельный коммит (лучше через PR), потом новый тег: `v1.0.1`, `v1.0.2`, …
3. Проблем несколько. Часть видна в кластере сразу, часть вылезет только
   после того, как починишь предыдущие: релиз будет падать каждый раз чуть дальше.
4. Решение «удалить проверку» (probe, smoke-тест, лимит) не засчитывается.
   Хак «поправил руками через `kubectl edit`» допустим для диагностики,
   но итоговое исправление должно быть в git — иначе следующий релиз всё откатит.
5. На каждую проблему заполни запись в журнале (шаблон ниже).

## Доступ

- **Кластер:** kubeconfig выдаст наставник (у тебя будет больше прав, чем у CI).
- **Логи релиза:** вкладка *Actions* → *Release*. На падении в логе есть
  шаг *Snapshot on failure* — это стартовая точка, а не ответ.

## Набор инструментов

Не подсказки, а то, чем стоит уметь пользоваться:

```bash
kubectl get pods -n shop -o wide          # статусы, ноды, рестарты
kubectl describe pod <pod> -n shop        # Events внизу — читать всегда
kubectl logs <pod> -n shop [--previous]   # --previous: лог упавшего контейнера
kubectl get events -n shop --sort-by=.lastTimestamp
kubectl get deploy,rs,svc,endpointslices -n shop
kubectl get pod <pod> -n shop -o yaml     # что реально применилось
kubectl get nodes --show-labels
kubectl rollout status / history / undo
kubectl debug -it <pod> -n shop --image=busybox:1.36 --target=<container>
kubectl run tmp -n shop --rm -it --image=busybox:1.36 -- sh   # сеть/DNS изнутри
kustomize build deploy/overlays/lab       # что именно уедет в кластер
```

Локально:

```bash
cd app && pip install -r requirements-dev.txt && pytest
```

## Журнал отладки

Для каждой проблемы:

```markdown
### Проблема N
- **Симптом:** что видно в Actions / kubectl (статус пода, текст ошибки)
- **Как нашёл:** какие команды, что в них увидел
- **Причина:** почему так происходит (механика Kubernetes, а не просто «опечатка»)
- **Исправление:** коммит / PR
- **Как не допустить снова:** проверка в CI, политика, договорённость
```

Последний пункт — самый важный. Хороший middle не только чинит, но и
делает так, чтобы это не повторилось.

## Структура

```
app/                     код, тесты, Dockerfile
deploy/base/             манифесты (data: redis, shop: api, worker, конфиг)
deploy/overlays/lab/     оверлей для учебного кластера
cluster/                 конфиг kind и bootstrap (для наставника)
scripts/smoke.sh         smoke-тест из релиза
.github/workflows/       CI и Release
```
