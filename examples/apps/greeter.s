// Greeter — Week 4
fn hi(name: str): str {
  ret "Namaste, " + name + "!"
}
print hi("S")
print hi("Supreme")
require(len(hi("x")) > 0, "empty greet")
