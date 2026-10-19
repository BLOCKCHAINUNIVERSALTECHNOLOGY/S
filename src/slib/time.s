// s.time — time helpers (stub)
fn now(): str {
    print "[Slib.time] now()"
    ret "1970-01-01T00:00:00Z"
}

fn sleep_ms(ms: int): int {
    print "[Slib.time] sleep:", ms
    ret ms
}
