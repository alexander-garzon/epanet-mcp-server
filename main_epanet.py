"""
FastMCP Movie Database Server

A Model Context Protocol server for retrieving movie data from MongoDB.
Compatible with Claude Desktop and other MCP clients.

To run:
    uv run server movie_server stdio

Environment Variables:
    MONGODB_URI: MongoDB connection string (default: mongodb://localhost:27017)
    DATABASE_NAME: Database name (default: moviedb)
    COLLECTION_NAME: Collection name (default: movies)
"""

import os
from mcp.server.fastmcp import FastMCP
from epyt import epanet
import numpy as np

# Create MCP server
mcp = FastMCP("Movie Database Server")





##################################################EPANET#####################################################

check = False
results = None
@mcp.resource("files://Networks")
def get_inp_files() -> str:
    """Checks the 'Networks' folder and returns a list of all .inp files.""" # <-- CORRECTED DOCSTRING
    try:
        # Define the folder path consistently
        folder_path = "Networks" 

        # Check if the folder exists
        if not os.path.isdir(folder_path):
            return f"Error: The folder '{folder_path}' does not exist."

        # Get a list of all files in the folder
        all_files = os.listdir(folder_path)

        # Filter for files ending with .inp
        inp_files = [file for file in all_files if file.endswith(".inp")]

        if not inp_files:
            return f"No .inp files found in the '{folder_path}' folder." # <-- CORRECTED MESSAGE

        # Format the list for display
        result = f"List of .inp files in the '{folder_path}' folder:\n\n" # <-- CORRECTED MESSAGE
        for i, file in enumerate(inp_files, 1):
            result += f"{i}. {file}\n"

        return result

    except Exception as e:
        # A simple string conversion is often sufficient for exceptions
        return f"Error during file listing: {str(e)}"


@mcp.tool()
def run_epanet_simulation(file_name: str) -> str:
    """
    Runs an EPANET simulation on a specified .inp file and returns the results.
   
    Args:
        file_name (str): The name of the .inp file to simulate.
                         This file must be located in the 'models' directory.
   
    Returns:
        str: A message indicating the success or failure of the simulation,
             along with simulation time, number of nodes, and number of pipes.
    """
   

    # ==========================
   
    try:
        
       
        # Check if the file exists
        if not os.path.exists("Networks/"+file_name):
            return f"Error: The file '{file_name}' does not exist in the 'models' folder."
           
        # Create a WaterNetworkModel object
        network = epanet("Networks/"+file_name, display_msg=False, display_warnings=False)
        network.setDemandModel("DDA",0,0,0)
        check = True
       
        # Measure simulation time
        import time
        start_time = time.time()
        
        # Create a simulator and run the simulation
        results = network.getComputedHydraulicTimeSeries()
        
        # Calculate simulation time
        simulation_time = time.time() - start_time
        
        # Get network statistics

        num_nodes = network.getNodeJunctionCount()
        num_pipes = len(network.getLinkIndex())
       
        return (f"Simulation of '{file_name}' completed successfully.\n"
                f"Simulation time: {simulation_time:.3f} seconds\n"
                f"The model has {num_nodes} nodes and {num_pipes} pipes.")
                
    except Exception as e:
        return f"Error during simulation: {str(e)}"
    


@mcp.tool()
def get_pressures_less_than(file_name: str,thresshold: float) -> str:
    """ Return the nodes with negative pressures after the last simulation. """


    network = epanet("Networks/"+file_name, display_msg=False, display_warnings=False)
    network.setDemandModel("DDA",0,0,0)
    results = network.getComputedHydraulicTimeSeries()
    
    pressures = results.Pressure

    #find the node id with the negative pressures
    negative_pressures = {}
    #remove the reservoirs 
    junctions_ENidx= np.array(network.getNodeJunctionIndex())-1

    pressures = pressures[0,junctions_ENidx]

    nodes_under_thress = {}
    under_thress = np.where(pressures < thresshold)
    #get the pressure for these nodes 
    display_pressures = pressures[under_thress]
    print(display_pressures)

    
    nodes_under_thress = {network.getNodeNameID(i+1): display_pressures[i] for i in range(len(under_thress[0]))}

    
    return f"The nodes that are having pressure less that {thresshold} are : {nodes_under_thress}" 





@mcp.tool()
def get_pipes_over(file_name: str,thresshold: float) -> str:
    
    network = epanet("Networks/"+file_name, display_msg=False, display_warnings=False)
    network.setDemandModel("DDA",0,0,0)
    results = network.getComputedHydraulicTimeSeries().Velocity
    
    under_thress = np.where(results > thresshold)


    pipe_under_thress = { network.getLinkNameID(i+1): results[0][i] for i in list(under_thress[1])}
    

    return f"The pipes that are having velocity more than {thresshold} are : {pipe_under_thress}"
    
    





if __name__ == "__main__":
    import asyncio
    mcp.run()
    #print(get_pressures_less_than("Balerma.inp",22))



