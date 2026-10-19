// S 4.0 — full language surface demo
fn fib(n: int): int {
  if n <= 1 { ret n }
  ret fib(n - 1) + fib(n - 2)
}

fn greet(name: str = "World"): str {
  ret "Hello, " + name + "!"
}

print greet("S")
print "fib(8) =", fib(8)

var xs = [3, 1, 4, 1, 5]
print "sorted", sort(xs)
print "unique", unique(xs)
print "sum", sum(xs)
print "take", take(xs, 3)
print 10 |> { n -> n * n }

let data = json_parse("{\"ok\": true}")
print data
print html_escape("<b>")
print date_fmt("%Y-%m-%d")

if false {
  print "no"
} elif true {
  print "elif ok"
}

var i = 0
while i < 2 {
  print "w", i
  i += 1
}

require(true, "must hold")
print "FULL DEMO OK"
