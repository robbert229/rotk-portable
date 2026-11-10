/* rotk/divx_decoder.h — reconstructed API of DivxDecoder.dll (DivX 4/5 video codec)
 *
 * Source: REA/Ghidra decompilation of DivxDecoder.dll
 *   sha256 cc68db0409234d3cd2d2282b0e09dff95acb98ea07fddf08f503ec95d17c4971
 *   REA Evidence ev_b570f9bef37e9948ddb3c236df4ea7cb9af7b8a8caef7f8a324867154e03a93d
 * __cdecl observed. Decoder contexts live in global table DAT_10060bc0[slot].
 * Internal dispatcher: FUN_100013b0(ctx, op, out, in) with op 1=init, 5=decode (observed).
 * Tags: [O] observed, [I] inferred, [U] unknown.
 */
#ifndef ROTK_DIVX_DECODER_H
#define ROTK_DIVX_DECODER_H

typedef int DecoderHandle;           /* slot index into decoder table */

/* [O] bool __cdecl InitializeDivxDecoder(int slot) — dispatcher op 1 */
int __cdecl InitializeDivxDecoder(DecoderHandle slot);
/* [I] teardown (imported by DivxMediaLib; body trivial at 0x11f0) */
int __cdecl UnInitializeDivxDecoder(DecoderHandle slot);      /* [U] */

/* [O] uint __cdecl SetOutputFormat(int slot, int fmt, uint w, uint h)
 *     allocates ctx 0x34 bytes if fmt==3 else 0x28 (observed size arithmetic) —
 *     fmt 3 is special-cased (RGB32 output? [U]); fields zeroed then populated. */
unsigned __cdecl SetOutputFormat(DecoderHandle slot, int fmt, unsigned width, unsigned height);

/* [O] bool __cdecl DivxDecode(int slot, uint *out, int *in) — dispatcher op 5.
 *     out: destination frame buffer (as set via DivxSetVideoBuffer chain)
 *     in:  per-frame descriptor (bitstream ptr/size/keyframe? [U]) */
int __cdecl DivxDecode(DecoderHandle slot, unsigned *frame_out, int *frame_in);

#endif /* ROTK_DIVX_DECODER_H */
