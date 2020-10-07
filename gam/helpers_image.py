import itk

def update_image_py_to_cpp(py_img, cpp_img, rotation):
    cpp_img.set_spacing(py_img.GetSpacing())
    cpp_img.set_origin(py_img.GetOrigin())
    cpp_img.set_direction(rotation)
    # I dont know to convert GetDirection into something for set_direction
    arr = itk.array_view_from_image(py_img)
    cpp_img.from_pyarray(arr)