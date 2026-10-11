@AGENTS.md

## Claude Code

- Na początku sesji przeczytaj `docs/backlog.md` (sekcje „Stan” i „Najbliższe drobne kroki”).
- Nowe znaleziska zapisuj komendą `/finding` (`.claude/commands/finding.md`).
- Polecenia na Sparku uruchamiaj przez `ssh -o ClearAllForwardings=yes spark '…'`; tylko odczyt (`make status`, `make errors`, `make log`, `docker ps`, `free -h`) bez pytania, resztę po potwierdzeniu.
