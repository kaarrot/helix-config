; inherits: markdown

; td tasks are `- [S] text` bullets only (bin/td TASK), so `*`, `+` and `1.` lists stay plain.
; The text is styled on `paragraph`, not `(inline)`: td.inline captures its root node
; to find a leading [Y]/[A]/[W]/[!], and an uncoloured capture over the exact same range
; would clear this colour. `paragraph` also takes the line end, so the ranges differ.
; Only the paragraph right after the marker (`.`) is the task: a note after a blank
; line, indented, is a paragraph of its own and keeps the plain text colour. A line
; straight under the task is the same paragraph, so it can't be told apart.

; Open tasks (- [ ] my text): stand out from regular buffer text, in bold. Its
; dates stay plain: themes/github_light.toml takes the bold off ui.text.inactive.
(list_item
  (list_marker_minus)
  (task_list_marker_unchecked) @constant)
(list_item
  (list_marker_minus)
  (task_list_marker_unchecked)
  .
  (paragraph) @variable.other.member)
(list_item
  (list_marker_minus)
  (task_list_marker_unchecked)
  .
  (paragraph (inline) @markup.bold))

; Open tasks with td states (- [Y] / - [A] / - [W] my text). Their bold comes
; from td.inline, which captures this same inline node to find the marker.
((list_item
  (list_marker_minus)
  .
  (paragraph) @variable.other.member)
 (#match? @variable.other.member "^\\[[yYaAwW]\\]\\s"))

; Done / ignored tasks (- [x] / - [!] my text): dim the whole line
(list_item
  (list_marker_minus)
  (task_list_marker_checked) @ui.text.inactive)
(list_item
  (list_marker_minus)
  (task_list_marker_checked)
  .
  (paragraph) @ui.text.inactive)

((list_item
  (list_marker_minus)
  .
  (paragraph) @ui.text.inactive)
 (#match? @ui.text.inactive "^\\[!\\]\\s"))
