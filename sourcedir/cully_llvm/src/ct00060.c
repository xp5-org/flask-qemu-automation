// line comment

int
testmain()
{
	/*
		multiline
		comment
	*/
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00060: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
