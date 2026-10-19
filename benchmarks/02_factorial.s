fn fact(n: int): int {
  if n <= 1 { ret 1 }
  ret n * fact(n - 1)
}
print fact(10)
