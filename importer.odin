vec3_f32 :: struct {
    x,y,z: f32,
}

uv_f32 :: struct {
    u,v: f32,
}

object_format :: struct {
    positions: []vec3_f32,
    normals: []vec3_f32,
    tangents: []vec3_f32,
    uvs: []uv_f32,
    indices: []u16,
    bitangent_signs: []u8,
}

object_headers :: struct {
    header: u64,
    version: u64,
    position_header: u64,
    normal_header: u64,
    tangent_header: u64,
    uv_header: u64,
    index_header: u64,
    bitangent_sign_header: u64,
    footer: u64,
}

main :: proc() {

    object := object_format{}
    stack_space := [4096*8]u128{}
    {
        blah_fd, _ := os.open("/path/to/Suzanne.blah")
        assert(blah_fd != os.INVALID_HANDLE)
        defer os.close(blah_fd)

        bytes_read, read_result := os.read(blah_fd, mem.slice_to_bytes(stack_space[:]))
        assert(read_result == os.ERROR_NONE)
        assert(bytes_read <= size_of(stack_space))

        {
            object_version_0_headers := object_headers {
                header = 0x0123456789ABCDEF,
                version = 0,
                position_header = 0xABCDEF,
                normal_header = 0xFEDCBA,
                tangent_header = 0xF5E4D3C2B1A0,
                uv_header = 0xFEEDBEEF,
                index_header = 0x0A1B2C3D4E5F,
                bitangent_sign_header = 0x0123456789,
                footer = 0xFEDCBA9876543210,
            }

            ptr := uintptr(&stack_space[0])
            assert((^u64)(ptr)^ == object_version_0_headers.header)

            ptr += size_of(u64)
            assert((^u64)(ptr)^ == object_version_0_headers.version)

            ptr += size_of(u64)
            number_of_verts := (^u64)(ptr)^

            ptr += size_of(u64)
            number_of_indices := (^u64)(ptr)^

            ptr += size_of(u64)
            assert((^u64)(ptr)^ == object_version_0_headers.position_header)

            ptr += size_of(u64)
            object.positions = transmute(type_of(object.positions)) runtime.Raw_Slice {
                data = rawptr(ptr),
                len = int(number_of_verts),
            }

            ptr += uintptr(slice.bytes_count(object.positions))
            assert((^u64)(ptr)^ == object_version_0_headers.normal_header)

            ptr += size_of(u64)
            object.normals = transmute(type_of(object.normals)) runtime.Raw_Slice {
                data = rawptr(ptr),
                len = int(number_of_verts),
            }

            ptr += uintptr(slice.bytes_count(object.normals))
            assert((^u64)(ptr)^ == object_version_0_headers.tangent_header)

            ptr += size_of(u64)
            object.tangents = transmute(type_of(object.tangents)) runtime.Raw_Slice {
                data = rawptr(ptr),
                len = int(number_of_verts),
            }

            ptr += uintptr(slice.bytes_count(object.tangents))
            assert((^u64)(ptr)^ == object_version_0_headers.uv_header)

            ptr += size_of(u64)
            object.uvs = transmute(type_of(object.uvs)) runtime.Raw_Slice {
                data = rawptr(ptr),
                len = int(number_of_verts),
            }

            ptr += uintptr(slice.bytes_count(object.uvs))
            assert((^u64)(ptr)^ == object_version_0_headers.index_header)

            ptr += size_of(u64)
            object.indices = transmute(type_of(object.indices)) runtime.Raw_Slice {
                data = rawptr(ptr),
                len = int(number_of_indices),
            }

            ptr += uintptr(slice.bytes_count(object.indices))
            assert((^u64)(ptr)^ == object_version_0_headers.bitangent_sign_header)

            ptr += size_of(u64)
            object.bitangent_signs = transmute(type_of(object.bitangent_signs)) runtime.Raw_Slice {
                data = rawptr(ptr),
                len = int(number_of_verts),
            }

            ptr += uintptr(slice.bytes_count(object.bitangent_signs))
            assert((^u64)(ptr)^ == object_version_0_headers.footer)
        }
    }

    fmt.println(object)
}
