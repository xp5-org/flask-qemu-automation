// Standalone Verilator testbench for fb_card.v -- NOT part of the SIMH
// bridge. Replays a bus transaction script (gen_fb_card_test.py) over the
// exact bus fb_card.v exposes, and on a PULSE_P (present) transaction,
// clocks pix_clk through exactly one frame and dumps the captured mono
// bitmap for verify_fb_card.py to check against an independent recompute.
//
// This is the proof step before fb_card.v is wired into nova_fb.c: it
// exercises the real bus protocol and the real pixel-domain scanout, with
// no SIMH/C-bridge involved yet.
#include "Vfb_card.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

static void bus_edge(Vfb_card *top, int reg_sel, int we, int pulse, int data) {
    top->cs = 1;
    top->reg_sel = reg_sel;
    top->we = we;
    top->pulse = pulse;
    top->data_in = data;
    top->clk = 0;
    top->eval();
    top->clk = 1;
    top->eval();
    top->cs = 0;
    top->clk = 0;
    top->eval();
}

static void pix_edge(Vfb_card *top) {
    top->pix_clk = 0;
    top->eval();
    top->pix_clk = 1;
    top->eval();
}

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 5) {
        fprintf(stderr, "usage: fb_card_tb <script> <out.mono> <width> <height>\n");
        return 2;
    }
    std::string script_path = argv[1];
    std::string out_path = argv[2];
    int width = atoi(argv[3]);
    int height = atoi(argv[4]);

    Vfb_card *top = new Vfb_card;
    top->rst = 1;
    top->clk = 0;
    top->pix_clk = 0;
    top->eval();
    top->clk = 1;
    top->pix_clk = 1;
    top->eval();
    top->rst = 0;
    top->cs = 0;

    std::ifstream f(script_path);
    if (!f) {
        fprintf(stderr, "fb_card_tb: cannot open %s\n", script_path.c_str());
        return 1;
    }

    std::vector<uint8_t> mono;  // packed rows, MSB = leftmost, matches nova_fb.c
    int stride = (width + 7) / 8;
    bool captured = false;

    std::string line;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        std::istringstream iss(line);
        int reg_sel, we, pulse, data;
        iss >> reg_sel >> we >> pulse >> data;
        bus_edge(top, reg_sel, we, pulse, data);

        if (pulse == 3 /* P: present */) {
            // Clock the pixel domain through exactly one frame, capturing
            // active-video pixels in raster order -- same technique as
            // verilator_vga's vga_tb.cpp.
            mono.assign(static_cast<size_t>(stride) * height, 0);
            long pixel_idx = 0;
            long total = static_cast<long>(width) * height;
            long cycles = 0;
            const long MAX_CYCLES = 2000L * 600L * 3L;
            while (pixel_idx < total && cycles < MAX_CYCLES) {
                pix_edge(top);
                cycles++;
                if (top->video_on) {
                    long x = pixel_idx % width;
                    long y = pixel_idx / width;
                    if (top->mono) {
                        size_t byte_idx = static_cast<size_t>(y) * stride + (x / 8);
                        mono[byte_idx] |= (0x80 >> (x % 8));
                    }
                    pixel_idx++;
                }
            }
            if (pixel_idx < total) {
                fprintf(stderr, "fb_card_tb: FAILED to capture a full frame "
                        "(%ld/%ld pixels in %ld cycles)\n", pixel_idx, total, cycles);
                delete top;
                return 1;
            }
            captured = true;
        }
    }

    if (!captured) {
        fprintf(stderr, "fb_card_tb: script never issued a present pulse\n");
        delete top;
        return 1;
    }

    FILE *out = fopen(out_path.c_str(), "wb");
    if (!out) {
        fprintf(stderr, "fb_card_tb: cannot open %s for writing\n", out_path.c_str());
        delete top;
        return 1;
    }
    uint32_t w32 = width, h32 = height;
    fwrite(&w32, 4, 1, out);
    fwrite(&h32, 4, 1, out);
    fwrite(mono.data(), 1, mono.size(), out);
    fclose(out);

    printf("fb_card_tb: captured %dx%d -> %s\n", width, height, out_path.c_str());
    delete top;
    return 0;
}
