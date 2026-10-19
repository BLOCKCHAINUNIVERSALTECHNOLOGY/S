// S Calculator — Week 1 sample
fn add(a: int, b: int): int { ret a + b }
fn sub(a: int, b: int): int { ret a - b }
fn mul(a: int, b: int): int { ret a * b }
fn div(a: int, b: int): dec {
  guard b != 0
  ret a / b
}

print "1+2 =", add(1, 2)
print "10-3 =", sub(10, 3)
print "4*5 =", mul(4, 5)
print "20/4 =", div(20, 4)
print "20/0 =", div(20, 0)
print json_stringify({ "app": "calc", "ok": true })
