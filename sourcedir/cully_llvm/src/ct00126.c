int
testmain()
{
        int x;

        x = 3;
        x = !x;
        x = !x;
        x = ~x;
        x = -x;
        if(x != 2)
                return 1;
        return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00126: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
