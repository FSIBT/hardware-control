---
title: 'Hardware-Control: Instrument control and automation package'
tags:
  - Python
  - Instrument Control
  - Automation
  - Data Collection
authors:
  - name: Arun Persaud
    orcid: 0000-0003-3186-8358
    affiliation: 1
  - name: Grant Giesbrecht
    orcid: 0000-0003-2885-4801
    affiliation: 1
  - name: Timo Bauer
    orcid: 0000-0000-0000-0000
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
affiliations:
 - name: Lawrence Berkeley National Laboratory
   index: 1
 - name: Technische Universität Darmstadt
   index: 2
date: 7 August 2020
bibliography: paper.bib

---

# Summary

Conducting experimental research often presents a need to communicate with
laboratory instruments to facilitate running the experiment and collecting data.
Implementing a computer control system for an experiment can lead to quicker
results and a reduced chance of human error by minimizing the need for the
researcher to perform repeated tasks. Any software package for experiment
automation will require driver program to facilitate communication with the lab
instruments and some form of user interface to receive commands and present
data.

# Statement of need

`Hardware-Control` is a Python package for instrument control and
automation. It provides reusable user interfaces and instrument
drivers to simplify writing control programs. `Hardware-Control` uses
Qt to create fast and efficient user interfaces compatible with most
major operating systems. `Hardware-Control` is also designed so that
new drivers can be easily added for new instrument models and used
with existing user interfaces. The package also provides means for
simplifying data collection with automatic data logging, plotting, and
many export formats. `Hardware-Control` was designed to be a flexible
solution for many experimental challenges.

# Mathematics

Single dollars ($) are required for inline mathematics e.g. $f(x) = e^{\pi/x}$

Double dollars make self-standing equations:

$$\Theta(x) = \left\{\begin{array}{l}
0\textrm{ if } x < 0\cr
1\textrm{ else}
\end{array}\right.$$

You can also use plain \LaTeX for equations
\begin{equation}\label{eq:fourier}
\hat f(\omega) = \int_{-\infty}^{\infty} f(x) e^{i\omega x} dx
\end{equation}
and refer to \autoref{eq:fourier} from text.

# Citations

Citations to entries in paper.bib should be in
[rMarkdown](http://rmarkdown.rstudio.com/authoring_bibliographies_and_citations.html)
format.

If you want to cite a software repository URL (e.g. something on GitHub without a preferred
citation) then you can do it with the example BibTeX entry below for @fidgit.

For a quick reference, the following citation commands can be used:
- `@author:2001`  ->  "Author et al. (2001)"
- `[@author:2001]` -> "(Author et al., 2001)"
- `[@author1:2001; @author2:2001]` -> "(Author1 et al., 2001; Author2 et al., 2002)"

# Figures

Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Fenced code blocks are rendered with syntax highlighting:
```python
for n in range(10):
    yield f(n)
```

# Acknowledgements

The information, data, or work presented herein was funded by the Advanced Research
Projects Agency-Energy (ARPA-E), U.S. Department of Energy, under Contract No. DE-AC02-
05CH11231.

# References
