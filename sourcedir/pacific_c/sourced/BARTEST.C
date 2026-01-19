#include <dos.h>
#include <conio.h>
#include <stdlib.h>
#include <string.h>

#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 200
#ifndef MK_FP
#define MK_FP(seg, off) ((void far *)(((unsigned long)(seg) << 16) | (unsigned int)(off)))
#endif

void set_mode(int mode) {
    union REGS regs;
    regs.h.ah = 0x00;
    regs.h.al = (unsigned char)mode;
    int86(0x10, &regs, &regs);
}

void wait_ms(unsigned int ms) {
    union REGS regs;
    unsigned long us = (unsigned long)ms * 1000L;
    regs.h.ah = 0x86;
    regs.x.cx = (unsigned int)(us >> 16);
    regs.x.dx = (unsigned int)(us & 0xFFFF);
    int86(0x15, &regs, &regs);
}

void clear_screen() {
    unsigned int i;
    unsigned char far *ptr = (unsigned char far *)MK_FP(0xA000, 0);
    for (i = 0; i < 32000U; i++) {
        ptr[i] = 0;
        ptr[i + 32000U] = 0;
    }
}

void draw_bars(int num_bars) {
    int i, row;
    int bar_width = SCREEN_WIDTH / num_bars;
    unsigned char far *vga = (unsigned char far *)MK_FP(0xA000, 0);

    for (i = 0; i < num_bars; i++) {
        int height = rand() % (SCREEN_HEIGHT - 20) + 10;
        unsigned char color = (unsigned char)(i + 32);
        int x_offset = i * bar_width;
        unsigned char far *dest = vga + x_offset + (SCREEN_HEIGHT - height) * 320;

        for (row = 0; row < height; row++) {
            int col;
            for (col = 0; col < bar_width; col++) {
                dest[col] = color;
            }
            dest += 320;
        }
    }
}



int main() {
    set_mode(0x13);

    while (!kbhit()) {
        clear_screen();
        draw_bars(80);
        wait_ms(500);
    }

    set_mode(0x03);
    return 0;
}