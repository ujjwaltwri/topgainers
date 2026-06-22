"""
Formatting Model, used for formatting Finance Toolkit results into Markdown strings for LLMs.
"""

import pandas as pd

from financetoolkit.utilities.logger_model import get_logger

logger = get_logger()


def format_result(
    dataset: dict | pd.Series | pd.DataFrame | int | float | str | None,
) -> str:
    """
    Format a Finance Toolkit result into a compact Markdown string for LLM consumption.

    Args:
        dataset (dict | pd.Series | pd.DataFrame | int | float | str | None):
            The value to format. Supported behaviors per type:
            - None: returns "No data available."
            - pd.Series: converted to a one-column DataFrame and handled like a DataFrame.
            - pd.DataFrame: rendered as a Markdown table. Empty or all-NaN frames
              return "No data available.". Very wide tables (more than 20 columns)
              with 10 or fewer rows are auto-transposed before rendering.
            - dict: each key/value pair is formatted; DataFrame values are formatted
              recursively.
            - int | float | str: returned as a plain string.

    Returns:
        str: A compact Markdown string representation of the input dataset.
    """
    if dataset is None:
        return "No data available."

    if isinstance(dataset, pd.Series):
        # All pd.Series are treated in similar fashion as a pd.DataFrame
        dataset = dataset.to_frame()

    if isinstance(dataset, pd.DataFrame):
        # Determine whether the dataset is empty or contains only NaN values
        if dataset.empty or not int(dataset.notna().to_numpy().sum()):
            return "No data available."

        # Auto-transpose if very wide
        if len(dataset.columns) > 20 and len(dataset) <= 10:  # noqa
            dataset = dataset.T

        return f"{dataset.to_markdown()}\n\n"

    elif isinstance(dataset, dict):
        lines = []
        for key, value in dataset.items():
            if isinstance(value, pd.DataFrame):
                formatted = format_result(value)
                if formatted != "No data available.":
                    lines.append(f"**{key}**\n\n{formatted}")
                else:
                    lines.append(f"**{key}:** No data available.")
            else:
                lines.append(f"**{key}:** {value}")
        return "\n\n".join(lines)
    elif isinstance(dataset, (int, float, str)):
        return str(dataset)
    else:
        logger.warning(
            f"Unexpected result type: {type(dataset)}. Returning raw string."
        )
        return str(dataset)
