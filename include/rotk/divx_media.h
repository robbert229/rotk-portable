/* rotk/divx_media.h — reconstructed API of DivxMediaLib.dll (ROTK 2003 PC FMV stack)
 *
 * Source: REA/Ghidra decompilation of DivxMediaLib.dll
 *   sha256 ed2c45bcb3beab5fd64e51acd7cefc06f3cdb888f21f03d19ae16836dee35ecd
 *   REA Evidence ev_bbbfa1074e47a3d3aaf220a9596378427aa9072a72f36d3b976cbe65bf7c5838
 * Calling convention: __cdecl for all exports (observed in pseudocode).
 * Sessions are slots in a global table, stride 0x350 bytes (observed); handle
 * validity checked via slot-in-use flag at +0x5C; invalid handle returns 5 (observed).
 * Status of each prototype: [O]bserved decompile, [I]nferred from name/usage, [U]nknown params.
 */
#ifndef ROTK_DIVX_MEDIA_H
#define ROTK_DIVX_MEDIA_H

typedef int DivxHandle;            /* slot index; 5 = DIVX_E_BADHANDLE (observed return) */
#define DIVX_E_BADHANDLE 5         /* observed: returned when slot not open */

/* [O] int __cdecl OpenDivxFile(char *path)  — allocates slot, calls divxSplitterFileParse */
DivxHandle __cdecl OpenDivxFile(const char *path);
/* [O] void __cdecl CloseDivxFile(int handle) — stops play, frees splitter + decoder ctx */
void __cdecl CloseDivxFile(DivxHandle h);

/* [I] transport control (threaded play: CreateThread/SetEvent observed in imports) */
int __cdecl DivxPlay(DivxHandle h);        /* [U] */
int __cdecl DivxPause(DivxHandle h);       /* [U] */
int __cdecl DivxResume(DivxHandle h);      /* [U] */
int __cdecl DivxStop(DivxHandle h);        /* [U] */

/* [O] undefined4 __cdecl DivxNextFrame(int handle) — pulls next video frame under CS */
int __cdecl DivxNextFrame(DivxHandle h);
/* [I] render/present current frame (string "Function: DivxDoFrame" observed) */
int __cdecl DivxDoFrame(DivxHandle h);     /* [U] */
/* [I] next audio block for game's DirectSound path */
int __cdecl DivxNextAudioChunk(DivxHandle h, void *dst, int *size); /* [U] */
/* [I] seek */
int __cdecl DivxGotoFrame(DivxHandle h, int frame);        /* [U] */
int __cdecl DivxGotoFrameEx(DivxHandle h, int a2, int a3); /* [U] */

/* [O] undefined4 __cdecl DivxGetContentInfo(int handle, int info) — forwards to
 *     splitter divxGetContentInfo(handle, out) under critical section */
int __cdecl DivxGetContentInfo(DivxHandle h, DivxContentInfo *info /* see file_parser.h, ≥10 dwords */);

/* [O] DivxSetVideoBuffer(int handle, u32 val) stores ptr at slot+0x32C (dest RGB surface) */
int __cdecl DivxSetVideoBuffer(DivxHandle h, void *dst);
/* [I] symmetric audio destination */
int __cdecl DivxSetAudioBuffer(DivxHandle h, void *dst);   /* [U] */
/* [O] DivxSetOutputVideoFormat(int handle, u32 fmt) → decoder SetOutputFormat(handle, fmt, w, h) */
int __cdecl DivxSetOutputVideoFormat(DivxHandle h, int fmt);
/* [I] buffer depth config → splitter divxSetAudVidBuffers */
int __cdecl DivxSetNumAudVidBuffers(int nvid, int naud);   /* [U] */
/* [I] progress/completion callback */
int __cdecl DivxSetCallBackFn(DivxHandle h, void (__cdecl *cb)(int, void *), void *ctx); /* [U] */

/* [I] mode/profile knobs — semantics unknown */
int __cdecl DivxModeSet(int a1);           /* [U] */
int __cdecl DivxProfile(DivxHandle h);     /* [U] */

/* [I] errors */
int   __cdecl DivxGetLastError(void);                        /* [U] */
const char *__cdecl DivxFormatErrorMessage(int err);         /* "%s - %s" observed */

/* [I] version query */
int __cdecl DivxGetSDKVersion(void);       /* [U] */

#endif /* ROTK_DIVX_MEDIA_H */
