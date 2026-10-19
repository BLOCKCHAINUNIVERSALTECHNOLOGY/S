// Classes + safe/rescue — M7 / V0.0.7
class Point {
    fn init(x: int, y: int): int {
        this.x = x
        this.y = y
        ret 0
    }
    fn sum(): int {
        ret this.x + this.y
    }
}

let p = new Point(10, 20)
print "Point sum:", p.sum()

safe {
    print "About to crash..."
    print 1 / 0
    print "never reached"
} rescue err {
    print "Rescued:", err
}

print "Program continues!"
