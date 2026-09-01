int
testmain()
{
  int c;
  c = 0;
  do
    ;
  while (0);
  return c;
}

#include <stdio.h>

void main(void)
{
	printf("00101: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
