/*
 * M68K Sound Test — Retro68 Sound Manager demo for the System 7.5 / q800
 * test target. The m68k/x86 equivalent of owc_sb16soundtest/src/TONETEST.C,
 * but through the Mac's Sound Manager instead of raw SB16 register I/O
 * (there is no port-mapped I/O on 68k Macs; the on-board ASC/EASC chip is
 * driven exclusively via Sound Manager on real hardware and under emulation).
 *
 * Plays a repeating cycle of three distinct tones, one second each, through
 * a `sampledSynth` SndChannel: each tone is a small in-memory 8-bit PCM sine
 * buffer, queued with a single `bufferCmd` SndCommand (Inside Macintosh's
 * "quick and dirty way to play a raw buffer" — no 'snd ' resource needed).
 *
 * QEMU's q800 machine has the ASC/EASC chip built in (unlike i386's SB16,
 * which is an addable -device); it just needs `-audiodev ...,id=X` plus
 * `-M q800,audiodev=X` (see test_startqemu's m68k branch). The host then
 * measures the capture for all three frequencies with
 * audiohelpers.detect_tone_sequence (a sliding-window Goertzel check, since
 * -- unlike the single-tone SB16 test -- three DIFFERENT tones can't all be
 * "the loudest window in the whole capture" at once).
 *
 * IMPORTANT: this is a plain QuickDraw app, NOT a Retro68 CONSOLE app. An
 * earlier CONSOLE version crashed the instant it called printf() (the console
 * runtime's lazy window init died — reproduced via serial markers: the app
 * wrote its pre-printf markers and then vanished, no error dialog). The
 * cuberotate demo already proved the plain-QuickDraw path is solid, so this
 * follows it: DrawString for the on-screen status line (OCR target) and the
 * serial port (.AOut) for the OCR-free host log.
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
#include <Sound.h>
#include <OSUtils.h>
#include <Devices.h>
#include <Serial.h>

#define START_TOKEN "RETRO68_SOUND_START"
#define OK_TOKEN    "RETRO68_SOUND_OK"

#define SAMPLE_RATE 22050
#define TONE_SECONDS 1
#define BUFLEN (SAMPLE_RATE * TONE_SECONDS)
#define PI 3.14159265358979323846

/* Three well-separated tones -- easy to tell apart with a Goertzel filter
 * even allowing +-60Hz tolerance for each. */
static const double tones[3] = {440.0, 660.0, 880.0};

static unsigned char sampleBuf[BUFLEN];

/* Write a C string to the Mac Serial Driver's output side (modem port, .AOut).
 * Opens the driver ONCE and caches the refnum: reopening a driver on every
 * call is wrong, and this program writes many diagnostic lines. */
static short g_serialRef = 0;
static Boolean g_serialTried = false;

static void serial_puts(const char *s)
{
    long count;

    if (!g_serialTried) {
        g_serialTried = true;
        if (OpenDriver("\p.AOut", &g_serialRef) != noErr)
            g_serialRef = 0;
    }
    if (g_serialRef == 0)
        return;
    count = (long)strlen(s);
    FSWrite(g_serialRef, &count, s);
}

/* Draw a C string as a Pascal string at (h, v) in the current port. Keeps the
 * on-screen status human/OCR-readable without needing a "\p" literal. */
static void draw_cstr(short h, short v, const char *s)
{
    unsigned char pstr[256];
    size_t n = strlen(s);
    if (n > 255) n = 255;
    pstr[0] = (unsigned char)n;
    memcpy(pstr + 1, s, n);
    MoveTo(h, v);
    DrawString(pstr);
}

/* Erase a line's worth of the window, then draw s there. QuickDraw's
 * DrawString only ORs black pixels into the port (the default pen mode never
 * removes ink) -- overdrawing old text with a string of spaces draws NO
 * pixels at all, so the previous digits stay put and each redraw visibly
 * stacks on top of the last one. An explicit EraseRect over that line's
 * bounding box is what actually clears it. */
static void draw_cstr_line(short h, short v, const char *s)
{
    Rect line;
    line.left = h;
    line.right = 390;
    line.top = v - 11;     /* ~1 line above baseline covers ascenders    */
    line.bottom = v + 4;   /* a few px below baseline covers descenders  */
    EraseRect(&line);
    draw_cstr(h, v, s);
}

/* Fill sampleBuf with one second of an 8-bit unsigned PCM sine wave at hz. */
static void fillTone(double hz)
{
    long i;
    double step = 2.0 * PI * hz / (double)SAMPLE_RATE;

    /* Amplitude 100 of a possible 127 leaves headroom so nothing clips into
     * harmonics that would muddy the host-side SNR check (matches
     * TONETEST.C's choice for the same reason). */
    for (i = 0; i < BUFLEN; i++)
        sampleBuf[i] = (unsigned char)(128 + (int)(100.0 * sin(step * (double)i)));
}

/* bufferCmd plays asynchronously: the Sound Manager keeps reading this header
 * (and, through samplePtr, sampleBuf) after SndDoCommand returns. Both must
 * therefore outlive the call -- static, not stack-local. */
static SoundHeader playHdr;

static void playTone(SndChannelPtr chan, double hz)
{
    SndCommand cmd;
    long finalTicks;

    fillTone(hz);

    playHdr.samplePtr = (Ptr)sampleBuf;
    playHdr.length = BUFLEN;
    playHdr.sampleRate = (Fixed)((long)SAMPLE_RATE << 16);   /* Fixed 16.16, no fractional part */
    playHdr.loopStart = 0;
    playHdr.loopEnd = 0;
    playHdr.encode = stdSH;
    playHdr.baseFrequency = 60;

    cmd.cmd = bufferCmd;
    cmd.param1 = 0;
    cmd.param2 = (long)&playHdr;
    SndDoCommand(chan, &cmd, false);

    Delay(60 * TONE_SECONDS + 4, &finalTicks);   /* ~1s of playback + margin */
}

/* How many full 3-tone cycles to play. Bounded so the run is deterministic:
 * the .wav gets a fixed number of tone cycles, then the app parks in an event
 * loop so the OCR step has a stable status line and test_terminate_all can
 * stop the VM cleanly. */
#define CYCLES 3

/* Bottom-right pushbutton, created once and reused for both the failure park
 * loop and the normal end-of-run park loop -- either way the app needs a way
 * to quit besides waiting for the test framework to kill the VM. */
static ControlHandle makeQuitButton(WindowPtr w)
{
    Rect btnRect;
    btnRect.left = 300; btnRect.right = 380;
    btnRect.top = 210;  btnRect.bottom = 234;
    return NewControl(w, &btnRect, "\pQuit", true, 0, 0, 1, pushButProc, 0);
}

/* Park the app in a real event loop, watching for a click on quitBtn (or the
 * window's own close/go-away box) to exit -- rather than looping forever with
 * no way out except the test framework killing the VM. Returns once the user
 * asks to quit. */
static void parkUntilQuit(WindowPtr w, ControlHandle quitBtn)
{
    for (;;) {
        EventRecord ev;
        if (WaitNextEvent(everyEvent, &ev, 30, NULL)) {
            if (ev.what == mouseDown) {
                Point pt = ev.where;
                WindowPtr hitWindow;
                short part = FindWindow(pt, &hitWindow);
                if (part == inGoAway && hitWindow == w) {
                    return;
                }
                if (part == inContent && hitWindow == w) {
                    ControlHandle hitCtl;
                    GlobalToLocal(&pt);
                    if (FindControl(pt, w, &hitCtl) == inButton && hitCtl == quitBtn) {
                        if (TrackControl(hitCtl, pt, NULL) != 0)
                            return;   /* mouse released while still over the button */
                    }
                }
            }
        }
    }
}

int main(void)
{
    WindowPtr w;
    Rect bounds = {70, 60, 70 + 260, 60 + 400};
    SndChannelPtr chan = NULL;
    ControlHandle quitBtn;
    OSErr err;
    long cycle;
    char line[64];

    /* Classic Mac Toolbox bring-up -- required before any QuickDraw / Window
     * Manager call. */
    InitGraf(&qd.thePort);
    InitFonts();
    InitWindows();
    InitMenus();
    TEInit();
    InitDialogs(NULL);
    InitCursor();

    serial_puts(START_TOKEN "\r\n");

    w = NewWindow(NULL, &bounds, "\pM68K Sound Test", true, documentProc,
                  (WindowPtr)-1L, false, 0);
    SetPort(w);
    quitBtn = makeQuitButton(w);

    draw_cstr(10, 20, "M68K Sound Test");
    draw_cstr(10, 40, "opening sound channel...");

    err = SndNewChannel(&chan, sampledSynth, 0 /* mono */, NULL);
    if (err != noErr) {
        draw_cstr(10, 60, "SndNewChannel FAILED");
        serial_puts("RETRO68_SOUND_FAIL\r\n");
        parkUntilQuit(w, quitBtn);
        return 1;
    }
    draw_cstr(10, 60, "playing 3 tones x 3 cycles: 440 / 660 / 880 Hz");

    for (cycle = 0; cycle < CYCLES; cycle++) {
        int i;
        for (i = 0; i < 3; i++) {
            strcpy(line, "cycle ?: playing ??? Hz");
            line[6] = (char)('0' + cycle);
            line[17] = (char)('0' + (int)tones[i] / 100 % 10);
            line[18] = (char)('0' + (int)tones[i] / 10 % 10);
            line[19] = (char)('0' + (int)tones[i] % 10);
            draw_cstr_line(10, 90, line);
            playTone(chan, tones[i]);
        }
        if (cycle == 0) {
            /* One full cycle done -> all three tones are now in the capture. */
            draw_cstr(10, 120, "STATUS: " OK_TOKEN);
            serial_puts(OK_TOKEN "\r\n");
        }
    }

    SndDisposeChannel(chan, true);
    draw_cstr(10, 150, "(done; tones played)");

    /* Park so the window (and its status line) stays up for OCR, and
     * test_terminate_all can stop the VM cleanly -- or a human running this
     * interactively can click Quit (or the window's close box) to exit. */
    parkUntilQuit(w, quitBtn);

    return 0;
}
