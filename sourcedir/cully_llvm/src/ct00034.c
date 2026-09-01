int
testmain()
{
	int x;
	
	x = 0;
	while(1)
		break;
	while(1) {
		if (x == 5) {
			break;
		}
		x = x + 1;
		continue;
	}
	for (;;) {
		if (x == 10) {
			break;
		}
		x = x + 1;
		continue;
	}
	do {
		if (x == 15) {
			break;
		}
		x = x + 1;
		continue;
	} while(1);
	return x - 15;
}

#include <stdio.h>

void main(void)
{
	printf("00034: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
