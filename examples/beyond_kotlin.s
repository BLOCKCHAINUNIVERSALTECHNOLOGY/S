// S features designed to beat Kotlin on simplicity + power
// V1.4.0

// Lambda (no verbose syntax)
let triple = { x -> x * 3 }
print triple(7)

// Pipe chain (like Elixir / cleaner than nested calls)
fn inc(x: int): int { ret x + 1 }
fn square(x: int): int { ret x * x }
print 4 |> inc |> square

// Null-coalesce
print none() ?? "default"
print some("S") ?? "no"

// Default params
fn greet(name: str = "World"): str {
    ret "Hello, ${name}!"
}
print greet()
print greet("Queen")

// Result type
let r = ok(100)
print "ok?", isOk(r), "value", unwrap(r)

// map + lambda together
print map([1, 2, 3], { n -> n * n })

// defer cleanup
defer { print "[cleanup done]" }
print "working..."
