; inherits: markdown

; On the agenda (it starts with `# td VIEW ONLY`), a task folds its subtask rows under its own
; row, and starts folded (za toggles one, zR opens all, zM closes all). Nested bullets in todo.md
; and the task files stay open. Needs an hx that folds (helix main-kuba); another one ignores
; this file.
((document
   (section
     (list
       (list_item (list)) @fold))) @agenda
  (#match? @agenda "^# td VIEW ONLY")
  (#set! fold.closed))
