// fb_card.v -- real RTL for nova_fb's TEXT MODE only (v1 of the C-to-Verilog
// swap scoped in BUILD.txt's bridge design). Bitmap/pixel/sprite/8-bit-bus
// modes stay on the existing C model in nova_fb.c -- see fb_bridge.cpp for
// exactly where this plugs in (fb_present()'s FBT_M_ENABLE branch only).
//
// BUS (two clock domains, on purpose -- see the design scope this
// implements): `clk` is the Nova bus clock, one edge per IOT transaction,
// register semantics matching nova_fb.c's programming model exactly so the
// swap is invisible to every Nova program and every existing testlist:
//
//   reg_sel   0=NONE (NIO, pulse-only)  1=A  2=B  3=C   (matches Nova's own
//             2-bit transfer-type field -- see BUILD.txt's instruction
//             encoding table)
//   we        1 = DO* (write), 0 = DI* (read; NOT IMPLEMENTED in v1 -- this
//             card is write-only, matching gen_modeswitch.py's Nova program,
//             which never issues DIA/DIB/DIC toward device 042)
//   pulse     0=none 1=S 2=C 3=P        (P/present has no RTL meaning here;
//             the bridge captures a frame around it, same as nova_fb.c
//             calling fb_present() only on NIOP)
//
//   DOC (reg_sel=C, we=1)   ctl <= data_in.  Only bit 10 (TEXT, 0002000) and
//                           bit 13 (AUTOINC, 0020000) are implemented -- the
//                           other control bits (PIXEL/SPRITE/BUS8/BANK) are
//                           latched but ignored, matching v1's scope.
//   DOA (reg_sel=A, we=1)   ctl.TEXT=0: addr <= data_in        (word mode)
//                           ctl.TEXT=1: taddr <= data_in[1:0]  (text port)
//   DOB (reg_sel=B, we=1)   ctl.TEXT=0: disp_mem[addr] <= data_in;
//                                       AUTOINC: addr <= addr+1
//                           ctl.TEXT=1: {TEXTPTR,CHARPTR,TCTL}[taddr] <=
//                                       data_in; taddr <= taddr+1 (mod 4)
//
// `pix_clk` is the free-running pixel clock: it scans WIDTH x HEIGHT
// continuously off disp_mem (dual-port in intent -- see the note below) and
// the built-in font ROM, generating hsync/vsync/video_on/mono exactly the
// way fb_text_render() computes fb_front[] today. This is genuinely a
// second clock domain at the port level; fb_bridge.cpp drives it by
// sequencing "apply all pending bus writes, then clock exactly one frame of
// pix_clk" rather than two real OS threads ticking concurrently -- see that
// file for why that is still a faithful exercise of the dual-domain design
// for an on-demand ("render at present-time") integration.
//
// SIMPLIFICATION, same spirit as verilator_vga/src/vga_hello.v's division
// comment: disp_mem is one array read combinationally from the pix_clk
// domain and written synchronously from the clk domain, not real
// synthesizable dual-port BRAM with proper CDC synchronizers. Correct for
// simulation/verification; a tapeout would need real dual-port memory and
// synchronizers on ctl/tctl.
module fb_card #(
    parameter WIDTH = 720,
    parameter HEIGHT = 400,
    parameter H_FRONT = 18,
    parameter H_SYNC = 108,
    parameter H_BACK = 54,
    parameter V_FRONT = 12,
    parameter V_SYNC = 2,
    parameter V_BACK = 35,
    parameter FONT_HEX = "src/nova_charrom.hex"  // relative to the process's cwd at run time
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        cs,
    input  wire [1:0]  reg_sel,
    input  wire        we,
    input  wire [1:0]  pulse,
    input  wire [15:0] data_in,
    output reg  [15:0] data_out,

    input  wire        pix_clk,
    output reg          hsync,
    output reg          vsync,
    output reg          video_on,
    output reg          mono
);

    localparam CELL_H = 16;
    localparam signed [1:0] SEL_NONE = 2'd0, SEL_A = 2'd1, SEL_B = 2'd2, SEL_C = 2'd3;

    localparam CTL_V_TEXT    = 10;
    localparam CTL_V_AUTOINC = 13;

    // ---- bus domain -------------------------------------------------------
    reg [15:0] ctl;
    reg [15:0] addr;
    reg [1:0]  taddr;
    reg [15:0] textptr, charptr, tctl;

    reg [15:0] disp_mem [0:65535];

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            ctl <= 16'd0;
            addr <= 16'd0;
            taddr <= 2'd0;
            textptr <= 16'd0;
            charptr <= 16'd0;
            tctl <= 16'd0;
            data_out <= 16'd0;
        end else if (cs && we) begin
            case (reg_sel)
                SEL_C: ctl <= data_in;
                SEL_A: begin
                    if (ctl[CTL_V_TEXT])
                        taddr <= data_in[1:0];
                    else
                        addr <= data_in;
                end
                SEL_B: begin
                    if (ctl[CTL_V_TEXT]) begin
                        case (taddr)
                            2'd0: textptr <= data_in;
                            2'd1: charptr <= data_in;
                            2'd2: tctl    <= data_in;
                            default: ; // register 3 reserved, matches fb_twrite
                        endcase
                        taddr <= taddr + 2'd1;
                    end else begin
                        disp_mem[addr] <= data_in;
                        if (ctl[CTL_V_AUTOINC])
                            addr <= addr + 16'd1;
                    end
                end
                default: ; // SEL_NONE: no register transfer (NIO/pulse-only)
            endcase
        end
    end

    // ---- pixel domain: timing generator -----------------------------------
    localparam H_TOTAL = WIDTH + H_FRONT + H_SYNC + H_BACK;
    localparam V_TOTAL = HEIGHT + V_FRONT + V_SYNC + V_BACK;

    reg [15:0] hcount, vcount;
    wire hsync_active = (hcount >= WIDTH + H_FRONT) && (hcount < WIDTH + H_FRONT + H_SYNC);
    wire vsync_active = (vcount >= HEIGHT + V_FRONT) && (vcount < HEIGHT + V_FRONT + V_SYNC);
    wire active = (hcount < WIDTH) && (vcount < HEIGHT);

    always @(posedge pix_clk or posedge rst) begin
        if (rst) begin
            hcount <= 16'd0;
            vcount <= 16'd0;
        end else if (hcount == H_TOTAL - 1) begin
            hcount <= 16'd0;
            vcount <= (vcount == V_TOTAL - 1) ? 16'd0 : vcount + 16'd1;
        end else begin
            hcount <= hcount + 16'd1;
        end
    end

    // ---- pixel domain: text renderer, matches fb_text_render() -----------
    reg [15:0] charrom [0:4095];
    initial $readmemh(FONT_HEX, charrom);

    wire [15:0] cellw = tctl[1] ? 16'd9 : 16'd8;           // T_CELL9
    wire [15:0] cols  = WIDTH / cellw;
    wire [15:0] rows  = HEIGHT / CELL_H;
    wire [15:0] col   = hcount / cellw;
    wire [15:0] row   = vcount / CELL_H;
    wire [15:0] scan  = {12'b0, vcount[3:0]};              // CELL_H=16, power of 2
    wire [15:0] c     = hcount % cellw;

    wire [15:0] cell_addr = (textptr + row * cols + col) & 16'hFFFF;
    wire [15:0] cellword = disp_mem[cell_addr];
    wire [7:0]  code = cellword[7:0];
    wire        reverse = cellword[8];
    wire        uline = cellword[9];

    wire [15:0] glyph_addr_rom = {4'b0, code, scan[3:0]};  // code*16 + scan
    wire [15:0] glyph_addr_ram = (charptr + {4'b0, code, 4'b0} + scan) & 16'hFFFF;
    wire [15:0] glyph = (charptr != 16'd0) ? disp_mem[glyph_addr_ram]
                                          : charrom[glyph_addr_rom[11:0]];
    wire [7:0]  bits_raw = glyph[15:8];

    wire linegfx_range = (code >= 8'o300) && (code <= 8'o337);
    wire ninth_raw = (cellw > 16'd8) && tctl[2] && linegfx_range ? bits_raw[0] : 1'b0;

    wire is_uline_row = uline && (scan == CELL_H - 1);
    wire [7:0] bits_u = is_uline_row ? 8'hFF : bits_raw;
    wire       ninth_u = is_uline_row ? 1'b1 : ninth_raw;

    wire [7:0] bits_final = reverse ? ~bits_u : bits_u;
    wire       ninth_final = reverse ? !ninth_u : ninth_u;

    wire pixel_on = tctl[0] &&
                    ((c < 16'd8) ? bits_final[3'd7 - c[2:0]] : ninth_final);

    always @(posedge pix_clk) begin
        hsync    <= ~hsync_active;
        vsync    <= ~vsync_active;
        video_on <= active;
        mono     <= active && pixel_on;
    end

endmodule
