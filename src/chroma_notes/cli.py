import click

from .pipeline import process_pdf


@click.command()
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_pdf", type=click.Path(dir_okay=False))
def main(input_pdf: str, output_pdf: str) -> None:
    """Color-code every note in a sheet music PDF using Boomwhacker colors.

    \b
    Colors:  C=red  D=orange  E=yellow  F=lime  G=green  A=purple  B=pink
    """
    process_pdf(input_pdf, output_pdf)
