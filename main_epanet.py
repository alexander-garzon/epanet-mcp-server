import os
import io
import time
import base64
import numpy as np
import matplotlib.pyplot as plt
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent
from epyt import epanet
from models import Intervention  # Import your new models

# --- Configuration ---
NETWORKS_DIR = "Networks"
MODIFIED_DIR = "Modified"

# Ensure directories exist
os.makedirs(NETWORKS_DIR, exist_ok=True)
os.makedirs(MODIFIED_DIR, exist_ok=True)

mcp = FastMCP("EPANET Simulation Server")

# --- Universal Helper Logic ---

def _get_full_path(filename: str) -> str:
    """
    Smarter path resolver that handles missing .inp extensions.
    """
    clean_name = os.path.basename(filename)
    
    # If the user forgot the extension, add it
    if not clean_name.lower().endswith(".inp"):
        clean_name += ".inp"
    
    # 1. Check Modified folder
    mod_path = os.path.join(MODIFIED_DIR, clean_name)
    if os.path.exists(mod_path):
        return mod_path
        
    # 2. Check original Networks folder
    net_path = os.path.join(NETWORKS_DIR, clean_name)
    if os.path.exists(net_path):
        return net_path
        
    raise FileNotFoundError(f"'{clean_name}' not found in {MODIFIED_DIR} or {NETWORKS_DIR}.")
        

def _load_and_simulate(filename: str):
    """Centralized simulation engine used by all tools."""
    full_path = _get_full_path(filename)
    network = epanet(full_path, display_msg=False, display_warnings=False)
    network.setDemandModel("DDA", 0, 0, 0)
    results = network.getComputedHydraulicTimeSeries()
    return network, results

def _create_plot_image(x_data, y_data, title, xlabel, ylabel, colors) -> ImageContent:
    """Standardized image generator that accepts a list of colors for bars."""
    plt.switch_backend('Agg') 
    plt.figure(figsize=(12, 6))
    
    # Pass the list of colors here
    plt.bar(x_data, y_data, color=colors)
    
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=90)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return ImageContent(
        type="image",
        data=base64.b64encode(buf.read()).decode('utf-8'),
        mimeType="image/png"
    )

# --- Resources: Letting the AI 'See' the files ---

@mcp.resource("files://all_networks")
def list_all_available_networks() -> str:
    """Lists all files available in both Original and Modified folders."""
    try:
        net_files = [f for f in os.listdir(NETWORKS_DIR) if f.endswith(".inp")]
        mod_files = [f for f in os.listdir(MODIFIED_DIR) if f.endswith(".inp")]
        
        output = "--- ORIGINAL NETWORKS ---\n" + ("\n".join(net_files) if net_files else "None")
        output += "\n\n--- MODIFIED NETWORKS ---\n" + ("\n".join(mod_files) if mod_files else "None")
        return output
    except Exception as e:
        return str(e)

# --- Tools: All now use the universal search logic ---

@mcp.tool()
def run_epanet_simulation(file_name: str) -> str:
    """Runs a full simulation on any network (Original or Modified)."""
    try:
        start = time.time()
        network, results = _load_and_simulate(file_name)
        
        junc_idx = np.array(network.getNodeJunctionIndex()) - 1
        pressures = results.Pressure[0, junc_idx]
        stats = (
            f"Results for: {file_name}\n"
            f"Source Path: {_get_full_path(file_name)}\n"
            f"Nodes: {network.getNodeJunctionCount()} | Pipes: {len(network.getLinkIndex())}\n"
            f"Min Pressure: {np.min(pressures):.2f} Meters  | Max Velocity: {np.max(results.Velocity[0]):.2f} m/s"
        )
        return stats
    except Exception as e: return str(e)

@mcp.tool()
def modify_network(file_name: str, interventions: list[Intervention]) -> str:
    """
    Apply engineering interventions using the structured Intervention model.
    """
    try:
        full_path = _get_full_path(file_name)
        network = epanet(full_path, display_msg=False, display_warnings=False)
        log = []

        for task in interventions:
            # NO MORE .get()! Use task.attribute
            action = task.action.lower()
            item_id = task.id

            if action == "status":
                idx = network.getLinkIndex(item_id)
                # Accessing .value directly from the object
                status_val = 1 if task.value.lower() == "open" else 0
                network.setLinkStatus(idx, status_val)                           #FIX this is not reflected in the saved inp file.
                log.append(f"Set status of {item_id} to {task.value}")

            elif action == "add_pipe":
                # Use the names defined in your Pydantic model
                network.addLinkPipe(item_id, task.from_node, task.to_node)
                if task.diameter:
                    idx = network.getLinkIndex(item_id)
                    network.setLinkDiameter(idx, task.diameter)
                log.append(f"Added pipe {item_id} ({task.from_node} -> {task.to_node})")

            elif action == "set_diameter":
                idx = network.getLinkIndex(item_id)
                network.setLinkDiameter(idx, task.diameter)
                log.append(f"Updated {item_id} diameter to {task.diameter}")

            elif action == "delete_pipe":
                idx = network.getLinkIndex(item_id)
                network.deleteLink(idx)
                log.append(f"Removed pipe {item_id}")

        # Save logic
        base = os.path.basename(file_name)
        save_name = base if base.startswith("Modified_") else f"Modified_{base}"
        save_path = os.path.join(MODIFIED_DIR, save_name)
        network.saveInputFile(save_path)

        return f"Successfully modified {save_name}:\n" + "\n".join([f"• {l}" for l in log])

    except Exception as e:
        # This will now catch specific Pydantic errors if they occur
        return f"Modification failed: {str(e)}"
    
    
@mcp.tool()
def plot_pressures(file_name: str, low_threshold: float = 20.0, only_critical: bool = False) -> list:
    """
    Plots node pressures with an option to filter only for critical nodes.
    
    Args:
        file_name: Name of the .inp file.
        low_threshold: Pressure threshold for highlighting/filtering.
        only_critical: If True, only nodes below the threshold will be shown in the plot.
    """
    try:
        network, results = _load_and_simulate(file_name)
        idx = np.array(network.getNodeJunctionIndex()) - 1
        all_pressures = results.Pressure[0, idx]
        all_names = [network.getNodeNameID(i + 1) for i in idx]

        # Filtering Logic
        if only_critical:
            # Keep only nodes where pressure < threshold
            plot_data = [(n, p) for n, p in zip(all_names, all_pressures) if p < low_threshold]
            if not plot_data:
                return [f"No nodes found below {low_threshold} Meters in {file_name}."]
            
            names, pressures = zip(*plot_data)
            colors = ['#ff4d4d'] * len(pressures) # All will be red
            title_suffix = f"(Only Nodes < {low_threshold} Meters)"
        else:
            names, pressures = all_names, all_pressures
            colors = ['#ff4d4d' if p < low_threshold else '#87ceeb' for p in pressures]
            title_suffix = ""

        # Count total critical nodes for the summary regardless of plot view
        low_count = sum(1 for p in all_pressures if p < low_threshold)

        plot_img = _create_plot_image(
            names, pressures, 
            f"Node Pressures: {file_name} {title_suffix}", 
            "Node ID", "Pressure (Meters)", 
            colors=colors
        )

        return [
            plot_img,
            f"Summary for {file_name}:\n"
            f"• Total Network Junctions: {len(all_pressures)}\n"
            f"• 🔴 Critical Nodes (< {low_threshold} Meters): {low_count}\n"
            f"• Showing {len(names)} nodes in the current plot."
        ]
    except Exception as e:
        return [f"Error: {str(e)}"]

@mcp.tool()
def plot_velocities(file_name: str, low_threshold: float = 0.5, only_critical: bool = False) -> list:
    """
    Plots pipe velocities. Highlights pipes with low velocity (potential stagnation).
    
    Args:
        file_name: Name of the .inp file.
        low_threshold: Velocity below which pipes are highlighted (default 0.5 m/s).
        only_critical: If True, only pipes below the threshold will be shown.
    """
    try:
        network, results = _load_and_simulate(file_name)
        all_vels = results.Velocity[0]
        all_names = [network.getLinkNameID(i + 1) for i in range(len(all_vels))]

        # Filtering Logic
        if only_critical:
            # Keep only pipes where velocity < threshold
            plot_data = [(n, v) for n, v in zip(all_names, all_vels) if v < low_threshold]
            if not plot_data:
                return [f"Great news! No pipes found with velocity below {low_threshold} m/s in {file_name}."]
            
            names, vels = zip(*plot_data)
            colors = ['#ff4d4d'] * len(vels) # All critical shown as red
            title_suffix = f"(Only Pipes < {low_threshold} m/s)"
        else:
            names, vels = all_names, all_vels
            # Red for stagnant (<0.5), Green for healthy (>=0.5)
            colors = ['#ff4d4d' if v < low_threshold else '#2ecc71' for v in vels]
            title_suffix = ""

        # Global count for the summary
        low_count = sum(1 for v in all_vels if v < low_threshold)
        healthy_count = len(all_vels) - low_count

        plot_img = _create_plot_image(
            names, vels, 
            f"Pipe Velocities: {file_name} {title_suffix}", 
            "Pipe ID", "Velocity (m/s)", 
            colors=colors
        )

        return [
            plot_img,
            f"Velocity Analysis for {file_name}:\n"
            f"• Total Network Pipes: {len(all_vels)}\n"
            f"• 🔴 Stagnant/Low Flow (< {low_threshold} m/s): {low_count}\n"
            f"• 🟢 Healthy Flow (≥ {low_threshold} m/s): {healthy_count}\n"
            f"• Showing {len(names)} pipes in this view."
        ]
    except Exception as e:
        return [f"Error during velocity plotting: {str(e)}"]


@mcp.tool()
def get_pressures_less_than(file_name: str, threshold: float) -> str:
    """Filters nodes by pressure threshold in any network."""
    try:
        network, results = _load_and_simulate(file_name)
        idx = np.array(network.getNodeJunctionIndex()) - 1
        p = results.Pressure[0, idx]
        hits = np.where(p < threshold)[0]
        report = {network.getNodeNameID(idx[i]+1): round(p[i], 2) for i in hits}
        return f"Nodes under {threshold} in {file_name}: {report}" if report else "None found."
    except Exception as e: return str(e)

@mcp.tool()
def get_pipes_over(file_name: str, threshold: float) -> str:
    """Filters pipes by velocity threshold in any network."""
    try:
        network, results = _load_and_simulate(file_name)
        v = results.Velocity[0]
        hits = np.where(v > threshold)[0]
        report = {network.getLinkNameID(i+1): round(v[i], 2) for i in hits}
        return f"Pipes over {threshold} in {file_name}: {report}" if report else "None found."
    except Exception as e: return str(e)

if __name__ == "__main__":
    mcp.run()