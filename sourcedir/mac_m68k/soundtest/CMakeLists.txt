# M68K Sound Test — a Sound Manager tone-sequence demo, built with Retro68.
#
# Standalone build (see build.sh):
#   cmake .. -DCMAKE_TOOLCHAIN_FILE=/opt/Retro68/toolchain/m68k-apple-macos/cmake/retro68.toolchain.cmake
#   make
#
# add_application(... CONSOLE) emits SoundTest.APPL, .bin (MacBinary) and
# .dsk (an HFS disk image with the app on it) — the .dsk is what the test
# list attaches to QEMU as a SCSI disk.
cmake_minimum_required(VERSION 3.10)
# Enable C and C++: the Retro68 runtime (libretrocrt/RetroConsole) links via
# the C++ driver, so CXX must be enabled even though soundtest.c is pure C.
project(SoundTest C CXX)

add_application(SoundTest
    soundtest.c
)
# sin()/cos() for the tone synthesis live in libm, not libc.
target_link_libraries(SoundTest m)

# NOTE: deliberately NOT using -Wl,-gc-sections here -- see
# ../retro68poc/CMakeLists.txt for the full explanation (Retro68 issue #184:
# --gc-sections corrupts relocations unless every linked object, including
# Retro68's own prebuilt runtime libs, was built with matching
# -ffunction-sections/-fdata-sections; symptom is a launch-time crash).
if(CMAKE_SYSTEM_NAME MATCHES Retro68)
    set_target_properties(SoundTest PROPERTIES LINK_FLAGS "-Wl,--mac-strip-macsbug")
endif()
