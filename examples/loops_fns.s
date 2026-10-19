// Loops & Functions — S 3.2.0

fn double(x: int): int {
  ret x * 2
}

fn greet(name: str = "Supreme"): str {
  ret "Hello, " + name + "!"
}

print greet()
print greet("S")
print double(21)

var i = 0
while i < 3 {
  print "while", i
  i += 1
}

for n in [1, 2, 3] {
  print "for", n |> double
}

repeat 2 {
  print "repeat ok"
}
