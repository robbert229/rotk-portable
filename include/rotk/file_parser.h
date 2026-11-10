/* rotk/file_parser.h — reconstructed API of FileParser.dll (AVI splitter for DIVX 5 FMVs)
 *
 * Source: REA/Ghidra decompilation of FileParser.dll
 *   sha256 196fb53afbf15c02ffc27cba3b4b7ad66b632e70ad68427d042813a8996acf67
 *   REA Evidence ev_7bbf06882e42bc2566bbd3a8ee435d387b6752a89c42fd81f637329c3c840cb7
 * Calling convention: __cdecl (observed). All stream functions take a slot index;
 * splitter table stride 0x58 bytes (observed), buffer-manager table stride 0x78 (observed).
 * Tags: [O] observed decompile, [I] inferred, [U] unknown.
 */
#ifndef ROTK_FILE_PARSER_H
#define ROTK_FILE_PARSER_H

typedef int SplitterHandle;          /* slot index into DAT_10013820 table */
#define FP_E_OUTOFMEM   500          /* observed: divxSplitterFileParse malloc fail */
#define FP_E_BADCFG     0x1f7        /* observed: divxBufManagerInit unconfigured counts */

/* [O] uint __cdecl divxBufManagerInit(uint slot, LPCSTR path)
 *     requires counts set via divxSetAudVidBuffers first; zeroes 0x78-byte slot,
 *     opens file handle for buffered reads. */
int __cdecl divxBufManagerInit(SplitterHandle h, const char *path);
/* [I] teardown */
int __cdecl divxBufManagerUnInit(SplitterHandle h);           /* [U] */

/* [O] divxSplitterFileParse(LPCSTR path, int, int slot, u32, u32, u32 a6)
 *     mallocs 0x88-byte parse context, parses RIFF/AVI (hdrstr + movi + idx1),
 *     stores slot config (a4→+0x3C, a5→+0x54, a6→+0x1C); sets last error from
 *     ctx+0x80 on failure. */
int __cdecl divxSplitterFileParse(const char *path, int a2, SplitterHandle h,
                                  unsigned a4, unsigned a5, unsigned a6);
/* [I] */
int __cdecl divxSplitterInit(SplitterHandle h);               /* [U] */
int __cdecl divxSplitterUninitialise(SplitterHandle h);       /* [U] */

/* [I] */
int __cdecl divxSetAudVidBuffers(unsigned nvid, unsigned naud); /* [U] — feeds globals checked by BufManagerInit */
int __cdecl divxFrameReady(SplitterHandle h);                 /* [U] */
int __cdecl divxReadFrame(SplitterHandle h);                  /* [U] */
int __cdecl divxLocateVideoFrame(SplitterHandle h, int frame);/* [U] */
int __cdecl divxLocateAudioFrame(SplitterHandle h, int pos);  /* [U] */
int __cdecl divxFillVideoDecodeBuffer(SplitterHandle h);      /* [U] */
int __cdecl divxFillAudioDecodeBuffer(SplitterHandle h);      /* [U] */
int __cdecl divxSetToStart(SplitterHandle h);                 /* [U] */

/* [O] divxGetContentInfo(int slot, u32 out[10+]) fills ≥10 dwords:
 *     out[0..1] ← ctx+0x8, ctx+0xC (video dims candidates)
 *     out[2..4] ← slot+0x20/0x24/0x28
 *     out[5..9] ← getters FUN_100022e0/330/310/340/320(ctx) (fps/framerate candidates) */
typedef struct DivxContentInfo {
    unsigned v0, v1;          /* observed from ctx+0x8/+0xC (w?, h?) */
    unsigned slot20, slot24, slot28;
    unsigned g5, g6, g7, g8, g9;  /* observed: 5 getter calls */
    /* ...more (dump truncated at 10) [U] */
} DivxContentInfo;
int __cdecl divxGetContentInfo(SplitterHandle h, DivxContentInfo *info);

/* [I] */
int __cdecl divxGetLastError(void);                           /* [U] */
/* [O] error→message from static table: "Not an AVI file", "AVI file has no MOVI
 *     list (corrupted?)", "Not DIVX 5.0 encoded", "operation needs an index", ... */
const char *__cdecl divxGetErrorMessage(int err);

#endif /* ROTK_FILE_PARSER_H */
