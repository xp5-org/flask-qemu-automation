#include <stdio.h>	// printf()

#define CAT2(a,b) a##b
#define CAT(a,b) CAT2(a,b)
#define AB(x) CAT(x,y)

int testmain(void)
{
  int xy = 42;
  printf("%d\n", CAT(A,B)(x));
  return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00201: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
