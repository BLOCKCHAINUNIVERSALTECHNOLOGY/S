// V1.7 features
print "slice:", [1, 2, 3, 4, 5][1:4]
print "ternary:", true ? "S" : "no"
repeat 2 {
  print "repeat ok"
}
print replace("kotlin", "kotlin", "S")
write_file("/tmp/s_hello.txt", "Hello from S")
print "file:", read_file("/tmp/s_hello.txt")
