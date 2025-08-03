import os
import subprocess
import rasterio
import numpy as np

def apply_rtc(input_files, output_dir='processed', dem='SRTM 1Sec HGT'):
    """
    Apply Radiometric Terrain Correction (RTC) to Sentinel-1 data.
    This function uses SNAP's graph processing tool (gpt) to apply terrain correction.
    
    Parameters
    ----------
    input_files : list
        List of input Sentinel-1 file paths
    output_dir : str, optional
        Directory to save processed files, by default 'processed'
    dem : str, optional
        Digital Elevation Model to use, by default 'SRTM 1Sec HGT'
    
    Returns
    -------
    list
        List of processed file paths
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    processed_files = []
    
    for input_file in input_files:
        try:
            # Get base filename without extension
            base_name = os.path.basename(input_file)
            base_name = os.path.splitext(base_name)[0]
            
            # Output file path
            output_file = os.path.join(output_dir, f"{base_name}_RTC.tif")
            
            # Create XML graph for SNAP GPT
            graph_file = create_rtc_graph(input_file, output_file, dem)
            
            # Run SNAP GPT
            cmd = f"gpt {graph_file}"
            print(f"Running: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
            
            # Check if output file exists
            if os.path.exists(output_file):
                processed_files.append(output_file)
                print(f"Successfully processed {input_file} to {output_file}")
            else:
                print(f"Failed to process {input_file}")
                
        except Exception as e:
            print(f"Error processing {input_file}: {e}")
    
    return processed_files

def create_rtc_graph(input_file, output_file, dem):
    """
    Create XML graph for SNAP GPT to apply Radiometric Terrain Correction.
    
    Parameters
    ----------
    input_file : str
        Input file path
    output_file : str
        Output file path
    dem : str
        Digital Elevation Model to use
    
    Returns
    -------
    str
        Path to created graph XML file
    """
    # Create temporary directory for graph file
    os.makedirs('temp', exist_ok=True)
    graph_file = os.path.join('temp', 'rtc_graph.xml')
    
    # Create XML graph
    graph_xml = f"""<graph id="Graph">
  <version>1.0</version>
  <node id="Read">
    <operator>Read</operator>
    <sources/>
    <parameters>
      <file>{input_file}</file>
    </parameters>
  </node>
  <node id="Apply-Orbit-File">
    <operator>Apply-Orbit-File</operator>
    <sources>
      <sourceProduct refid="Read"/>
    </sources>
    <parameters>
      <orbitType>Sentinel Precise (Auto Download)</orbitType>
      <polyDegree>3</polyDegree>
      <continueOnFail>false</continueOnFail>
    </parameters>
  </node>
  <node id="Calibration">
    <operator>Calibration</operator>
    <sources>
      <sourceProduct refid="Apply-Orbit-File"/>
    </sources>
    <parameters>
      <outputSigmaBand>true</outputSigmaBand>
      <outputGammaBand>false</outputGammaBand>
      <outputBetaBand>false</outputBetaBand>
    </parameters>
  </node>
  <node id="Speckle-Filter">
    <operator>Speckle-Filter</operator>
    <sources>
      <sourceProduct refid="Calibration"/>
    </sources>
    <parameters>
      <filter>Lee</filter>
      <filterSizeX>5</filterSizeX>
      <filterSizeY>5</filterSizeY>
    </parameters>
  </node>
  <node id="Terrain-Correction">
    <operator>Terrain-Correction</operator>
    <sources>
      <sourceProduct refid="Speckle-Filter"/>
    </sources>
    <parameters>
      <demName>{dem}</demName>
      <pixelSpacingInMeter>10.0</pixelSpacingInMeter>
      <mapProjection>EPSG:4326</mapProjection>
      <nodataValueAtSea>true</nodataValueAtSea>
      <saveSelectedSourceBand>true</saveSelectedSourceBand>
      <outputComplex>false</outputComplex>
      <applyRadiometricNormalization>true</applyRadiometricNormalization>
      <saveSigmaNought>true</saveSigmaNought>
      <saveGammaNought>false</saveGammaNought>
      <saveBetaNought>false</saveBetaNought>
      <incidenceAngleForSigma0>Use projected local incidence angle from DEM</incidenceAngleForSigma0>
    </parameters>
  </node>
  <node id="Write">
    <operator>Write</operator>
    <sources>
      <sourceProduct refid="Terrain-Correction"/>
    </sources>
    <parameters>
      <file>{output_file}</file>
      <formatName>GeoTIFF</formatName>
    </parameters>
  </node>
</graph>"""
    
    # Write graph to file
    with open(graph_file, 'w') as f:
        f.write(graph_xml)
    
    return graph_file