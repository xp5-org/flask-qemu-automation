#include <stdio.h>

int testmain()
{
    long long int res = 0;

    if (res < -2147483648LL) {
        printf("Error: 0 < -2147483648\n");
        return 1;
    }
    else
    if (2147483647LL < res) {
        printf("Error: 2147483647 < 0\n");
        return 2;
    }
    else
        printf("long long constant test ok.\n");
    return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00203: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
