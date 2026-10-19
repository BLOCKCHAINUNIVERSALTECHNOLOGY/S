# Security Policy — S Language

## Supported versions
| Version | Supported |
|---------|-----------|
| 3.3.x   | Yes |
| 3.2.x   | Yes |
| < 3.0   | Best effort |

## Reporting a vulnerability
Email or open a **private** security advisory on the project host.
Do **not** post exploit details in public issues first.

## S Shield (.sbx)
- Format SBX2 uses PBKDF2-HMAC-SHA256 and dual HMAC tags.
- Integrity failure **halts** the app (fail-closed).
- This raises the cost of casual reverse engineering; it is **not** a mathematical guarantee against a determined attacker.
- Never ship `.s` sources or `.sbx.map` in public releases.
- Keep `S_SHIELD_KEY` out of git and client-visible configs when possible.
- Real secrets (API keys, billing) belong on a server, not only inside the client pack.

## Claims we do not make
- "Impossible to reverse engineer"
- "Destroys the analyst's machine"
