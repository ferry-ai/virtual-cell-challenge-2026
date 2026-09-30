"""Build the private, confirmation-only notebook without executing its source."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / "kaggle_confirmation_runner.py").read_text(encoding="utf-8")
compile(source, "kaggle_confirmation_runner.py", "exec")
notebook = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "id": "scope",
         "source": ["# VCC: conferma preregistrata del generatore\n",
                    "Dataset e notebook privati. Esegue soltanto i finalisti scelti nello sviluppo Colab; "
                    "controlla snapshot, input, split e versione dello scorer. Non è un punteggio VCC.\n"]},
        {"cell_type": "code", "metadata": {}, "id": "confirmation",
         "execution_count": None, "outputs": [], "source": source.splitlines(keepends=True)},
    ],
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, default=HERE / "kaggle_remote/vcc-lead-generator-r1.ipynb")
destination = parser.parse_args().out
destination.parent.mkdir(parents=True, exist_ok=True)
with destination.open("x", encoding="utf-8") as stream:
    json.dump(notebook, stream, indent=1, ensure_ascii=False)
    stream.write("\n")
print(destination)
