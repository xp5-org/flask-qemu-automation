/* fb_bridge.h -- C-callable entry point from nova_fb.c into the real
   fb_card.v RTL (Verilated), replacing fb_text_render()'s C logic for the
   ONE resolution nova_fb.textmode actually uses.

   nova_fb.c is plain C (SIMH's convention); fb_bridge.cpp is C++ (it links
   the Verilated model + verilated.cpp). This header is the seam: nova_fb.c
   includes it and calls fb_bridge_render_text() exactly where it used to
   call fb_text_render(), with no other change to the IOT decode path,
   fb_back[]/fb_front[] storage, or sprite compositing -- those stay on the
   original C model unmodified. See BUILD.txt's "VERILATOR BRIDGE" section
   for the full scope (bitmap/pixel/sprite modes are NOT covered by this).

   WIDTH/HEIGHT are Verilog PARAMETERS in fb_card.v (elaborated once, at
   build time), not bus registers -- matching the real card, where they are
   set by SET FB WIDTH/HEIGHT, not something a Nova program can change. v1
   only elaborates the model at 720x400 (what modeswitch.ini uses --
   "ONE RESOLUTION, DELIBERATELY", see gen_modeswitch.py). Any other
   WIDTH/HEIGHT makes fb_bridge_render_text() return 0 immediately; the
   caller falls back to fb_text_render(). */
#ifndef FB_BRIDGE_H
#define FB_BRIDGE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* disp_words/n_words: the card's full display memory (fb_back), so the
   bridge can read out exactly the text buffer and (if CHARPTR != 0) the
   custom font table -- the same words fb_text_render() reads today, over
   the RTL's real DOA/DOB bus port, not by peeking at Verilated internals.

   out_front/out_words: filled with the rendered frame in fb_front[]'s own
   layout (bit 15 = leftmost pixel, WIDTH/16 words per row), so
   fb_composite()/fb_live_publish()/the PNG writer need no changes.

   Returns 1 on success, 0 if (width, height) isn't the supported
   resolution -- the caller must fall back to fb_text_render() in that case. */
int fb_bridge_render_text(const uint16_t *disp_words, int n_words,
                          int width, int height,
                          uint16_t textptr, uint16_t charptr, uint16_t tctl,
                          uint16_t *out_front, int out_words);

#ifdef __cplusplus
}
#endif

#endif /* FB_BRIDGE_H */
