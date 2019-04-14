example of usage:

python -m cccalc.run ~/Desktop/BCH-fills.csv


# cost basis model

The cost basis of holdings exists as a list of cost basis segments.
Each cost basis segment contains:
* product name of what is held
* timestamp when holding was acquired
* quantity of product acquired (or still unsold at the time the cost basis of holdings is valid at)
* unit cost of product at time holding acquired

Depending on if LIFO or FIFO model, either the first (oldest) or the last (newest) cost basis segment is consumed during
calculation of the capital gains/loss of a SELL fill.  BUY fills always append new cost basis segments to the end.