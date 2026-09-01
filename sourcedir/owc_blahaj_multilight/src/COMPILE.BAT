set DJGPP=C:\DJGPP\DJGPP.ENV
set PATH=C:\DJGPP\BIN;%PATH%
gcc -std=gnu99 -O2 -o blahaj.exe blahaj.c -lalleg -lm
if not errorlevel 1 echo BUILD OK executable
