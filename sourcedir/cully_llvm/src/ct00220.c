// this file contains BMP chars encoded in UTF-8
#include <stdio.h>
#include <wchar.h>

int testmain()
{
    wchar_t s[] = L"hello$$你好¢¢世界€€world";
    wchar_t *p;
    for (p = s; *p; p++) printf("%04X ", (unsigned) *p);
    printf("\n");
    return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00220: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
