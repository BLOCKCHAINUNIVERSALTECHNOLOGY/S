// s.net — network (stub)
fn get(url: str): str {
    print "[Slib.net] GET", url
    ret "net_stub_response"
}

fn post(url: str, body: str): str {
    print "[Slib.net] POST", url
    ret "net_stub_ok"
}
