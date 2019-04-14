import csv
import cccalc.types


def parse(filehandle):
    """
    Parse the CSV fills file which can be read from the open filehandle passed in.

    :param filehandle:
    :return: iterable of Fill objects
    """
    for row in csv.DictReader(filehandle):
        yield cccalc.types.Fill(row)


def parse_cost_basis(filehandle, size_unit, cost_unit, basis_method):
    cbq = cccalc.types.CostBasisQueue(size_unit, cost_unit, basis_method)
    cbq.load(filehandle)

    return cbq