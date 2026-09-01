#include <stdio.h>
#include <string.h>

int testmain()
{
   char a[10];
   strcpy(a, "abcdef");
   printf("%s\n", &a[1]);

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00180: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
