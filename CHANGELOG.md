# Changelog

## Unreleased
- Expanded `s check` into a scope-aware Basic type checker for annotated values, mutable assignments, user-function arguments/returns, numeric operators, map keys, and indexes.
- Added strict unresolved-name checks, source-located diagnostics, and Phase B regression coverage; test suite now includes 140 checks.
- Corrected the calculator example's division return annotation to `dec`.

## 4.1.0 — Current source package
- CLI, Doctor, REPL, and module listing read the version from `VERSION`.
- `s test` now runs the built-in suite and Phase B checks; failures return a non-zero exit code.
- Doctor reports the same complete suite result as `s test`.

## 4.0.0 — Full language cut
- Stdlib: env_get, path_join, regex_match, csv_split, date_fmt, exit
- Serve: /api/form, /api/echo (W-WEB-3 baseline)
- examples/full_demo.s
- Language reference docs/23_LANGUAGE_REF.sd
- 129 tests green

## 3.8.x
Multi-platform packs, CI/CD, s serve, native Rust
