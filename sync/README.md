# Mirror synchronization

`mirror-sync.json` is the single source of truth for storage budgets and registry scope.
All content lives on Volume 1. The repository contains configuration and code only.

Commands:

```sh
python3 scripts/mirror_sync.py validate
python3 scripts/mirror_sync.py plan
python3 scripts/mirror_sync.py status
python3 scripts/mirror_sync.py run --registry all
```

`run` is fail-closed. It refuses to transfer anything unless the root-owned approval
file exists and contains the exact token printed by `plan`. Timers are installed but
remain disabled until the initial download has been explicitly approved and completed.

APT jobs use `debmirror`; PyPI and npm jobs use their curated prefetch adapters. Every
job has its own quota and the orchestrator also enforces the combined 450 GiB ceiling.
