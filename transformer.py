"""Testing instance of transformer
"""

import argparse
import transformer_class

#pylint: disable=unused-argument
def add_parameters(parser: argparse.ArgumentParser) -> None:
    """Adds parameters
    Arguments:
        parser: instance of argparse
    """

def check_continue(transformer: transformer_class.Transformer, check_md: dict, transformer_md: dict, full_md: dict) -> list:
    """Checks if conditions are right for continuing processing
    Arguments:
        transformer: instance of transformer class
    Return:
        Returns a dictionary containining the return code for continuing or not, and
        an error message if there's an error
    """
    print("check_continue(): received arguments: %s" % str(check_md))
    return (0)

def perform_process(transformer: transformer_class.Transformer, check_md: dict, transformer_md: dict, full_md: dict) -> dict:
    """Performs the processing of the data
    Arguments:
        transformer: instance of transformer class
    Return:
        Returns a dictionary with the results of processing
    """
    print("perform_process(): received arguments: %s" % str(check_md))
    return {'code': 0, 'message': "Everything is going swimmingly"}
