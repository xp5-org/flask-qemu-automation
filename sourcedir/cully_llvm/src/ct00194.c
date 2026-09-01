#include <stdio.h>

int testmain()
{
   int a;
   char b;

   a = 0;
   while (a < 2)
   {
      printf("%d", a++);
      break;

      b = 'A';
      while (b < 'C')
      {
         printf("%c", b++);
      }
      printf("e");
   }
   printf("\n");

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00194: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
