// s.io — file I/O (host-backed via built-ins later; stub for now)
fn read_stub(path: str): str {
    print "[Slib.io] read:", path
    ret ""
}

fn write_stub(path: str, content: str): str {
    print "[Slib.io] write:", path
    ret path
}
