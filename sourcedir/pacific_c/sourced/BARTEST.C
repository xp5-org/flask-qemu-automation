#include <dos.h>
#include <conio.h>
#include <stdio.h>
#include <stdlib.h> 
#define screenwidth 640
#define screenheight 480

void setVideoMode(unsigned char mode) {
    union REGS inregs, outregs;
    inregs.h.ah = 0x00;
    inregs.h.al = mode;
    int86(0x10, &inregs, &outregs);
}

void setPixel(int x, int y, unsigned char color) {
    union REGS inregs, outregs;
    inregs.h.ah = 0x0C;
    inregs.h.al = color;
    inregs.x.cx = x;
    inregs.x.dx = y;
    int86(0x10, &inregs, &outregs);
}

int *generateRandomBars(int n) {
int i;

    static int barHeights[320]; 
    for (i = 0; i < n; i++) {
        barHeights[i] = rand() % screenheight - 10; // Random height between 1 and MAX_HEIGHT
    }
    
    return barHeights;
}

void drawBarsFromArray(int *barHeights, int numBars) {
    unsigned char color;
    int y, x, i;

    for (x = 0; x < numBars; x++) {
        int barHeight = barHeights[x];
        int barWidth = screenwidth / numBars;
        int startX = x * barWidth; // Calculate the starting position of the current bar
        color = rand() % 256;
        for (y = screenheight - barHeight; y < screenheight; y++) {
            for (i = 0; i < barWidth; i++) {
                //color = rand() % 256; // Random color for each pixel of the bar
                setPixel(startX + i, y, color); // Corrected calculation for x-coordinate
            }
        }
    }
}

#include <conio.h> // Include conio.h for getch()

int main() {
    int *barHeights;
    int numBars = 10; 

    // Infinite loop until any key is pressed
    while (!kbhit()) {
        barHeights = generateRandomBars(numBars);

        setVideoMode(0x12); // Set Mode 12h 640x480

        drawBarsFromArray(barHeights, numBars);

        // Wait for a key press or continue looping
        if (kbhit()) break; // Break out of the loop if a key is pressed

        // Clean up
        free(barHeights);
        setVideoMode(0x03); // Set text mode
    }

    // Clean up before exiting
    setVideoMode(0x03); // Set text mode
    return 0;
}

