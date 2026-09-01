int
testmain()
{
	int arr[2];

	arr[0] = 1;
	arr[1] = 2;

	return arr[0] + arr[1] - 3;
}

#include <stdio.h>

void main(void)
{
	printf("00015: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
