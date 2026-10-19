// Collections demo — M4
let scores = [95, 87, 92, 78]
print "Scores:", scores
print "First:", scores[0]
print "Count:", len(scores)

let student = {
    "name": "Sia",
    "lang": "S",
    "level": "Supreme"
}
print "Student:", student
print "Name:", student["name"]

print "All scores:"
for s in scores {
    print "  ->", s
}

let matrix = [[1, 2], [3, 4]]
print "matrix[1][0] =", matrix[1][0]
