; inherits: markdown

; Fold heading sections, keeping the conversation marker outside those folds.
((section
   [
     (atx_heading)
     (setext_heading)
   ] @heading) @fold
  (#not-match? @heading "^# helix-agent-session: "))
