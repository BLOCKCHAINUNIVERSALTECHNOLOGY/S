// Factorial + range loop — M3 demo
fn fact(n: int): int {
    if n <= 1 {
        ret 1
    }
    ret n * fact(n - 1)
}

print "5! =", fact(5)
print "6! =", fact(6)

print "Counting 1 to 5:"
for i in 1..6 {
    print "  ", i
}
print "Done!"
