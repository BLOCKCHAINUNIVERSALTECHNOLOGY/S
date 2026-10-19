// s.json — JSON helpers (Week 1)
fn parse(text: str): str {
    ret json_parse(text)
}
fn stringify(value: str): str {
    ret json_stringify(value)
}
