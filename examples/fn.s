// Functions
fn add(a: int, b: int): int {
    ret a + b
}

fn greet(name: str): str {
    ret "Hello, " + name + "!"
}

print add(10, 25)
print greet("Queen")
