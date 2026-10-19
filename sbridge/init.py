"""Generate Android-oriented SBridge project tree."""

from pathlib import Path


def init_project(dest: str, app_name: str = "SApp", package: str = "com.slang.app"):
    root = Path(dest)
    root.mkdir(parents=True, exist_ok=True)
    (root / "src" / "main" / "java" / package.replace(".", "/")).mkdir(parents=True, exist_ok=True)
    (root / "src" / "main" / "assets").mkdir(parents=True, exist_ok=True)
    (root / "src" / "main" / "res").mkdir(parents=True, exist_ok=True)

    tdir = Path(__file__).parent / "templates"
    mapping = {
        "PACKAGE": package,
        "APP_NAME": app_name,
        "ENTRY": "main.s",
    }

    def render(name: str) -> str:
        text = (tdir / name).read_text(encoding="utf-8")
        for k, v in mapping.items():
            text = text.replace("{{" + k + "}}", v)
        return text

    (root / "src" / "main" / "AndroidManifest.xml").write_text(
        render("AndroidManifest.xml.tpl"), encoding="utf-8"
    )
    pkg_path = root / "src" / "main" / "java" / package.replace(".", "/")
    (pkg_path / "MainActivity.kt").write_text(render("MainActivity.kt.tpl"), encoding="utf-8")
    (root / "src" / "main" / "assets" / "main.s").write_text(
        render("main.s.tpl"), encoding="utf-8"
    )
    (root / "project.se").write_text(
        f"""# SBridge project
name: {app_name}
package: {package}
entry: main.s
version: 0.1.0
strict_let_collections: false
""",
        encoding="utf-8",
    )
    (root / "README.sd").write_text(
        f"""# {app_name} — SBridge scaffold

1. Install Android SDK + open as Gradle project (wire manually for now)
2. S entry: src/main/assets/main.s
3. MainActivity is a host stub — link SBridge when available

This is Phase C structure, not a finished APK.
""",
        encoding="utf-8",
    )
    return root
