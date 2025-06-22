<h1 align="center">QEMU + DOS + Flask Automation Toolkit</h1>


This is a Python Flask tool used for automating QEMU, MS-DOS, and Pacific-C workflows.

I like writing software and tools for DOS, but it’s tedious and takes many steps. This project is an effort to reduce the process to a button click or API call to:

- Copy and build the code, validating whether the compiler succeeded or failed  
- Play the saved-state VM with the built executable and automatically capture the screen to observe the program's behavior

### In its current state, it:

- Copies data into the `hdd.img` DOS filesystem  
- Converts `hdd.img` into `hdd.qcow2` (for `savevm` support)  
- Boots MS-DOS using `qemu-system-i386`  
- Performs OCR against screenshots  
- Sends key inputs  
- Takes VM-state snapshots  
- Attaches and copies data to a floppy image  
- Records the runtime and results as an HTML report

### Working on:

- Separating out floppy build/package steps into a separate test  
- Making the build test solely responsible for checking if code compiles




## Build & Run demo

Build-test

https://github.com/user-attachments/assets/dd1ac9d7-7b0d-412a-85af-f96541620758

Play-test

https://github.com/user-attachments/assets/f65638ed-ffad-45da-8fd2-869d3140ef0a







## Screenshots

**Screenshot 1: Initial Build View**  
the tests are separated as its unreliable to write to the msdos FAT disk image while the vm is in a powered on state or may want to have separate build vs run actions

![Screenshot 2025-06-19 at 9 01 03 PM](https://github.com/user-attachments/assets/7a13753e-6e48-406e-83aa-ca8ca55fb3bf)

**Screenshot 2: Post-Build Summary**  
report generation with screenshots included inline

![Screenshot 2025-06-19 at 9 03 01 PM](https://github.com/user-attachments/assets/9e73eca0-c5af-4fb0-8399-b1f3c781d9eb)


Example Build-test failure:
![Screenshot 2025-06-21 at 9 35 01 AM](https://github.com/user-attachments/assets/657d8669-f6fc-494a-8ff8-7d2c50135f7a)


Example Build-test success detailed report:
![image](https://github.com/user-attachments/assets/7e6e57a9-1df3-4c98-ad75-cf9fd291ae7a)




