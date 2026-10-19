// S Todo — Week 1 sample
var tasks = []
push(tasks, "Build S Core")
push(tasks, "Ship .sbx")
push(tasks, "Pass 100 tests")

print "TODO count:", len(tasks)
print " 1.", tasks[0]
print " 2.", tasks[1]
print " 3.", tasks[2]

let done = pop(tasks)
print "Done:", done
print "Left:", len(tasks)
print json_stringify({ "left": len(tasks), "done": done })
