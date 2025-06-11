from generate import CrosswordCreator
from crossword import Crossword, Variable

structure = "data/structure2.txt"
words = "data/words1.txt"

# Set up crossword

crossword = Crossword(structure, words)
creator = CrosswordCreator(crossword)

creator.enforce_node_consistency()
creator.ac3()
a = creator.solve()
print(a)
