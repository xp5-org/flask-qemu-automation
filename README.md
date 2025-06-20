this is a python flask tool used for automating qemu. in its current state it boots msdos using qemu-system-i386, performs OCR against screenshots, sends key inputs, takes snapshots and records the time 


test runner with build & play testlists. the build test takes a "savevm" snapshot (memory state save) which is replayed for instant boot with the play testlist

the tests are separated as its unreliable to write to the msdos FAT disk image while the vm is in a powered on state or may want to have separate build vs run actions
![Screenshot 2025-06-19 at 9 01 03 PM](https://github.com/user-attachments/assets/7a13753e-6e48-406e-83aa-ca8ca55fb3bf)

report generation with screenshots included inline
![Screenshot 2025-06-19 at 9 03 01 PM](https://github.com/user-attachments/assets/9e73eca0-c5af-4fb0-8399-b1f3c781d9eb)
