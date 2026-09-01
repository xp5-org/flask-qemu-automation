#include <stdio.h>

int testmain()
{
   int a;
   int p;
   int t;

   a = 1;
   p = 0;
   t = 0;

   do
   {
      printf("%d\n", a);
      t = a;
      a = t + p;
      p = t;
   } while (a < 100);

   return 0;
}

// vim: set expandtab ts=4 sw=3 sts=3 tw=80 :

#include <stdio.h>

void main(void)
{
	printf("00161: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
