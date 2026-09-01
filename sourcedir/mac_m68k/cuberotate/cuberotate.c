/*
 * M68K Cube Rotate — Retro68 GUI demo for the System 7.5 / q800 test target.
 *
 * Draws a wireframe cube in a QuickDraw window and continuously rotates it
 * (X and Y axes) using a simple perspective projection. Unlike the console
 * PoC (retro68poc/hello.c) this is a plain graphical app: no CONSOLE runtime,
 * just the classic Mac Toolbox init sequence + a QuickDraw draw loop.
 *
 * Same dual-verification pattern as the console PoC, so the flask-testrunner
 * can assert on this without any interactive input:
 *
 *   1. On-screen: a status line ("STATUS: RETRO68_CUBE_OK") is drawn under
 *      the cube once the render loop has produced a number of frames — an
 *      OCR word-search step reads it off the framebuffer.
 *   2. Serial: the same token is written to the modem port (.AOut), which
 *      QEMU/Basilisk redirect to a host file for a grep-based, OCR-free check.
 *
 * NOTE on link flags: do NOT add -Wl,-gc-sections to this target. See
 * ../retro68poc/CMakeLists.txt for why (Retro68 issue #184) — it corrupts
 * relocations and crashes the app with "error of type 3" at launch.
 */

#include <string.h>
#include <math.h>

#include <Quickdraw.h>
#include <Windows.h>
#include <Fonts.h>
#include <Menus.h>
#include <TextEdit.h>
#include <Dialogs.h>
#include <Events.h>
#include <OSUtils.h>
#include <Devices.h>
#include <Serial.h>

#define CUBE_TOKEN "RETRO68_CUBE_OK"
#define START_TOKEN "RETRO68_CUBE_START"

/* Write a C string to the Mac Serial Driver's output side (modem port,
 * .AOut) -- identical helper to retro68poc/hello.c. Best-effort: if the
 * driver can't be opened we just skip serial and rely on the on-screen text. */
static OSErr serial_puts(const char *s)
{
    short outRef;
    OSErr err;
    long count;

    err = OpenDriver("\p.AOut", &outRef);
    if (err != noErr)
        return err;

    count = (long)strlen(s);
    return FSWrite(outRef, &count, s);
}

/* Unit cube vertices (x,y,z in [-1,1]). */
static const double cubeVerts[8][3] = {
    {-1, -1, -1}, { 1, -1, -1}, { 1,  1, -1}, {-1,  1, -1},
    {-1, -1,  1}, { 1, -1,  1}, { 1,  1,  1}, {-1,  1,  1},
};

/* The 12 edges, as pairs of vertex indices. */
static const int cubeEdges[12][2] = {
    {0,1}, {1,2}, {2,3}, {3,0},   /* back face   */
    {4,5}, {5,6}, {6,7}, {7,4},   /* front face  */
    {0,4}, {1,5}, {2,6}, {3,7},   /* connectors  */
};

/* Rotate (x,y,z) around the X then Y axis, project with simple perspective,
 * and return the screen-space point (window-relative pixels). */
static Point projectVertex(double x, double y, double z,
                            double ax, double ay,
                            int cx, int cy, double scale)
{
    double y1, z1, x2, z2;
    double focal = 4.0;
    double persp;
    Point p;

    /* rotate around X axis */
    y1 = y * cos(ax) - z * sin(ax);
    z1 = y * sin(ax) + z * cos(ax);

    /* rotate around Y axis */
    x2 = x * cos(ay) + z1 * sin(ay);
    z2 = -x * sin(ay) + z1 * cos(ay);

    /* perspective divide */
    persp = focal / (focal + z2);

    p.h = (short)(cx + x2 * scale * persp);
    p.v = (short)(cy + y1 * scale * persp);
    return p;
}

/* Draw one frame: erase, project all 8 vertices, stroke the 12 edges, and
 * (once past STATUS_AFTER_FRAME) redraw the persistent status line. */
#define STATUS_AFTER_FRAME 60

static void drawFrame(WindowPtr w, double ax, double ay, long frame)
{
    Point pts[8];
    int i;
    Rect r = w->portRect;
    int cx = (r.right - r.left) / 2;
    int cy = (r.bottom - r.top) / 2 + 10;
    double scale = 60.0;

    EraseRect(&r);

    MoveTo(10, 20);
    DrawString("\pM68K Cube Rotate");

    for (i = 0; i < 8; i++)
        pts[i] = projectVertex(cubeVerts[i][0], cubeVerts[i][1], cubeVerts[i][2],
                               ax, ay, cx, cy, scale);

    for (i = 0; i < 12; i++) {
        Point a = pts[cubeEdges[i][0]];
        Point b = pts[cubeEdges[i][1]];
        MoveTo(a.h, a.v);
        LineTo(b.h, b.v);
    }

    if (frame >= STATUS_AFTER_FRAME) {
        MoveTo(10, r.bottom - 15);
        /* NOTE: must be a single "\p..." literal, not "\pfoo" CONCAT_MACRO --
         * \p is a Retro68/GCC lexer-level prefix that computes the Pascal
         * length byte for THAT ONE literal token; concatenating it with a
         * plain C-string macro (adjacent-literal concatenation happens in a
         * later translation phase) does not recompute the length across the
         * combined text, and silently produces a garbled/invisible string. */
        DrawString("\pSTATUS: RETRO68_CUBE_OK");
    }
}

int main(void)
{
    WindowPtr w;
    Rect bounds = {60, 60, 60 + 320, 60 + 320};
    double angleX = 0.0, angleY = 0.0;
    long frame = 0;
    long finalTicks;

    /* Classic Mac Toolbox bring-up -- required before any QuickDraw/Window
     * Manager call, even for a single-window demo like this one. */
    InitGraf(&qd.thePort);
    InitFonts();
    InitWindows();
    InitMenus();
    TEInit();
    InitDialogs(NULL);
    InitCursor();

    w = NewWindow(NULL, &bounds, "\pCube Rotate", true, documentProc,
                  (WindowPtr)-1L, false, 0);
    SetPort(w);

    serial_puts(START_TOKEN "\r\n");

    for (;;) {
        drawFrame(w, angleX, angleY, frame);

        if (frame == STATUS_AFTER_FRAME)
            serial_puts(CUBE_TOKEN "\r\n");

        angleX += 0.05;
        angleY += 0.03;
        frame++;

        Delay(2, &finalTicks);   /* ~2/60s per frame */
    }

    return 0;
}
