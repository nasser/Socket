(ns todo
  (:use 
    arcadia.core 
    arcadia.linear
    hard.core))

'[repl
  ([x] history + navigation
    ([x] don't record duplicate history)
    ([x] prevent editing above history prompt?))]

'[interface
  ([x] better socket view insertion - only create second group if none exists)
  ([ ] socket commands in context menu)
  ([ ] research best default key commands (maybe use sublimeREPL's layout))]

'[advanced
  ([ ] extend to system processes (pipes))
  ([ ] allow customizable command wrapping + namespace sniffing
    ([ ] template with tokens for entered text and regex to apply to current view?))]

'[bugs
  ]

'(map inc (range 3))
