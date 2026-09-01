@echo off
rem One-shot build of the Pacific C TSR. 8086 (default) + small model (-Bs).
rem
rem -E8192 is the TSR-critical one: it caps the memory DOS hands the EXE at
rem ~8K of heap/stack on top of the image. PACC's default is FFFFFH, which
rem tells DOS to give the program everything, and INT 21h AH=31h then keeps
rem all of it -- leaving no free memory behind to run anything.
rem
rem The -S pass is not needed to build; it leaves TSRTEST.AS so the as86
rem syntax used by the asm() statements can be checked against what the
rem compiler itself generates. Compiler output goes to BUILD.LOG so errors
rem can be read off the disk rather than OCR'd off the screen.
set PATH=C:\PACIFIC\BIN;%PATH%
c:
cd \src
if exist TSRTEST.EXE del TSRTEST.EXE
if exist BUILD.LOG del BUILD.LOG
pacc -Q -Bs -S TSRTEST.C > BUILD.LOG
pacc -Q -Bs -O -Zg -E8192 -MTSRTEST.MAP -OTSRTEST.EXE TSRTEST.C >> BUILD.LOG
if errorlevel 1 goto failed
if not exist TSRTEST.EXE goto failed
echo BUILDPASS
goto done
:failed
echo BUILDFAIL
:done
