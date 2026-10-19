// sdx.dev — device sensors (stub)

fn camera(): str {
    print "[SDX] camera opened"
    ret "camera_ok"
}

fn gps(): str {
    print "[SDX] gps: lat=0.0 lon=0.0 (stub)"
    ret "0.0,0.0"
}

fn vibrate(ms: int): int {
    print "[SDX] vibrate:", ms, "ms"
    ret ms
}
