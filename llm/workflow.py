def run():  # placeholder (content unchanged; raw string to prevent escape processing)
    return r"""
\documentclass[tikz,border=10pt]{standalone}
\usetikzlibrary{positioning}

\begin{document}
\begin{tikzpicture}[
    layer/.style={rectangle, draw, minimum width=2.5cm, minimum height=0.8cm, rounded corners=2pt, font=\sffamily},
    arrow/.style={->, thick}
]

% --- Generator ---
\node[layer, fill=blue!20] (z) {Input Noise $z$};
\node[layer, fill=blue!20, below=of z] (g1) {Dense + ReLU};
\node[layer, fill=blue!20, below=of g1] (g2) {Reshape};
\node[layer, fill=blue!20, below=of g2] (g3) {ConvTranspose + BN + ReLU};
\node[layer, fill=blue!20, below=of g3] (g4) {ConvTranspose + Tanh};
\node[layer, fill=blue!40, below=of g4] (fake) {Generated Image};

% Generator arrows
\draw[arrow] (z) -- (g1);
\draw[arrow] (g1) -- (g2);
\draw[arrow] (g2) -- (g3);
\draw[arrow] (g3) -- (g4);
\draw[arrow] (g4) -- (fake);

% --- Discriminator ---
\node[layer, fill=red!20, right=5cm of fake] (x) {Input Image (real/fake)};
\node[layer, fill=red!20, above=of x] (d1) {Conv + LeakyReLU};
\node[layer, fill=red!20, above=of d1] (d2) {Conv + LeakyReLU};
\node[layer, fill=red!20, above=of d2] (d3) {Dense + Sigmoid};
\node[layer, fill=red!40, above=of d3] (out) {Output: Real / Fake};

% Discriminator arrows
\draw[arrow] (x) -- (d1);
\draw[arrow] (d1) -- (d2);
\draw[arrow] (d2) -- (d3);
\draw[arrow] (d3) -- (out);

% Connect Generator to Discriminator
\draw[arrow, dashed] (fake.east) -- ++(1.5,0) |- (x.south);

% Labels
\node[above=0.2cm of z] {\textbf{Generator}};
\node[above=0.2cm of out] {\textbf{Discriminator}};

\end{tikzpicture}
\end{document}

"""