; inherits: markdown_inline
; markdown.inline's own queries, reached through the markdown_inline link, since
; tree-house's pattern for the line above stops at a dot and can't name markdown.inline

; td task state markers ([Y], [A], [W], [!]), only at the start of the text,
; so an `[A]` later in a line or in prose stays a plain link. Plain text is no
; node here, so `.` alone would also take the first link after some words. The
; whole text is captured to check that, and for [Y]/[A]/[W] that capture is also
; the task's bold (td/highlights.scm can't bold this node: this layer's capture
; on the same range would win).
((inline . (shortcut_link (link_text) @label)) @markup.bold (#match? @markup.bold "^\\[[Yy]\\]"))
((inline . (shortcut_link (link_text) @tag)) @markup.bold (#match? @markup.bold "^\\[[Aa]\\]"))
((inline . (shortcut_link (link_text) @type)) @markup.bold (#match? @markup.bold "^\\[[Ww]\\]"))
((inline . (shortcut_link (link_text) @ui.text.inactive)) @_task (#match? @_task "^\\[!\\]"))

; Dim dates in backticks or brackets (`2026-10-16 Fri 14:00` or [2026-10-16 Fri 14:00]).
; The code span and the whole bracket link are captured, so the backticks and
; brackets drop a task's bold along with the date.
((code_span) @ui.text.inactive
 (#match? @ui.text.inactive "^`[0-9]{4}-[0-9]{2}-[0-9]{2}"))
((shortcut_link) @ui.text.inactive
 (#match? @ui.text.inactive "^\\[[0-9]{4}-[0-9]{2}-[0-9]{2}"))
((shortcut_link (link_text) @ui.text.inactive)
 (#match? @ui.text.inactive "^[0-9]{4}-[0-9]{2}-[0-9]{2}"))
