from pydantic import BaseModel, Field
from typing import Optional, Literal


class Intervention(BaseModel):
    """Represents a single engineering change to the water network."""

    action: Literal["status", "add_pipe", "set_diameter", "delete_pipe"] = Field(
        ...,
        description="The type of modification: change status, add a new link, change diameter, or remove a link.",
    )
    id: str = Field(..., description="The Unique ID of the pipe or link you want to modify.")
    value: Optional[str] = Field(
        None, description="For 'status' action: Use 'open' or 'close'."
    )
    diameter: Optional[float] = Field(
        None, description="For 'set_diameter' or 'add_pipe': The pipe diameter in inches."
    )
    from_node: Optional[str] = Field(
        None, description="For 'add_pipe': The ID of the node where the pipe starts."
    )
    to_node: Optional[str] = Field(
        None, description="For 'add_pipe': The ID of the node where the pipe ends."
    )


class SimulationFilter(BaseModel):
    """Used for filtering results after a simulation."""

    file_name: str = Field(..., description="The name of the .inp file.")
