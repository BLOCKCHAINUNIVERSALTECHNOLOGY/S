# Privacy

S Language core tools run **offline by default**.

- No telemetry is sent to project servers by the default CLI.
- Local logs (`s log`) stay on the machine under `~/.s-lang/logs` unless you copy them.
- `http_get` / `http_post` only contact URLs **your program** requests.
- SAI live mode only runs when you set API env vars; those keys never belong in public repos.

If you fork and add analytics, update this file and obtain consent where required.
