import bpy
import os
import numpy as np
from bpy_extras.io_utils import axis_conversion

def main():
    basedir = os.path.dirname(bpy.data.filepath)

    if not basedir:
        raise Exception("Blend file is not saved")

    view_layer = bpy.context.view_layer

    obj_active = view_layer.objects.active
    selection = bpy.context.selected_objects

    bpy.ops.object.select_all(action='DESELECT')

    object_data_format_header_magic_number = np.uint64(0x0123456789ABCDEF)
    object_data_format_footer_magic_number = np.uint64(0xFEDCBA9876543210)
    object_data_format_version_number = np.uint64(0)
    position_header_magic_number = np.uint64(0xABCDEF)
    normal_header_magic_number = np.uint64(0xFEDCBA)
    tangent_header_magic_number = np.uint64(0xF5E4D3C2B1A0)
    bitangent_sign_header_magic_number = np.uint64(0x0123456789)
    uv_header_magic_number = np.uint64(0xFEEDBEEF)
    index_header_magic_number = np.uint64(0x0A1B2C3D4E5F)

    blender_to_export_axis_transform = axis_conversion(from_forward='-Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
    export_axis_to_blender_transform= blender_to_export_axis_transform.inverted()

    for obj in selection:
        obj.select_set(True)
        view_layer.objects.active = obj

        name = bpy.path.clean_name(obj.name)
        fn = os.path.join(basedir, name)

        obj.data.transform(blender_to_export_axis_transform)
        
        mesh_data = obj.data        
        mesh_data.calc_tangents() #NOTE(Jesse): Apparently this *must* be called before any other handle to geometry is acquired.

        uv_data = mesh_data.uv_layers.active.data
        loops = mesh_data.loops
        loop_count = len(loops)
        vertices = mesh_data.vertices

        unique_verts = {}
        indices = np.zeros(loop_count, dtype=np.uint16)
        latest_index = 0
        for i, loop in enumerate(loops):
            vert = (vertices[loop.vertex_index].co[:], loop.normal[:], loop.tangent[:], uv_data[loop.index].uv[:], loop.bitangent_sign, loop.vertex_index)
            if vert in unique_verts:
                indices[i] = unique_verts[vert]
            else:
                unique_verts[vert] = latest_index
                indices[i] = latest_index
                latest_index += 1
          
        #NOTE(Jesse): There is an open question about how to handle tangent frames along UV splits, especially for HP -> LP baked normal map models.
        #             Should such shared vertices with identical UVs but *slightly* differing tangents have their tangents averaged?
        #             The routine below has not been seriously verified but does work on simple meshes.

        fixup_tangent_frames = True
        if fixup_tangent_frames:
            unique_verts = [list(key) for key in unique_verts]

            vert_idx_table = [[] for _ in range(len(mesh_data.vertices))] #TODO(Jesse): This could be a list of *sets* to leverage the fact that most shared vertices *are* identical, and that insertion order is not a constraint.
            for i, vert in enumerate(unique_verts):
                vert_idx = vert[5]
                vert_idx_table[vert_idx].append(i)

            for vert_idx_slot in vert_idx_table:
                if len(vert_idx_slot) <= 1:
                    continue

                #NOTE(Jesse): Only average tangents whose bitangent signs are equal.
                positive_bitangents_vert_idxs = []
                negative_bitangents_vert_idxs = []
                pn_bitangents_vert_idxs = (positive_bitangents_vert_idxs, negative_bitangents_vert_idxs)

                for vert_idx in vert_idx_slot:
                    if unique_verts[vert_idx][4] > 0:
                        pn_bitangents_vert_idxs[0].append(vert_idx)
                    else:
                        pn_bitangents_vert_idxs[1].append(vert_idx)

                for pn_bitangent_vert_idxs in pn_bitangents_vert_idxs:
                    if len(pn_bitangent_vert_idxs) <= 1:
                        continue

                    unique_vert_v1 = unique_verts[pn_bitangent_vert_idxs[0]]
                    v_uv = unique_vert_v1[3]
                    v_tangent = unique_vert_v1[2]

                    vert_indices_to_average_tangents = []
                    for ii in pn_bitangent_vert_idxs[1:]:
                        unique_vert_vn = unique_verts[ii]
                        v2_uv = unique_vert_vn[3]
                        if v_uv != v2_uv: #NOTE(Jesse): Using a set above would eliminate this check.
                            continue
            
                        v2_tangent = unique_vert_vn[2]
                        v_dot_v2 = np.dot(v_tangent, v2_tangent)
                        
                        if v_dot_v2 < 0.95:
                            continue
                        
                        #NOTE(Jesse): The tangents differ slightly causing shading discontinuities.
                        vert_indices_to_average_tangents.append(ii)
                
                    if len(vert_indices_to_average_tangents) == 0:
                        continue
                    
                    average_tangent = np.array(v_tangent, dtype=np.float32)
                    for idx in vert_indices_to_average_tangents:
                        average_tangent += unique_verts[idx][2]
                    
                    average_tangent *= 0.5 * len(vert_indices_to_average_tangents)

                    unique_vert_v1[2] = average_tangent
                    for idx in vert_indices_to_average_tangents:
                        unique_verts[idx][2] = average_tangent

        num_of_unique_vertices = len(unique_verts)
        positions = np.zeros(num_of_unique_vertices * 3, dtype=np.float32)
        normals = np.zeros(num_of_unique_vertices * 3, dtype=np.float32)
        tangents = np.zeros(num_of_unique_vertices * 3, dtype=np.float32)
        uvs = np.zeros(num_of_unique_vertices * 2, dtype=np.float32)
        bitangent_signs = np.zeros(num_of_unique_vertices, dtype=np.int8)
        
        for i, vert in enumerate(unique_verts):
            v3_offset_start = i * 3
            v3_offset_end = v3_offset_start + 3
            
            v2_offset_start = i * 2 
            v2_offset_end = v2_offset_start + 2
            
            positions[v3_offset_start : v3_offset_end] = vert[0]
            normals[v3_offset_start : v3_offset_end] = vert[1]
            tangents[v3_offset_start : v3_offset_end] = vert[2]
            uvs[v2_offset_start : v2_offset_end] = vert[3]
            bitangent_signs[i] = vert[4]
        
        with open(fn + ".blah", "wb") as fh:
            #TODO(Jesse): 8 byte alignment? CRC? Multiple UV layouts.
            #NOTE(Jesse): Format is, tightly byte packed, each 8 bytes:
            # magic header () u64
            #
            # version number (aligned to 8 bytes) u64
            #
            # number of verts (aligned to 8 bytes) u64
            #
            # number of indices
            #
            # position header
            # position data (aligned to 4 bytes) each vert is 3 float32
            #
            # normal header
            # normal data (aligned to 4 bytes) each normal is 3 float32
            #
            # tangent header
            # tangent data (aligned to 4 bytes) each tangent is 3 float32
            #
            # uv header
            # uv data (aligned to 4 bytes) each uv is 2 float32
            #
            # index header
            # index data (aligned to 4 bytes) each index is 1 uint16
            #
            # bitangent sign header
            # bitangent data (aligned to 2 bytes) each element is 1 uint8
            #
            # magic footer (aligned to 1 byte) u64
            
            fh.write(object_data_format_header_magic_number)
            fh.write(object_data_format_version_number)

            fh.write(np.uint64(num_of_unique_vertices))
            fh.write(np.uint64(loop_count))
            
            fh.write(position_header_magic_number)
            fh.write(positions)
            
            fh.write(normal_header_magic_number)
            fh.write(normals)
            
            fh.write(tangent_header_magic_number)
            fh.write(tangents)
            
            fh.write(uv_header_magic_number)
            fh.write(uvs)
            
            fh.write(index_header_magic_number)
            fh.write(indices)

            fh.write(bitangent_sign_header_magic_number)
            fh.write(bitangent_signs)
            
            fh.write(object_data_format_footer_magic_number)
            #TODO(Jesse): fh.write(CRC)
        
        obj.select_set(False)

        print(f"Exported {obj.name}")
        obj.data.transform(export_axis_to_blender_transform)

    view_layer.objects.active = obj_active

    for obj in selection:
        obj.select_set(True)

main()
