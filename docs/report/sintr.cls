%
%   LaTeX class file for AJSTD
%   Copyright 2018-2021 Joaquim Baeta <mail@joaquimbaeta.com>
%
%   This program is free software: you can redistribute it and/or modify
%   it under the terms of the GNU General Public License as published by
%   the Free Software Foundation, either version 3 of the License, or
%   (at your option) any later version.
%
%   This program is distributed in the hope that it will be useful,
%   but WITHOUT ANY WARRANTY; without even the implied warranty of
%   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%   GNU General Public License for more details.
%
%   You should have received a copy of the GNU General Public License
%   along with this program.  If not, see <https://www.gnu.org/licenses/>.
%
%------------------------------------------------------------

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{sintr}[2023/01/20, version 1.0.0]
%\AtEndOfClass{\RequirePackage{microtype}} % For better typography

%   Options for element switching
\RequirePackage{xifthen} % For if arguments
    \DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
    \ProcessOptions*

\LoadClass{extarticle} % Support more font sizes

%   Display line numbers; must comment out \linenumbers for flushend to work
\RequirePackage[switch]{lineno} 
    \linenumberfont{\normalfont\footnotesize\sffamily}

% Page structure
\RequirePackage[inner=18mm,%
                outer=18mm,%
                top=18mm,%
                bottom=18mm,%
                headheight=10mm,%
                headsep=1mm,%
                footskip=8mm,%
                a4paper]{geometry}
\setlength{\columnsep}{8mm} 
\RequirePackage{flushend} 

% Paragraph structure
\RequirePackage{setspace}
    \setstretch{1.121} % Body leading
    \edef\restoreparindent{\parindent=\the\parindent\relax}
    \RequirePackage{parskip}
    \setlength{\parskip}{1pt plus 0.5pt minus 0pt}
    \restoreparindent
    \setlength{\parindent}{16pt}
\RequirePackage{enumitem}
    \setlist[itemize]{noitemsep,leftmargin=16pt,label=\textcolor{darkblue}{\textbullet}}
    \setlist[enumerate]{noitemsep,labelindent=16pt,style=multiline,leftmargin=*,label=\textcolor{darkblue}{\sffamily\arabic*.}}

% Language and fonts
\RequirePackage[english]{babel}
\RequirePackage{amsmath,amsfonts,amssymb}
\RequirePackage{mathpazo}
\RequirePackage[T1]{fontenc}
\RequirePackage{url}
\RequirePackage{xurl}

% PATCHED for latextemplates.com: upstream loads hyperxmp for extra PDF/XMP
% metadata, but on this pipeline's current TeX Live, hyperxmp's XMP string
% flattening of \@title corrupts LaTeX's internal font-series-merge macros
% (\series@maybe@drop@one@m and friends) and dumps their raw expansion into
% the visible document, right after the title, on every real-length title —
% a clean compile with wrong output. hyperxmp is optional metadata enrichment,
% not needed for a normal PDF, so it is dropped rather than patched.

\RequirePackage[pdfusetitle,%
                colorlinks=true,%
                allcolors=darkblue]{hyperref}

% pdfcopyright is a hyperxmp key; hyperxmp is no longer loaded
% (see the patch note above), so this \hypersetup call is dropped
% rather than left to error.

\RequirePackage{lettrine}

%\RequirePackage{fontspec}
%\setmainfont[
%        Path = base/fonts/,
%        Extension = .ttf,
%        UprightFont = *-Regular,
%        ItalicFont = *-Italic,
%        BoldFont = *-Bold,
%        BoldItalicFont = *-BoldItalic,
%    ]{Lora}

%\setsansfont[
%        Path = base/fonts/,
%        Extension = .otf,
%        UprightFont = *-Regular,
%        ItalicFont = *-Italic,
%        BoldFont = *-Bold,
%        BoldItalicFont = *-BoldItalic,
%    ]{FiraSans}

%\newfontfamily\FiraSansLight[
%        Path = base/fonts/,
%        Extension = .otf,
%        UprightFont = *-Regular,
%    ]{FiraSansLight}

%\newfontfamily\CormorantSC[
%        Path = base/fonts/,
%        Extension = .otf,
%        UprightFont = *-Regular,
%    ]{CormorantSC}


% ============================================================
% FONT SIZES
% ============================================================

\RequirePackage[fontsize=11pt]{scrextend} % Default body font size: 11pt

% Font styles

%\newcommand{\journalname}
%    {\normalfont\CormorantSC\fontsize{14}{17}\selectfont}

\newcommand{\journalname}
    {\normalfont\sffamily\fontsize{14}{17}\selectfont} % Journal name


%\renewcommand{\titlefont}
%    {\normalfont\FiraSansLight\fontsize{15}{18}\selectfont}

\renewcommand{\titlefont}
    {\normalfont\sffamily\fontsize{15}{18}\selectfont} % Article title


%\newcommand{\toprightinfo}
%    {\normalfont\FiraSansLight\fontsize{9}{11}\selectfont}

\newcommand{\toprightinfo}
    {\normalfont\sffamily\fontsize{9}{11}\selectfont} % Top-right info


\newcommand{\basesansfont}
    {\normalfont\sffamily\fontsize{10}{12}\selectfont} % Abstract, keywords, etc.


%\newcommand{\baselightsansfont}
%    {\normalfont\FiraSansLight\fontsize{9}{11}\selectfont}

\newcommand{\baselightsansfont}
    {\normalfont\sffamily\fontsize{9}{11}\selectfont} % Footer content


\renewcommand\UrlFont{\rmfamily} % Make \url adhere to default body font


% Authors and affiliations
\RequirePackage{authblk}

\setlength{\affilsep}{10pt}

\renewcommand\Authfont
    {\normalfont\sffamily\fontsize{12}{14}\selectfont} % Authors

\renewcommand\Affilfont
    {\normalfont\sffamily\fontsize{10}{12}\selectfont} % Affiliations

\renewcommand\AB@affilsepx{\\ \protect\Affilfont}
\renewcommand\AB@authnote[1]{\textsuperscript{\mdseries\upshape#1}}
\renewcommand\AB@affilnote[1]{\textsuperscript{\upshape#1}}
\renewcommand\Authands{, and }


\RequirePackage{textcomp}
\RequirePackage{gensymb}
\RequirePackage{datetime}

\newdateformat{monthyeardate}{%
    \monthname[\THEMONTH] \THEYEAR}


% ============================================================
% GRAPHICS, TABLES, AND FIGURES
% ============================================================

\RequirePackage{graphicx,xcolor}

% Colours
\definecolor{black}{RGB}{0,0,0}
\definecolor{royalviolet}{HTML}{610C3A}
\definecolor{darkblue}{rgb}{0.0, 0.0, 0.6}

%\definecolor{green(html/cssgreen)}{rgb}{0.0, 0.5, 0.0}
%\definecolor{darkblue}{rgb}{0.15, 0.23, 0.89}


\RequirePackage{colortbl}

\RequirePackage[font={sf,footnotesize},%
                labelfont={color=darkblue},%
                labelsep=period,%
                figurename=FIGURE,%
                tablename=TABLE,%
                singlelinecheck=off,]{caption}

\RequirePackage{subcaption}
\RequirePackage{tabularx}

% Table style
\newenvironment{tableminipage}[1]
    {\begin{minipage}{#1}\renewcommand\footnoterule{ \kern -1ex}}
    {\end{minipage}}

\arrayrulecolor{black}

\renewcommand{\arraystretch}{1.5}

\captionsetup[table]{position=below}

\RequirePackage{booktabs}
\RequirePackage{siunitx}
\sisetup{detect-all}

\RequirePackage{tikz}
\usetikzlibrary{calc}

\RequirePackage{changepage}
\RequirePackage{afterpage}
\RequirePackage{rotating}
\RequirePackage{stfloats}

\RequirePackage[absolute,overlay]{textpos}
\setlength{\TPHorizModule}{1mm}
\setlength{\TPVertModule}{1mm}
\textblockorigin{0mm}{0mm}


% ============================================================
% EQUATIONS
% ============================================================

\AtBeginDocument{%
    \abovedisplayskip=4pt plus 2pt minus 2pt%
    \abovedisplayshortskip=4pt plus 2pt minus 2pt%
    \belowdisplayskip=12pt plus 2pt minus 2pt%
    \belowdisplayshortskip=12pt plus 2pt minus 2pt%
}


% ============================================================
% ARTICLE INFORMATION
% ============================================================

\newcommand{\articleinformation}[1]
    {\def\articleinformation{#1}}

\newcommand{\articleinformationtruncated}[1]
    {\def\articleinformationtruncated{#1}}

\newcommand{\articletype}[1]
    {\def\articletype{#1}}

\newcommand{\articleshorttile}[1]
    {\def\articleshorttile{#1}}

\newcommand{\authorheader}[1]
    {\def\authorheader{#1}}

%\newcommand{\articledoi}[1]
%    {\def\articledoi{#1}}

\newcommand{\submitted}[1]
    {\def\submitted{#1}}

\newcommand{\submittedname}
    {\color{darkblue}Submitted: }

%\newcommand{\revised}[1]
%    {\def\revised{#1}}

%\newcommand{\revisedname}
%    {\color{darkblue}REVISED}

%\newcommand{\accepted}[1]
%    {\def\accepted{#1}}

%\newcommand{\acceptedname}
%    {\color{darkblue}ACCEPTED}


% ============================================================
% HEADERS AND FOOTERS
% ============================================================

\RequirePackage{fancyhdr}

\pagestyle{fancy}

% Main header style
\fancyhead[L]{\emph{\articleshorttile}}
\fancyhead[R]{\baselightsansfont\thepage\ }

\renewcommand{\headrulewidth}{1pt}

% Main footer style
\lfoot{}
\cfoot{}
\rfoot{}

\fancyfoot[RO,LE]
    {\baselightsansfont\thepage\ }

\fancyfoot[RE]
    {\baselightsansfont{}}

% \fancyfoot[LO]
%     {\emph{Report by \authorheader}}

\renewcommand{\footrulewidth}{1pt}


% Header and footer of first page
\fancypagestyle{firststyle}{%
    \renewcommand{\headrulewidth}{0pt}
    \fancyhead[L]{}
    \fancyhead[R]{}
    \fancyfoot[L]
        {\vspace{-2.5mm}\baselightsansfont{\emph{\articletype}}}
    \fancyfoot[C]
        {\vspace{-2.5mm}\baselightsansfont{\emph{\articleshorttile}}}
    \fancyfoot[R]
        {\vspace{-2.5mm}\baselightsansfont{\emph{\authorheader}}}
}


% ============================================================
% SECTIONING
% ============================================================

\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{3}

\RequirePackage[explicit]{titlesec}

% Section
\titleformat{\section}
    {\color{darkblue}\normalfont\sffamily\fontsize{12}{14}\selectfont}
    {\thesection.}
    {0.5em}
    {#1}
    []

% Unnumbered section
\titleformat{name=\section,numberless}
    {\color{darkblue}\normalfont\sffamily\fontsize{12}{14}\selectfont}
    {}
    {0em}
    {#1}
    []

% Subsection
\titleformat{\subsection}
    {\color{darkblue}\normalfont\sffamily\fontsize{11}{13}\selectfont}
    {\thesubsection}
    {0.5em}
    {#1}
    []

% Subsubsection
\titleformat{\subsubsection}
    {\color{darkblue}\normalfont\sffamily\fontsize{10.5}{12.5}\selectfont}
    {\thesubsubsection}
    {0.5em}
    {#1}
    []

% Paragraph
\titleformat{\paragraph}[runin]
    {\sffamily\small\bfseries}
    {}
    {0em}
    {#1}

% Section spacing
\titlespacing*{\section}
    {0pc}
    {3ex \@plus4pt \@minus3pt}
    {6pt}

\titlespacing*{\subsection}
    {0pc}
    {2.5ex \@plus3pt \@minus2pt}
    {4pt}

\titlespacing*{\subsubsection}
    {0pc}
    {2.5ex \@plus5pt \@minus2pt}
    {4pt}

\titlespacing*{\paragraph}
    {0pc}
    {1.5ex \@plus2pt \@minus1pt}
    {12pt}


% ============================================================
% REFERENCES
% ============================================================

%\RequirePackage[round]{natbib}
%\bibpunct{(}{)}{;}{author-year}{}{,}
%\bibliographystyle{sty/cse}
%\addto{\captionsenglish}{\renewcommand{\refname}{References:}}
%\setlength{\bibsep}{0pt plus 0.5pt minus 0pt}
%\setlength{\bibhang}{16pt}
%\setcitestyle{aysep={}}

\RequirePackage[fixlanguage]{babelbib}
\bibliographystyle{babunsrt}


% ============================================================
% KEYWORDS AND ABSTRACT
% ============================================================

% \newcommand{\keywords}[1]
%     {\def\keywords{#1}}

% \renewcommand{\abstract}[1]
%     {\def\abstract{#1}}

% \newcommand{\abscontent}{%

%     \begin{minipage}[t]{0.24\textwidth}

%         \vskip4pt

%         {\basesansfont\color{darkblue}Keywords: }\\
%         \basesansfont\keywords%

%         %\vskip2mm

%         %\basesansfont{%
%         %   {\submittedname}\hspace{0.5mm}\submitted
%         %   \hspace{1.5mm} \\
%         %   {\revisedname}\hspace{0.5mm}\revised
%         %   \hspace{1.5mm} \\
%         %   {\acceptedname}\hspace{0.5mm}\accepted%
%         %}

%     \end{minipage}
%     %
%     \begin{minipage}[t]{0.758\textwidth}

%         {\color{darkblue}\hrule height1pt width 1\linewidth depth0pt}

%         \vskip7.9pt

%         {\basesansfont\color{darkblue}Abstract}
%         \hspace{1mm}
%         \basesansfont\abstract\par

%         \vskip8pt

%         {\color{darkblue}\hrule height1pt width 1\linewidth depth0pt}

%         \vskip3pt

%         % Copyright / submission information
%         \sffamily\fontsize{8}{10}\selectfont
%         \copyright
%         \hspace{1pt}
%         The Author(s) \the\year.
%         {\submittedname}
%         \hspace{0.5mm}
%         \submitted ~as the \articletype.

%     \end{minipage}
% }


% ============================================================
% FIRST PAGE / TITLE
% ============================================================

\renewcommand{\@maketitle}{%
    \bgroup
    \setlength{\parindent}{0pt}

    %\begin{minipage}{0.2\textwidth}
    %    \vspace{0pt}
    %    \includegraphics[width=25mm]{base/ajstd-logo-2.pdf}
    %\end{minipage}%
    %
    %\begin{minipage}{0.8\textwidth}
    %    \vspace{-2pt}
    %    \flushright
    %    \journalname{
    %        \@title\par
    %        ASEAN Journal on Science
    %        {\color{darkblue}\&}
    %        Technology for Development
    %    } \\
    %
    %    \toprightinfo{%
    %        \articleinformation \\
    %        {\color{darkblue}DOI} \articledoi \\
    %        {\color{darkblue}\articletype} \\
    %    }%
    %
    %\end{minipage}

    \begin{flushleft}
        {%
            \vskip25pt%

            {\titlefont \@title\par}

            \vskip16pt%

            {\@author\par}

            \vskip10pt%
        }%
    \end{flushleft}

    \egroup

    {%
        \vskip10pt%

        \abscontent

        % \vskip27pt
    }%
}