from generate import CrosswordCreator
from crossword import Crossword, Variable

structure = "data/structure0.txt"
words = "data/words0.txt"

# Set up crossword

crossword = Crossword(structure, words)
creator = CrosswordCreator(crossword)

creator.enforce_node_consistency()
creator.ac3()


