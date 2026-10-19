// jsonx — sample Hub package
fn quote(s: str): str {
    ret "\"" + s + "\""
}

fn pair(k: str, v: str): str {
    ret quote(k) + ": " + quote(v)
}
