// fb_bridge.cpp -- C++ implementation of fb_bridge.h: drives the real
// fb_card.v RTL (Verilated) over its actual bus port, synchronously, once
// per fb_present() call -- same cadence nova_fb.c already uses for
// fb_text_render(), so no threading is needed (see verilator_common/
// bus_bridge.hpp's header comment for when that WOULD be needed -- a
// continuously-live design, which this on-demand integration isn't).
#include "fb_bridge.h"
#include "Vfb_card.h"
#include "verilated.h"

#include <cstring>
#include <vector>

namespace {

const int SUPPORTED_WIDTH = 720;
const int SUPPORTED_HEIGHT = 400;

const int SEL_NONE = 0, SEL_A = 1, SEL_B = 2, SEL_C = 3;
const uint16_t CTL_TEXT = 0002000;         // matches fb_card.v's CTL_V_TEXT (bit 10)
const uint16_t CTL_WORD_AUTOINC = 0020000; // matches CTL_V_AUTOINC (bit 13)

const int CELL_H = 16;
const int CHAR_W = 8;
const int T_CELL9 = 0002;
const int FONT_WORDS = 256 * CELL_H;       // 4096, matches src/nova_charrom.hex

Vfb_card *g_dut = nullptr;
bool g_argsInit = false;

void bus_edge(Vfb_card *dut, int reg_sel, int we, int pulse, uint16_t data) {
    dut->cs = 1;
    dut->reg_sel = reg_sel;
    dut->we = we;
    dut->pulse = pulse;
    dut->data_in = data;
    dut->clk = 0;
    dut->eval();
    dut->clk = 1;
    dut->eval();
    dut->cs = 0;
    dut->clk = 0;
    dut->eval();
}

Vfb_card *dut() {
    if (g_dut == nullptr) {
        if (!g_argsInit) {
            static const char *argv0 = "fb_bridge";
            Verilated::commandArgs(1, &argv0);
            g_argsInit = true;
        }
        g_dut = new Vfb_card;
        g_dut->rst = 1;
        g_dut->clk = 0;
        g_dut->pix_clk = 0;
        g_dut->eval();
        g_dut->clk = 1;
        g_dut->pix_clk = 1;
        g_dut->eval();
        g_dut->rst = 0;
        g_dut->cs = 0;
    }
    return g_dut;
}

}  // namespace

extern "C" int fb_bridge_render_text(const uint16_t *disp_words, int n_words,
                                     int width, int height,
                                     uint16_t textptr, uint16_t charptr, uint16_t tctl,
                                     uint16_t *out_front, int out_words) {
    if (width != SUPPORTED_WIDTH || height != SUPPORTED_HEIGHT) return 0;
    if (n_words <= 0 || disp_words == nullptr) return 0;

    Vfb_card *top = dut();

    int cellw = (tctl & T_CELL9) ? 9 : CHAR_W;
    int cols = width / cellw;
    int rows = height / CELL_H;

    // 1. Word mode, autoinc: mirror the text buffer into the RTL's own
    //    display memory over the real DOA/DOB bus port -- the same words
    //    fb_text_render() reads out of fb_back[] today, just handed across
    //    a bus transaction instead of a C array index.
    bus_edge(top, SEL_C, 1, 0, CTL_WORD_AUTOINC);
    bus_edge(top, SEL_A, 1, 0, textptr);
    for (int i = 0; i < cols * rows; i++) {
        uint16_t w = disp_words[(textptr + i) % n_words];
        bus_edge(top, SEL_B, 1, 0, w);
    }

    // 2. If a custom font is in play, mirror that table too.
    if (charptr != 0) {
        bus_edge(top, SEL_C, 1, 0, CTL_WORD_AUTOINC);
        bus_edge(top, SEL_A, 1, 0, charptr);
        for (int i = 0; i < FONT_WORDS; i++) {
            uint16_t w = disp_words[(charptr + i) % n_words];
            bus_edge(top, SEL_B, 1, 0, w);
        }
    }

    // 3. Text register port: TEXTPTR, CHARPTR, TCTL.
    bus_edge(top, SEL_C, 1, 0, CTL_TEXT);
    bus_edge(top, SEL_A, 1, 0, 0);
    bus_edge(top, SEL_B, 1, 0, textptr);
    bus_edge(top, SEL_B, 1, 0, charptr);
    bus_edge(top, SEL_B, 1, 0, tctl);

    // 4. Present: clock the pixel domain through exactly one frame,
    //    packing bits into out_front the same way fb_front[] already is
    //    (bit 15 = leftmost, WIDTH/16 words per row).
    int stride_words = width / 16;
    int need_words = stride_words * height;
    if (out_front == nullptr || out_words < need_words) return 0;
    std::memset(out_front, 0, sizeof(uint16_t) * need_words);

    long pixel_idx = 0;
    long total = static_cast<long>(width) * height;
    long cycles = 0;
    const long MAX_CYCLES = 2000L * 600L * 3L;
    while (pixel_idx < total && cycles < MAX_CYCLES) {
        top->pix_clk = 0;
        top->eval();
        top->pix_clk = 1;
        top->eval();
        cycles++;
        if (top->video_on) {
            long x = pixel_idx % width;
            long y = pixel_idx / width;
            if (top->mono) {
                int word = static_cast<int>(y) * stride_words + static_cast<int>(x / 16);
                int bit = 15 - static_cast<int>(x % 16);
                out_front[word] |= static_cast<uint16_t>(1u << bit);
            }
            pixel_idx++;
        }
    }
    if (pixel_idx < total) return 0;  // timing generator didn't complete a frame

    return 1;
}
