// s.html — static HTML helpers (W-WEB-1)
fn escape(text: str): str {
  ret html_escape(text)
}
fn tag(name: str, body: str): str {
  ret html_tag(name, body)
}
fn page(title: str, body: str): str {
  ret html_page(title, body)
}
