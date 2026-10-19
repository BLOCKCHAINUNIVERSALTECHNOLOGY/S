// S > Kotlin demonstration — V1.8
// All user code lives in .s (S symbol)

print """S Language
Simple · Safe · Supreme"""

// guard — early exit (cleaner than nested if)
fn positive(n: int): int {
  guard n > 0
  ret n
}
print "guard:", positive(9)
print "guard fail:", positive(-1)

// safe navigation ?.
class Box {
  fn init(v: int): int {
    this.v = v
    ret 0
  }
}
let b = new Box(7)
print "nav:", b?.v
print "nav nil:", nil?.v

// list power
print sort(unique([3, 1, 2, 1, 3]))
print reverse([1, 2, 3])

// still have pipes, opt, defer, async...
print none() ?? "safe default"
print 3 |> { x -> x * x }
