// _smoke_app — S project
// Simple · Safe · Supreme

fn greet(who: str): str {
  ret "Hello, " + who + "!"
}

print greet("_smoke_app")
print "Ready. Run: s check main.s"
print json_stringify({ "project": "_smoke_app", "ok": true })
