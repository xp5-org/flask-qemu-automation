/*
 * BLAHAJ.C -- DJGPP + Allegro multi-light 3D demo.
 *   - triangle3d_f() with POLYTYPE_GRGB, which interpolates a full RGB
 *     triplet across each triangle 
 *   - get_rotation_matrix_f()/apply_matrix_f() for the per-frame transform
 *
 * GRGB in a 256-colour mode needs a prepared rgb_map, so this demo asks for
 * a truecolor mode and refuses to run without one (see set_video_mode).
 *
 * SPACE = pause spin, W = wireframe/solid, R = cycle
 * resolution 640x480 default, 800x600, 1024x768, Q/Esc = quit.
 *
 * The flask-testrunner is non-interactive, so startup prints a text banner
 * containing OCR-verifiable "BLAHAJ READY" before switching to graphics,
 * and quitting prints "BLAHAJ DONE".
 *
 * Build: see COMPILE.BAT.
 */

#include <allegro.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <dpmi.h>

#include "shark.h"
#include "letters.h"

static int g_w = 640, g_h = 480;

#define MAX_LETTER_TRIS (WORD_LEN * MAX_STROKES * 12)
#define MAX_TRIS        (SHARK_NTRIS + MAX_LETTER_TRIS)

#define GROUP_SHARK 0
#define GROUP_TEXT  1

typedef struct {
    float p[3][3];
    float n[3][3];
    float alb[3][3];
    int group;
} MTri;

static MTri g_tris[MAX_TRIS];
static int g_ntris = 0;

typedef struct {
    float depth;
    int sx[3], sy[3];
    int c[3];
} DrawTri;

static DrawTri g_draw[MAX_TRIS];
static int g_ndraw = 0;

#define NLIGHTS 3

static float g_light_dir[NLIGHTS][3] = {
    {-1.00f, 0.10f, -0.25f},   /* red   -- from the left   */
    { 1.00f, 0.10f, -0.25f},   /* blue  -- from the right  */
    { 0.00f, 0.80f, -0.45f},   /* green -- from the middle */
};

static const float g_light_col[NLIGHTS][3] = {
    {255.0f,  40.0f,  40.0f},
    { 40.0f,  60.0f, 255.0f},
    { 40.0f, 255.0f,  80.0f},
};

static const float g_text_albedo[3] = {235.0f, 226.0f, 216.0f};

#define AMBIENT   0.07f
#define LIGHT_GAIN 0.62f
#define GLOBAL_FILL 0.30f

/* ------------------------------------------------------------------ */
static float dot3(const float a[3], const float b[3]) {
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
}

static void cross3(const float a[3], const float b[3], float out[3]) {
    out[0] = a[1]*b[2] - a[2]*b[1];
    out[1] = a[2]*b[0] - a[0]*b[2];
    out[2] = a[0]*b[1] - a[1]*b[0];
}

static void normalize3(float v[3]) {
    float len = (float)sqrt(dot3(v, v));
    if (len > 0.0001f) { v[0] /= len; v[1] /= len; v[2] /= len; }
}

static int light_vertex(const float n[3], const float alb[3], float global_fill) {
    float acc[3];
    int i, l, out[3];

    acc[0] = acc[1] = acc[2] = 0.0f;
    for (l = 0; l < NLIGHTS; l++) {
        float d = dot3(n, g_light_dir[l]);
        float s;
        if (d < 0.0f) d = 0.0f;
        s = (AMBIENT + (1.0f - AMBIENT) * d) * LIGHT_GAIN;
        for (i = 0; i < 3; i++)
            acc[i] += (alb[i] / 255.0f) * g_light_col[l][i] * s;
    }
    if (global_fill > 0.0f)
        for (i = 0; i < 3; i++)
            acc[i] += alb[i] * global_fill;

    for (i = 0; i < 3; i++) {
        out[i] = (int)acc[i];
        if (out[i] < 0) out[i] = 0;
        if (out[i] > 255) out[i] = 255;
    }
    return (out[0] << 16) | (out[1] << 8) | out[2];
}

static void add_tri(const float a[3], const float b[3], const float c[3],
                    const float na[3], const float nb[3], const float nc[3],
                    const float alba[3], const float albb[3], const float albc[3],
                    int group) {
    MTri *t;
    int i;
    if (g_ntris >= MAX_TRIS) return;
    t = &g_tris[g_ntris++];
    for (i = 0; i < 3; i++) {
        t->p[0][i] = a[i]; t->p[1][i] = b[i]; t->p[2][i] = c[i];
        t->n[0][i] = na[i]; t->n[1][i] = nb[i]; t->n[2][i] = nc[i];
        t->alb[0][i] = alba[i]; t->alb[1][i] = albb[i]; t->alb[2][i] = albc[i];
    }
    t->group = group;
}

static void add_quad_flat(const float a[3], const float b[3],
                          const float c[3], const float d[3],
                          const float n[3], const float alb[3], int group) {
    add_tri(a, b, c, n, n, n, alb, alb, alb, group);
    add_tri(a, c, d, n, n, n, alb, alb, alb, group);
}

/* Extrude one axis-aligned rectangle into a box: 6 faces, 12 triangles.
 * Corners are wound so every face's normal points outward */
static void extrude_rect(float x0, float y0, float x1, float y1,
                         float z0, float z1, const float alb[3], int group) {
    float v[8][3];
    int i;
    static const float nx_pos[3] = { 1, 0, 0}, nx_neg[3] = {-1, 0, 0};
    static const float ny_pos[3] = { 0, 1, 0}, ny_neg[3] = { 0,-1, 0};
    static const float nz_pos[3] = { 0, 0, 1}, nz_neg[3] = { 0, 0,-1};

    for (i = 0; i < 8; i++) {
        v[i][0] = (i & 1) ? x1 : x0;
        v[i][1] = (i & 2) ? y1 : y0;
        v[i][2] = (i & 4) ? z1 : z0;
    }

    add_quad_flat(v[0], v[2], v[3], v[1], nz_neg, alb, group);   /* back  (-z) */
    add_quad_flat(v[4], v[5], v[7], v[6], nz_pos, alb, group);   /* front (+z) */
    add_quad_flat(v[0], v[1], v[5], v[4], ny_neg, alb, group);   /* bottom     */
    add_quad_flat(v[2], v[6], v[7], v[3], ny_pos, alb, group);   /* top        */
    add_quad_flat(v[0], v[4], v[6], v[2], nx_neg, alb, group);   /* left       */
    add_quad_flat(v[1], v[3], v[7], v[5], nx_pos, alb, group);   /* right      */
}

#define LETTER_SCALE (0.155f * 0.75f)   /* 25% smaller */
#define LETTER_ADV   3.7f      /* glyph pitch in grid units */
#define LETTER_DEPTH 0.8f
#define TEXT_Y      -0.85f     /* sits below the shark */

#define SHARK_SCALE 2.0f

static void build_geometry(void) {
    int i, g, s;
    float word_w, x_origin;

    for (i = 0; i < SHARK_NTRIS; i++) {
        const int *t = g_shark_tris[i];
        float sp[3][3];
        int j, k;
        for (j = 0; j < 3; j++)
            for (k = 0; k < 3; k++)
                sp[j][k] = g_shark_verts[t[j]][k] * SHARK_SCALE;
        add_tri(sp[0], sp[1], sp[2],
                g_shark_normals[t[0]], g_shark_normals[t[1]], g_shark_normals[t[2]],
                g_shark_albedo[t[0]], g_shark_albedo[t[1]], g_shark_albedo[t[2]],
                GROUP_SHARK);
    }

    word_w = (WORD_LEN - 1) * LETTER_ADV + 3.0f;
    x_origin = -word_w / 2.0f;

    for (i = 0; i < WORD_LEN; i++) {
        g = g_word[i];
        for (s = 0; s < MAX_STROKES; s++) {
            const float *r = g_glyph_strokes[g][s];
            float x0, y0, x1, y1;
            /* All-zero slots are unused stroke entries. */
            if (r[0] == 0.0f && r[1] == 0.0f && r[2] == 0.0f && r[3] == 0.0f)
                continue;
            x0 = (x_origin + i * LETTER_ADV + r[0]) * LETTER_SCALE;
            x1 = (x_origin + i * LETTER_ADV + r[2]) * LETTER_SCALE;
            /* Grid y runs 0..5 from the baseline; recentre on the glyph. */
            y0 = (r[1] - 2.5f) * LETTER_SCALE + TEXT_Y;
            y1 = (r[3] - 2.5f) * LETTER_SCALE + TEXT_Y;
            extrude_rect(x0, y0, x1, y1,
                         -LETTER_DEPTH * LETTER_SCALE,
                          LETTER_DEPTH * LETTER_SCALE,
                         g_text_albedo, GROUP_TEXT);
        }
    }
}

#define CAM_D 4.5f
#define FOV_BASE 260.0f
#define REF_H    480.0f

static void project(const float p[3], int *sx, int *sy) {
    float fov = FOV_BASE * (float)g_h / REF_H;
    float z = p[2] + CAM_D;
    if (z < 0.1f) z = 0.1f;
    *sx = (int)(g_w / 2 + p[0] * fov / z);
    *sy = (int)(g_h / 2 - p[1] * fov / z);
}

/* Allegro's rotation matrices take binary angles: 256 to a full circle,
 * not radians and not degrees. */
static float rad_to_binary(float rad) {
    return rad * (256.0f / (2.0f * (float)M_PI));
}

static int cmp_depth(const void *a, const void *b) {
    float d = ((const DrawTri *)a)->depth - ((const DrawTri *)b)->depth;
    /* Farthest (largest camera z) first, so nearer triangles overpaint. */
    if (d > 0.0f) return -1;
    if (d < 0.0f) return 1;
    return 0;
}

static void build_draw_list(float sa, float ta) {
    MATRIX_f m[2];
    int i, k;

    get_rotation_matrix_f(&m[GROUP_SHARK], rad_to_binary(sa * 0.6f),
                          rad_to_binary(sa), rad_to_binary(sa * 0.25f));
    get_rotation_matrix_f(&m[GROUP_TEXT], 0.0f, rad_to_binary(ta), 0.0f);

    g_ndraw = 0;
    for (i = 0; i < g_ntris; i++) {
        const MTri *t = &g_tris[i];
        const MATRIX_f *mm = &m[t->group];
        float p[3][3], n[3][3], e1[3], e2[3], fn[3];
        DrawTri *d;

        for (k = 0; k < 3; k++) {
            apply_matrix_f(mm, t->p[k][0], t->p[k][1], t->p[k][2],
                           &p[k][0], &p[k][1], &p[k][2]);
            /* A pure rotation has no translation and no scale, so normals
             * transform with the same matrix as positions. */
            apply_matrix_f(mm, t->n[k][0], t->n[k][1], t->n[k][2],
                           &n[k][0], &n[k][1], &n[k][2]);
        }

        /* Backface cull on the geometric face normal (not the smooth vertex
         * normals, which don't say which way the facet itself points). The
         * camera sits at -z looking toward +z, so outward-facing means -z. */
        for (k = 0; k < 3; k++) {
            e1[k] = p[1][k] - p[0][k];
            e2[k] = p[2][k] - p[0][k];
        }
        cross3(e1, e2, fn);
        if (fn[2] >= 0.0f) continue;

        d = &g_draw[g_ndraw++];
        d->depth = (p[0][2] + p[1][2] + p[2][2]) / 3.0f;
        for (k = 0; k < 3; k++) {
            project(p[k], &d->sx[k], &d->sy[k]);
            d->c[k] = light_vertex(n[k], t->alb[k],
                                   t->group == GROUP_SHARK ? GLOBAL_FILL : 0.0f);
        }
    }

    qsort(g_draw, g_ndraw, sizeof(DrawTri), cmp_depth);
}

static void render(BITMAP *buf, int wireframe) {
    int i;
    for (i = 0; i < g_ndraw; i++) {
        const DrawTri *d = &g_draw[i];
        if (wireframe) {
            int col = makecol((d->c[0] >> 16) & 0xFF,
                              (d->c[0] >> 8) & 0xFF,
                              d->c[0] & 0xFF);
            line(buf, d->sx[0], d->sy[0], d->sx[1], d->sy[1], col);
            line(buf, d->sx[1], d->sy[1], d->sx[2], d->sy[2], col);
            line(buf, d->sx[2], d->sy[2], d->sx[0], d->sy[0], col);
        } else {
            V3D_f v[3];
            int k;
            for (k = 0; k < 3; k++) {
                v[k].x = (float)d->sx[k];
                v[k].y = (float)d->sy[k];
                v[k].z = 1.0f;
                v[k].u = v[k].v = 0.0f;
                v[k].c = d->c[k];
            }
            triangle3d_f(buf, POLYTYPE_GRGB, NULL, &v[0], &v[1], &v[2]);
        }
    }
}


static volatile int g_ticks = 0;
static void tick(void) { g_ticks++; }
END_OF_STATIC_FUNCTION(tick);


static unsigned long g_mem_free_kb = 0, g_mem_total_kb = 0;
static int g_mem_known = 0;

static void update_mem_info(void) {
    __dpmi_free_mem_info info;
    if (__dpmi_get_free_memory_information(&info) != 0)
        return;
    /* A DPMI host that doesn't track one of these returns -1 in that field
     * (documented DPMI 0.9 behaviour) -- only trust fields that are real. */
    g_mem_known = (info.total_number_of_free_pages != 0xFFFFFFFFUL &&
                  info.total_number_of_physical_pages != 0xFFFFFFFFUL);
    if (g_mem_known) {
        g_mem_free_kb  = info.total_number_of_free_pages * 4UL;
        g_mem_total_kb = info.total_number_of_physical_pages * 4UL;
    }
}


static const int g_modes[][2] = {
    {640, 480}, {800, 600}, {1024, 768},
};
#define NMODES ((int)(sizeof(g_modes) / sizeof(g_modes[0])))
static int g_mode_idx = 0;


static int try_video_mode(int idx) {
    static const int depths[2] = {16, 32};
    int d;

    for (d = 0; d < 2; d++) {
        set_color_depth(depths[d]);
        if (set_gfx_mode(GFX_AUTODETECT, g_modes[idx][0], g_modes[idx][1],
                         0, 0) == 0) {
            g_w = g_modes[idx][0];
            g_h = g_modes[idx][1];
            g_mode_idx = idx;
            return depths[d];
        }
    }
    return 0;
}

/* Startup: scan forward from the default (640x480) so a VESA BIOS that's
 * missing the default still gets something rather than refusing to run. */
static int set_video_mode(void) {
    int m;
    for (m = 0; m < NMODES; m++) {
        int depth = try_video_mode(m);
        if (depth) return depth;
    }
    return 0;
}

static int startup_banner(void) {
    int waited;

    printf("\n  BLAHAJ - DJGPP + Allegro multi-light 3D demo\n");
    printf("  ==============================================\n\n");
    printf("  %d triangles: %d mesh + %d extruded letters\n\n",
           g_ntris, SHARK_NTRIS, g_ntris - SHARK_NTRIS);
    printf("  Lights:  RED from the left,  BLUE from the right,\n");
    printf("           GREEN from the middle\n\n");
    printf("  Controls:  SPACE = pause spin   W = wireframe/solid\n");
    printf("             R = resolution (640x480/800x600/1024x768)\n");
    printf("             Q / Esc = quit\n\n");
    printf("  BLAHAJ READY\n");
    printf("  Starting graphics in a moment (press any key to skip)...\n");

    for (waited = 0; waited < 40; waited++) {
        if (keypressed()) { readkey(); return 1; }
        rest(100);
    }
    return 0;
}

int main(void) {
    BITMAP *buffer;
    float sa = 0.4f, ta = 0.0f;
    int running = 1, spinning = 1, wireframe = 0;
    int depth, fps = 0, frames = 0, last_ticks = 0;
    int i;

    if (allegro_init() != 0) {
        printf("allegro_init failed\n");
        return 1;
    }
    install_keyboard();
    install_timer();

    LOCK_VARIABLE(g_ticks);
    LOCK_FUNCTION(tick);
    install_int_ex(tick, BPS_TO_TIMER(100));

    for (i = 0; i < NLIGHTS; i++) normalize3(g_light_dir[i]);
    build_geometry();

    if (startup_banner()) {
        printf("\n  BLAHAJ DONE\n");
        return 0;
    }

    depth = set_video_mode();
    if (!depth) {
        set_gfx_mode(GFX_TEXT, 0, 0, 0, 0);
        printf("\n  NEED TRUECOLOR - no 16bpp or 32bpp mode available\n");
        printf("  (%s)\n", allegro_error);
        printf("\n  BLAHAJ DONE\n");
        return 1;
    }

    buffer = create_bitmap(g_w, g_h);
    if (!buffer) {
        set_gfx_mode(GFX_TEXT, 0, 0, 0, 0);
        printf("failed to allocate back buffer\n");
        return 1;
    }

    update_mem_info();

    while (running) {
        if (keypressed()) {
            int k = readkey() >> 8;
            if (k == KEY_Q || k == KEY_ESC) { running = 0; continue; }
            else if (k == KEY_SPACE) { spinning = !spinning; }
            else if (k == KEY_W) { wireframe = !wireframe; }
            else if (k == KEY_R) {
                int next = (g_mode_idx + 1) % NMODES;
                int new_depth = try_video_mode(next);
                if (!new_depth) {
                    /* That size isn't available at either depth -- put the
                     * previous mode back */
                    new_depth = try_video_mode(g_mode_idx);
                }
                if (new_depth) {
                    depth = new_depth;
                    destroy_bitmap(buffer);
                    buffer = create_bitmap(g_w, g_h);
                }
            }
        }

        if (spinning) {
            sa += 0.025f;
            ta += 0.018f;
        }

        build_draw_list(sa, ta);

        clear_to_color(buffer, makecol(6, 6, 12));
        render(buffer, wireframe);

        if (++frames >= 20) {
            int now = g_ticks;
            if (now > last_ticks)
                fps = (frames * 100) / (now - last_ticks);
            last_ticks = now;
            frames = 0;
            update_mem_info();
        }

        textprintf_ex(buffer, font, 4, 4, makecol(235, 235, 235), -1,
                      "%dtri %dfps %dbpp %s",
                      g_ndraw, fps, depth, wireframe ? "wire" : "solid");
        if (g_mem_known)
            textprintf_ex(buffer, font, 4, 16, makecol(190, 220, 255), -1,
                          "MEM %luK free / %luK used",
                          g_mem_free_kb, g_mem_total_kb - g_mem_free_kb);
        else
            textprintf_ex(buffer, font, 4, 16, makecol(190, 220, 255), -1,
                          "MEM: unknown (DPMI host doesn't report it)");
        textprintf_ex(buffer, font, 4, g_h - 12, makecol(160, 160, 170), -1,
                      "SPACE pause  W wire  R res  Q quit");

        vsync();
        blit(buffer, screen, 0, 0, 0, 0, g_w, g_h);
    }

    destroy_bitmap(buffer);
    set_gfx_mode(GFX_TEXT, 0, 0, 0, 0);
    printf("\n  BLAHAJ DONE\n");
    return 0;
}
END_OF_MAIN()
