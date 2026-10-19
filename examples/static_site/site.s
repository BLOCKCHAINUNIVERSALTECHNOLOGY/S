// W-WEB-1 — generate a small static site (prints full HTML)
let title = "S Static Site"
let user = "<script>alert(1)</script>"   // must be escaped in page

let nav = html_tag("nav", html_tag("a", "Home", { "href": "index.html" }))
let hero = html_tag("h1", html_escape(title))
let warn = html_tag("p", "User input: " + html_escape(user))
let about = html_tag("p", "Built with S — Simple · Safe · Supreme")
let body = nav + hero + warn + about

print html_page(title, body)
