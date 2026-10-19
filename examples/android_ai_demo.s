// SDX + SAI demo — M10 / V0.0.10
use sdx.ui
use sdx.dev
use sdx.notify
use sai.chat
use sai.gen

// Android UI stubs
screen("S App")
button("Click Me")
text("Welcome to S Language")
show("Hello from SDX!")

// Device
camera()
gps()
vibrate(100)

// Notifications
notify("S Alert", "Project S is running")

// AI
print ask("What is S Language?")
print chat("Make me Supreme")
print generate("a short poem about code")
