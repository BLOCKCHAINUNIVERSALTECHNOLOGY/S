// s.http — HTTP helpers (Week 1)
fn get(url: str): str {
    ret http_get(url)
}
fn post(url: str, body: str): str {
    ret http_post(url, body)
}
