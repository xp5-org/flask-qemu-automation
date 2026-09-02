// Standalone proof for fb_bridge.cpp's plumbing: reads the binary input
// gen_fb_bridge_test.py wrote (a full disp_words[] + textptr/charptr/tctl,
// exactly the shape nova_fb.c's fb_back[] + registers already are), calls
// fb_bridge_render_text() -- the SAME function nova_fb.c will call -- and
// dumps the result in the packed-mono format verify_fb_card.py already
// knows how to check against verify_frames._expected_text.
#include "fb_bridge.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: fb_bridge_test <input.bin> <out.mono>\n");
        return 2;
    }
    FILE *in = fopen(argv[1], "rb");
    if (!in) {
        fprintf(stderr, "fb_bridge_test: cannot open %s\n", argv[1]);
        return 1;
    }
    uint32_t n_words, width, height;
    uint16_t textptr, charptr, tctl;
    fread(&n_words, 4, 1, in);
    fread(&width, 4, 1, in);
    fread(&height, 4, 1, in);
    fread(&textptr, 2, 1, in);
    fread(&charptr, 2, 1, in);
    fread(&tctl, 2, 1, in);
    std::vector<uint16_t> disp(n_words);
    fread(disp.data(), 2, n_words, in);
    fclose(in);

    int stride_words = width / 16;
    std::vector<uint16_t> front(stride_words * height, 0);

    int ok = fb_bridge_render_text(disp.data(), static_cast<int>(n_words),
                                   static_cast<int>(width), static_cast<int>(height),
                                   textptr, charptr, tctl,
                                   front.data(), static_cast<int>(front.size()));
    if (!ok) {
        fprintf(stderr, "fb_bridge_test: fb_bridge_render_text failed\n");
        return 1;
    }

    // Repack front[] (word-per-16px, bit15=leftmost) into the same
    // byte-packed mono format fb_card_tb.cpp writes.
    int stride_bytes = (width + 7) / 8;
    std::vector<uint8_t> mono(stride_bytes * height, 0);
    for (uint32_t y = 0; y < height; y++) {
        for (uint32_t x = 0; x < width; x++) {
            uint16_t w = front[y * stride_words + x / 16];
            int bit = 15 - (x % 16);
            if ((w >> bit) & 1)
                mono[y * stride_bytes + x / 8] |= (0x80 >> (x % 8));
        }
    }

    FILE *out = fopen(argv[2], "wb");
    uint32_t w32 = width, h32 = height;
    fwrite(&w32, 4, 1, out);
    fwrite(&h32, 4, 1, out);
    fwrite(mono.data(), 1, mono.size(), out);
    fclose(out);
    printf("fb_bridge_test: wrote %s\n", argv[2]);
    return 0;
}
