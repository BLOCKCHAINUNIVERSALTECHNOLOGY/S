// S Power features — beyond Kotlin boilerplate
// V1.3.0

// 1. String interpolation (no + spam)
let lang = "S"
print "Language: ${lang} is Supreme"

// 2. when expression (cleaner than when in some cases)
let code = 200
when code {
  200 { print "OK" }
  404 { print "Not Found" }
  else { print "Other" }
}

// 3. enum
enum Status { Ready, Running, Done }
print Status.Ready

// 4. opt null-safety
let maybe = some(10)
print "value:", valueOr(maybe, 0)
print "empty:", valueOr(none(), -1)

// 5. map / filter — functional lists
fn square(n: int): int { ret n * n }
fn big(n: int): bool { ret n > 10 }

let xs = [2, 3, 4, 5]
print "squares:", map(xs, square)
print "big squares:", filter(map(xs, square), big)
