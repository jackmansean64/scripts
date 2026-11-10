# Class Seating Planner

A single-file, no-install seating plan tool for elementary teachers. Open `index.html` in any browser.

![screenshot](screenshot.png)

## Features

- **Student cards**: drag them between seats, onto a classmate to swap, or back to the *Unseated* list. Works with mouse and touch.
- **Groups**: individual desks, pairs, tables of 4, long tables (2 per side + 1 on the end), big tables and rows. Drag the top bar to move a group, double-click the name to rename it.
- **Edit layout** mode (top bar):
  - Drag desks to make tables any shape. Drop a desk on another table to move it there, or on open floor to make it a separate desk. The student sitting there moves with it.
  - **+** adds a desk to a table, **×** removes one, **⟳** rotates a table 90°.
  - Dotted lines show which desks count as "next to" each other (desks touching or less than 24px apart, side by side or one behind the other). Leave a gap if students across a table shouldn't count.
  - Drag the board to any wall, and drag the blue corner handle to resize the room.
- **Rules per student** (click a card):
  - Not in the same group as *student*
  - Not sitting next to *student*
  - In the same group as *student*
  - Not sitting next to a *boy / girl*
  - Sits alone (own desk)
  - Always sits at *group*
- **Red cards**: any card whose rule is broken turns red (hover it to see why). While dragging, every seat glows green or red to preview the result of dropping there.
- **Shuffle**: re-seats everyone randomly while satisfying every rule (randomised backtracking search). Students marked *Keep in this seat* are not moved. If no valid arrangement exists, it finds the one with the fewest broken rules and highlights them.
- Undo (Ctrl/⌘+Z), automatic saving in the browser, download/load the plan as JSON, and print (via the ⋯ menu).

Plans saved by earlier versions (rectangular tables) are converted automatically when loaded.
