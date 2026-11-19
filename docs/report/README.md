# Project Report

A two-column thesis/project report template built on `sintr.cls`, a
repurposed journal class (originally `ajstd.cls`, for the ASEAN Journal of
Science & Technology for Development), adapted for student BSMS/project
reports.

## Files

- `main.tex` — the report. Start here.
- `sintr.cls` — vendored class file.
- `references.bib` — bibliography, resolved via classic `bibtex`.
- `LICENCE` — GNU GPL v3.

## Building

    pdflatex main
    bibtex   main
    pdflatex main
    pdflatex main

`sintr.cls` already sets `\bibliographystyle{babunsrt}` (the `babelbib`
package's unsorted style) — plain `bibtex`, not `biber`.

## Licence

**GPL-3.0-or-later.** `sintr.cls`'s own header states:

> Copyright 2018-2021 Joaquim Baeta \<mail@joaquimbaeta.com\>
> This program is free software: you can redistribute it and/or modify it
> under the terms of the GNU General Public License as published by the
> Free Software Foundation, either version 3 of the License, or (at your
> option) any later version.

This is a **correction**, not a match, to how this template circulates
elsewhere: the Overleaf gallery listing it came from tags it CC-BY-4.0, but
that is the gallery's metadata, not the file's own licence — the class
header carries no CC grant of any kind, only the GPL text above. Trust the
file. See `LICENCE` for the full GPLv3 text.

Source (class file): `sintr.cls` as distributed via Overleaf and mirrored at
https://github.com/NanJ90/JiaShua/blob/main/sintr.cls (a student repo that
carries an unmodified copy from an Overleaf-git export; not the original
author's own repository).

This starter document is a minimal example written for latextemplates.com
and carries no additional restrictions beyond the GPL terms above.
