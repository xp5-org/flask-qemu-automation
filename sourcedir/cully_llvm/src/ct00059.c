int
testmain()
{
	if ('a' != 97)
		return 1;
		
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00059: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
