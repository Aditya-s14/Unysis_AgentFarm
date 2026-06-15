/**
 * UI punctuation & icons as Unicode escapes — avoids mojibake when files are
 * saved or served with the wrong encoding (common on Windows / PowerShell edits).
 */
export const MIDDOT = '\u00B7'; // ·
export const ARROW = '\u2192'; // →
export const ARROW_UP = '\u2191'; // ↑
export const EM_DASH = '\u2014'; // —
export const ELLIPSIS = '\u2026'; // …
export const SECTION = '\u25B8'; // ▸
export const WARN = '\u26A0'; // ⚠
export const CHECK = '\u2713'; // ✓
export const CROSS = '\u2717'; // ✗
/** Seedling — optional; use FARM_LABEL when emoji fonts are unreliable. */
export const FARM_ICON = '\uD83C\uDF31';

/** Plain-text farm prefix (always renders). */
export const FARM_LABEL = '[Farm]';
