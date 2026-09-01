struct {
	enum { X } x;
} s;


int
testmain()
{
	return X;
}

#include <stdio.h>

void main(void)
{
	printf("00120: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
