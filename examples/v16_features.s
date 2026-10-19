// V1.6 features
var scores = [10, 20, 30]
scores[0] = 15
print "scores:", scores
print "20 in list?", 20 in scores

var total = 100
total += 50
print "total:", total

print "type:", type(scores)
print upper("supreme")
print join(split("a-b-c", "-"), "/")

let frozen = freeze([1, 2, 3])
print "frozen len:", len(frozen)

var bag = []
push(bag, "S")
push(bag, "Lang")
print bag
