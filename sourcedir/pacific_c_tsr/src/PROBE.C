/* Syntax probe: compiled with -S so PACC emits PROBE.AS. The point is to read
 * back exactly what HI-TECH's as86 wants for the constructs a TSR needs --
 * far indirect calls, interrupt prologue/epilogue, port I/O -- instead of
 * guessing at MASM syntax that as86 does not speak. */
#include <dos.h>
#include <intrpt.h>

far interrupt void (*oldvec)(void);
void (far *plainfar)(void);
unsigned char scancode;
unsigned int counter;

/* 1. how does as86 spell a far indirect call through a pointer?
 * NOTE: (*oldvec)() does not compile -- "can't call an interrupt function".
 * So chaining to a saved vector cannot go through the isr type; probe a
 * plain far pointer instead and copy the call sequence into asm(). */
void probe_farcall(void)
{
    (*plainfar)();
}

/* 2. what does the interrupt prologue/epilogue look like? */
interrupt void probe_isr(void)
{
    counter++;
}

/* 3. port read -- confirms the `port` qualifier path */
void probe_port(void)
{
    scancode = inp(0x60);
}

/* 4. far pointer store into video memory */
void probe_video(void)
{
    unsigned char far *v = (unsigned char far *)MK_FP(0xB800, 3840);
    v[0] = '7';
    v[1] = 0x0F;
}

/* 5. does a bare asm() statement survive to the .AS? */
void probe_asm(void)
{
    asm("	cli");
    asm("	sti");
}

int main(void)
{
    return 0;
}
