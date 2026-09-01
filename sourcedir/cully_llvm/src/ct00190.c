#include <stdio.h>

void fred(void)
{
   printf("yo\n");
}

int testmain()
{
   fred();

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00190: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
