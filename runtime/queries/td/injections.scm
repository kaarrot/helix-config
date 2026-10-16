; inherits: markdown

; Parse inline text as td.inline (markdown.inline plus the task markers). Of two
; injections on the same node the later pattern wins, so this replaces markdown's
; own `(inline)` injection.
((inline) @injection.content (#set! injection.language "td.inline") (#set! injection.include-unnamed-children))
