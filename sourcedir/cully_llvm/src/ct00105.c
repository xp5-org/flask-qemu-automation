int
testmain()
{
	int i;

	for(i = 0; i < 10; i++)
		if (!i)
			continue;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00105: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
