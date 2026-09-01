/*
 * TSRTEST.C -- Pacific C (HI-TECH C) terminate-and-stay-resident counter.
 *
 * Hooks the BIOS user timer tick (INT 1Ch) and paints a number in the lower
 * left corner of the text screen, counting 0..10 once per second and then
 * wrapping back to 0. Hooks the keyboard IRQ (INT 09h) to watch for ESC; on
 * ESC it unhooks both vectors, writes "TSR STOPPED" over the counter and
 * leaves the machine as it found it.
 *
 * What Pacific C does and does not give you here:
 *
 *   interrupt      keyword works -- the compiler emits the push/pop + IRET
 *                  frame and reloads DS from __Ldata, so handler bodies can be
 *                  plain C. Handlers must be `far interrupt` because a vector
 *                  is a far pointer even in the small model.
 *   setiva/getiva  in the library (declared in <intrpt.h> under _HOSTED) --
 *                  no need to fiddle with INT 21h AH=25h/35h.
 *   inp()/outp()   in <dos.h>, built on HI-TECH's `port` type qualifier.
 *
 * What it does NOT give you, and why there is inline assembly below:
 *
 *   1. You cannot call an interrupt function from C. PACC rejects
 *      `(*old09)()` outright with "can't call an interrupt function", so
 *      chaining to the previous INT 09h handler has to be done by hand.
 *   2. There is no keep()/_dos_keep(). Going resident is a raw INT 21h AH=31h.
 *
 * The asm() dialect is HI-TECH's as86, which is neither MASM nor gas:
 *   - Intel operand order (dest first) but `#` for immediates
 *   - hex is 0ffffh / 060h -- leading zero, trailing h
 *   - a far indirect call through a pointer is `callf [0+_symbol]`
 *   - C identifiers carry a leading underscore
 *   - operand size is a trailing third operand: `mov [bx],#0,word`
 * The reliable way to find any of this is `pacc -S file.c` and read the .AS
 * the compiler generates for the equivalent C -- see PROBE.C.
 */

#include <dos.h>
#include <conio.h>
#include <intrpt.h>

#define VIDSEG      0xB800          /* colour text mode video segment */
#define SCR_ROW     24              /* bottom row of an 80x25 screen */
#define SCR_COL     0               /* lower LEFT corner */
#define VID_OFF     ((SCR_ROW * 80 + SCR_COL) * 2)
#define ATTR        0x0F            /* bright white on black */

#define TICKS_PER_SEC   18          /* INT 1Ch runs at 18.2 Hz */
#define COUNT_MAX       10

#define SC_ESC      0x01            /* ESC make code on port 0x60 */

/* Globals, not locals: an ISR gets a fresh stack frame every entry, and the
 * install path has to reach them too. */
far interrupt void (*old1c)(void);
far interrupt void (*old09)(void);

unsigned int  ticks;
unsigned int  count;
unsigned char stopreq;              /* set by the keyboard ISR, acted on by the tick ISR */
unsigned char running;

/* Paint a string at the counter position. Used for both the digits and the
 * final "TSR STOPPED" notice, so the ISR needs no stdio. */
static void
paint(char *s)
{
    unsigned char far *v;

    v = (unsigned char far *)MK_FP(VIDSEG, VID_OFF);
    while (*s != '\0') {
        v[0] = (unsigned char)*s++;
        v[1] = ATTR;
        v += 2;
    }
}

/*
 * INT 1Ch -- the BIOS "user" timer tick. Chosen over INT 08h precisely
 * because its default handler is a bare IRET: nothing else needs calling,
 * so no chaining and no EOI to get wrong.
 */
far interrupt void
tick1c(void)
{
    char buf[4];

    if (!running)
        return;

    if (stopreq) {
        running = 0;
        /* Put the vectors back before anything else can fire. */
        asm("	cli");
        setiva(0x1C, old1c);
        setiva(0x09, old09);
        asm("	sti");
        paint("TSR STOPPED");
        return;
    }

    if (++ticks < TICKS_PER_SEC)
        return;
    ticks = 0;

    buf[0] = (count >= 10) ? '1' : ' ';
    buf[1] = (char)('0' + (count % 10));
    buf[2] = '\0';
    paint(buf);

    if (++count > COUNT_MAX)
        count = 0;
}

/*
 * INT 09h -- keyboard IRQ. Peek at the scan code on its way past, then hand
 * the interrupt to the original handler. Peeking only: no EOI, no port 61h
 * acknowledge, nothing consumed, so the BIOS handler still sees a normal
 * keystroke and the key reaches DOS as usual.
 */
far interrupt void
key09(void)
{
    if (inp(0x60) == SC_ESC)
        stopreq = 1;

    /* Chain. PACC will not let C call an interrupt function, so this is the
     * INT-equivalent sequence by hand: push flags, far-call the saved vector.
     * Its IRET pops the flags we just pushed and returns here; our own
     * compiler-generated epilogue then restores registers and IRETs to the
     * interrupted code. .globl is emitted explicitly because the compiler
     * only auto-emits it for symbols it can see referenced from C. */
    asm("	.globl	_old09");
    asm("	pushf");
    asm("	callf	[0+_old09]");
}

int
main(void)
{
    union REGS r;
    unsigned int far *mcbsize;
    unsigned int psp;

    ticks = 0;
    count = 0;
    stopreq = 0;
    running = 1;

    old1c = getiva(0x1C);
    old09 = getiva(0x09);

    asm("	cli");
    setiva(0x1C, tick1c);
    setiva(0x09, key09);
    asm("	sti");

    cputs("TSR INSTALLED\r\n");

    /*
     * Go resident. There is no keep() in the Pacific C library, so this is
     * INT 21h AH=31h directly, and the paragraph count has to come from
     * somewhere. Rather than chase linker end-of-image symbols, ask DOS:
     * AH=62h gives the PSP, the MCB immediately below it holds the size of
     * our memory block in paragraphs, and that block is exactly what we want
     * to keep.
     *
     * This only behaves because the EXE is linked with -E<size> (see
     * BUILD.BAT). Without it PACC stamps FFFFFH in the header, DOS hands the
     * program every free paragraph, and keeping the whole block would leave
     * nothing for COMMAND.COM to run anything in.
     */
    r.h.ah = 0x62;
    int86(0x21, &r, &r);
    psp = r.x.bx;

    mcbsize = (unsigned int far *)MK_FP(psp - 1, 3);

    r.h.ah = 0x31;
    r.h.al = 0;
    r.x.dx = *mcbsize;
    int86(0x21, &r, &r);

    return 0;                       /* not reached */
}
