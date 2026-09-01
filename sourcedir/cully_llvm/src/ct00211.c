extern int printf(const char *format, ...);

#define ACPI_TYPE_INVALID       0x1E
#define NUM_NS_TYPES            ACPI_TYPE_INVALID+1
int array[NUM_NS_TYPES];

#define n 0xe
int testmain()
{
    printf("n+1 = %d\n", n+1);
//    printf("n+1 = %d\n", 0xe+1);
}

#include <stdio.h>

void main(void)
{
	printf("00211: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
