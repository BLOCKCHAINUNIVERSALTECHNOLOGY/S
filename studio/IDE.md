# S Studio IDE — V1.2

## Components

| Piece | Location | Status |
|-------|----------|--------|
| Syntax grammar | `studio/s.tmLanguage.json` | ✅ |
| Language config | `studio/s.language-configuration.json` | ✅ |
| LSP server | `studio/lsp/server.py` | ✅ minimal |
| Browser editor | `play/index.html` (S Play) | ✅ |
| Desktop IDE | — | Planned (Electron/Tauri + Monaco) |

## Wire LSP in VS Code / Cursor

```json
{
  "languages": [{
    "id": "s",
    "extensions": [".s"],
    "configuration": "./studio/s.language-configuration.json"
  }],
  "grammars": [{
    "language": "s",
    "scopeName": "source.s",
    "path": "./studio/s.tmLanguage.json"
  }]
}
```

Run LSP:
```bash
python3 studio/lsp/server.py
```

## Open S Play

```bash
# open play/index.html in any browser
xdg-open play/index.html   # linux
open play/index.html       # mac
```
