void
voidfn()
{
    return;
}

int
testmain()
{
    voidfn();
    return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00080: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
