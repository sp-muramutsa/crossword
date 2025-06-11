import sys

from crossword import *
from collections import defaultdict


class CrosswordCreator:

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy() for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont

        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size, self.crossword.height * cell_size),
            "black",
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border, i * cell_size + cell_border),
                    (
                        (j + 1) * cell_size - cell_border,
                        (i + 1) * cell_size - cell_border,
                    ),
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (
                                rect[0][0] + ((interior_size - w) / 2),
                                rect[0][1] + ((interior_size - h) / 2) - 10,
                            ),
                            letters[i][j],
                            fill="black",
                            font=font,
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for variable, values in self.domains.items():
            for value in values.copy():
                if variable.length != len(value):
                    self.domains[variable].remove(value)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps[x, y]

        if overlap is None:
            return False
        index_x, index_y = overlap

        for value_x in self.domains[x].copy():
            if not any(
                value_x[index_x] == value_y[index_y] for value_y in self.domains[y]
            ):
                self.domains[x].remove(value_x)
                revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            arcs = []
            for variable in self.crossword.variables:
                neighbors = self.crossword.neighbors(variable)
                for neighbor in neighbors:
                    arcs.append((variable, neighbor))

        while arcs:
            x, y = arcs.pop(0)

            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False

                neighbors = self.crossword.neighbors(x) - {y}
                for z in neighbors:
                    arcs.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """

        for variable in self.domains:
            if variable not in assignment:
                return False

        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check for duplicates
        counter = set()
        for variable, value in assignment.items():

            if variable.length != len(value):
                return False

            # there are no conflicts between neighboring variables.
            neighbors = self.crossword.neighbors(variable)
            for neighbor in neighbors:

                if neighbor not in assignment:
                    continue

                overlap = self.crossword.overlaps[variable, neighbor]
                index_x, index_y = overlap

                neighbor_value = assignment[neighbor]
                if value[index_x] != neighbor_value[index_y]:
                    return False

            if value in counter:
                return False
            counter.add(value)

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        values = self.domains[var]

        counter = {value: 0 for value in values}
        neighbors = self.crossword.neighbors(var)

        for value in values:

            for neighbor in neighbors:

                # Skip assigned neighbors
                if neighbor in assignment:
                    continue

                overlap = self.crossword.overlaps[var, neighbor]
                if overlap is None:
                    continue
                i, j = overlap

                for neighbor_value in self.domains[neighbor]:
                    if value[i] != neighbor_value[j]:
                        counter[value] += 1

        counter = dict(sorted(counter.items(), key=lambda x: x[1]))
        return list(counter.keys())

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        unassigned_variables = {}
        for variable in self.domains:
            if variable not in assignment:
                unassigned_variables[variable] = (
                    len(self.domains[variable]),
                    len(self.crossword.neighbors(variable)),
                )

        unassigned_variables = dict(
            sorted(unassigned_variables.items(), key=lambda x: (x[1][0], -x[1][1]))
        )

        return list(unassigned_variables.keys())[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        if self.assignment_complete(assignment):
            return assignment

        variable = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(variable, assignment):

            # Save a copy of current domain and current assignment
            domains_backup = self.domains.copy()
            assignment_backup = assignment.copy()

            if self.consistent(assignment):
                assignment[variable] = value
                self.domains[variable] = {value}

                # Prepare arcs to propagate inference
                arcs = [
                    (neighbor, variable)
                    for neighbor in self.crossword.neighbors(variable)
                ]

                inferences = self.ac3(arcs)

                if inferences:
                    # Add inferences to assignment
                    inferences = {
                        var: list(self.domains[var])[0]
                        for var in self.domains
                        if var not in assignment and len(self.domains[var]) == 1
                    }
                    assignment.update(inferences)

                    result = self.backtrack(assignment)
                    if result:
                        return result

            # Remove {var = value} and inferences from  assignment
            self.domains = domains_backup
            assignment = assignment_backup

        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    print(crossword.words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
