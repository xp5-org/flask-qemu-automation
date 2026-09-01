#if 0 != (0 && (0/0))
   #error 0 != (0 && (0/0))
#endif

#if 1 != (-1 || (0/0))
   #error 1 != (-1 || (0/0))
#endif

#if 3 != (-1 ? 3 : (0/0))
   #error 3 != (-1 ? 3 : (0/0))
#endif

int
testmain()
{
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00145: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
