# Respiratory chain expression
2023-03-24 Christoph Schweingruber

## DESCRIPTION
- The mammalian mitochondrial respiratory complexes were retrieved from PDB: I (Bos taurus, 5lc5), II (Sus scrofa, 1zoy), III (Bos taurus, 1bgy), IV (Bos taurus, 1occ), and V (Bos taurus, 5ara).
In UCSF Chimera (version 1.16, build 42360) they were arranged and rendered in neutral colors and saved as 'respiratory_chain_neutral.py'. The neutral colors can be restored with the script 'color_respiratory_chain_neurally.py'.
- The expression across ALS motor neurons (average of log2 foldchange) was used to color the individual protein chains with the script 'color_respiratory_chain_by_expression.py', generated in R project 'Chimera_Respiratory_Chain_Expression.RProj'. The structures were rendered in Chimera and saved as 'respiratory_chain_expression.py'.

## FILES
* R/Chimera_Respiratory_Chain_Expression.Rproj
* R/docs/Chimera_Respiratory_Chain_Expression.Rmd
* R/docs/legend_avg_log2fc.pdf
* python/color_respiratory_chain_by_expression.py, color_respiratory_chain_by_expression.pyc
* python/color_respiratory_chain_neurally.py, color_respiratory_chain_neurally.pyc
* python/respiratory_chain_expression.py, respiratory_chain_expression.pyc
* python/respiratory_chain_neutral.py, respiratory_chain_neutral.pyc
* images/respiratory_chain_expression.png
* images/respiratory_chain_neutral.png
* meta/Annotation_Respiratory_Complexes.txt
