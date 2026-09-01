/* First smoke test for the nova-llvm-backend (eclipse-clang) pipeline --
   deliberately trivial (mirrors nova_ctestsuite's ct00001.c shape: a
   testmain() returning 0, PASS/FAIL printed via putchar), so a failure
   here points at the toolchain/wiring, not at anything test-logic-shaped. */
#include <stdio.h>

int
testmain()
{
	return 0;
}

int main(void)
{
	putchar('S'); putchar('M'); putchar('O'); putchar('K'); putchar('E');
	putchar('0'); putchar('1'); putchar(':'); putchar(' ');
	if (testmain() == 0) {
		putchar('P'); putchar('A'); putchar('S'); putchar('S');
	} else {
		putchar('F'); putchar('A'); putchar('I'); putchar('L');
	}
	putchar('\n');
	return 0;
}
