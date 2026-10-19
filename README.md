# S — Simple · Safe · Supreme

**Version 4.1.0 — Fully developed offline language**

```bash
python3 s new myapp
python3 s run myapp/main.s
python3 s test
python3 s doctor
python3 s html build examples/static_site/site.s --out=site
python3 s serve site --port=8080
python3 s release myapp --key=secret
```

## Language

Functions (defaults, recursion), classes, `while`/`for`/`repeat`/`loop`,
`if/elif`, `when`, pipes `|>`, lambdas, `opt`/`guard`/`require`, async surface,
modules, JSON/HTTP, HTML static sites, HTTP serve, sealed `.sbx` packs.

### Static checks

```bash
python3 s check examples/full_demo.s
python3 s check examples/full_demo.s --strict
```

The checker validates known annotations, assignments, user-function calls and
returns, and common operator/index types. Strict mode also reports unresolved
names where imports permit reliable resolution. See `docs/23_LANGUAGE_REF.sd`
for supported rules and current limitations.

## Full demo
```bash
python3 s run examples/full_demo.s
```

## Docs
- `docs/23_LANGUAGE_REF.sd` — reference
- `docs/18_PRODUCT_BLUEPRINT.sd` — product plan
- `LICENSE` — MIT

## CI
Multi-OS GitHub Actions: `.github/workflows/ci.yml`
