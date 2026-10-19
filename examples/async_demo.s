// Async / await / spawn — V1.5
async fn load(name: str): str {
    sleep(10)
    ret "loaded:" + name
}

print "1. start"
print "2.", await load("config")
print "3.", await load("user")

async fn work(id: int): int {
    print "work", id
    ret id
}

spawn work(1)
spawn work(2)
print "4. spawned"
