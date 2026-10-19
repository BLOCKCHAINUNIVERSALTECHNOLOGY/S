// s.math — standard math helpers
fn abs(n: int): int {
    if n < 0 { ret 0 - n }
    ret n
}

fn min(a: int, b: int): int {
    if a < b { ret a }
    ret b
}

fn max(a: int, b: int): int {
    if a > b { ret a }
    ret b
}

fn clamp(n: int, lo: int, hi: int): int {
    if n < lo { ret lo }
    if n > hi { ret hi }
    ret n
}

fn pow(base: int, exp: int): int {
    var result = 1
    var i = 0
    loop {
        if i >= exp { break }
        result = result * base
        i = i + 1
    }
    ret result
}
