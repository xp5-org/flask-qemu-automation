@echo off
rem One-shot Pacific C build of BARTEST.C -- replaces the PPD IDE/F3 keystroke
rem drive. Build params: 8086 (default, no -1/-2/-7) and SMALL memory model
rem (-Bs). PACC is the command line driver; it runs cpp/p1/cg86/opt86/as86/
rem hlink itself and picks C:\PACIFIC\LIB\86--dsc.lib + RT86--DS.OBJ from -Bs.
set PATH=C:\PACIFIC\BIN;%PATH%
c:
cd \src
if exist BARTEST.EXE del BARTEST.EXE
pacc -Q -Bs -O -Zg -MBARTEST.MAP -OBARTEST.EXE BARTEST.C
if errorlevel 1 goto failed
if not exist BARTEST.EXE goto failed
echo BUILDPASS
goto done
:failed
echo BUILDFAIL
:done
