
# Blender_Exporter

# Important:
- The exporter assumes the mesh is triangulated!
- Indices currently hard coded to u16

## TODO:
- Specify the byte endianness
- Vertex coloring
- Keyframe animations
- Natively compiled exporter (Python script shell calls to shared library exporter):
    - Parallel export on meshes and vertex attributes of sufficient size, including tangent frame fixups
    - Optional meshoptimizer integration
