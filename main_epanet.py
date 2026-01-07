import os
from mcp.server.fastmcp import FastMCP
from epyt import epanet
import numpy as np
import time
import base64
import io
import matplotlib.pyplot as plt
from mcp.types import ImageContent, EmbeddedResource
# Create MCP server
mcp = FastMCP("EPANET Simulation Server")





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
   
    Returns:
        str: A message indicating the success or failure of the simulation,
             along with simulation time, number of nodes, and number of pipes.
    """
   
    try:


        # Check if the file exists
        if not os.path.exists(file_name):
            return f"Error: The file '{file_name}' does not exist in the 'models' folder."
           
        # Create a WaterNetworkModel object
        network = epanet(file_name, display_msg=False, display_warnings=False)
        network.setDemandModel("DDA",0,0,0)

       
        # Measure simulation time
        
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
                #TODO INCLUDE MORE INFORMATION ABOUT THE SIMULATION HERE.
    except Exception as e:
        return f"Error during simulation: {str(e)}"

@mcp.tool()   
def modify_inp_file(file_name: str,actions) -> str:
    """ Modify the inp file to close specific pipes. """
    #TODO
    return "Not implemented yet."

@mcp.tool()
def plot_pressures(file_name: str) -> ImageContent | str:
    """ 
    Plot the pressures in the nodes after the last simulation. 
    Returns the plot as an embedded image.
    """
    
    if not os.path.exists(file_name):
        return f"Error: The file '{file_name}' does not exist in the Networks folder."

    # --- Simulation Logic (Kept as is) ---
    network = epanet(file_name, display_msg=False, display_warnings=False)
    network.setDemandModel("DDA", 0, 0, 0)

    # Separate junctions with reservoirs.
    nodes_idx = np.array(network.getNodeJunctionIndex()) - 1
    
    # Get the pressure results
    results = network.getComputedHydraulicTimeSeries().Pressure[0]
    pressures = results[nodes_idx]

    # Get node names for labeling
    node_names = [network.getNodeNameID(i + 1) for i in nodes_idx]

    # --- Plotting Logic (Modified for MCP) ---
    
    # Switch backend to prevent GUI windows from trying to open on the server
    plt.switch_backend('Agg') 
    
    plt.figure(figsize=(12, 6))
    plt.bar(node_names, pressures, color='skyblue')
    plt.xlabel('Node Names')
    plt.ylabel('Pressure (psi)')
    plt.title(f'Node Pressures: {os.path.basename(file_name)}')
    plt.xticks(rotation=90)
    plt.tight_layout()

    # --- Image Encoding ---
    
    # 1. Create an in-memory bytes buffer
    buf = io.BytesIO()
    
    # 2. Save the plot to the buffer (instead of a file)
    plt.savefig(buf, format='png')
    plt.close() # Close the plot to free memory
    
    # 3. Rewind the buffer to the beginning
    buf.seek(0)
    
    # 4. Encode as Base64 string
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # 5. Return the ImageContent object
    return ImageContent(
        type="image",
        data=image_base64,
        mimeType="image/png"
    )

@mcp.tool()
def plot_velocities(file_name: str) -> str:
    """ Plot the velocities in the pipes after the last simulation. """
    #TODO
    return "Not implemented yet."


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
    mcp.run()
    #plot_pressures("Networks/Original Networks/Balerma.inp")

    #####DEBUG######

    #print(get_pressures_less_than("Balerma.inp",22))



####MODIFY
#check which networks are saved in the folders
#close open pipes in selected networks and then save the in the modified folder\

#when running the simulation check 
# minimum pressures in the nodes
#Min max velocities in the pipes
#pottential erros
#Time needed for the simulation 

#see if it is possible to plot pictures in the mcp client

#Information about the pumps
