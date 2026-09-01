int strlen(char *);

int
testmain()
{
	char *p;
	
	p = "hello";
	return strlen(p) - 5;
}

#include <stdio.h>

void main(void)
{
	printf("00025: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
