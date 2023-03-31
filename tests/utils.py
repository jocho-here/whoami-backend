def create_temp_image_file(tmp_path: str, name: str):
    import os

    # Create a temp image file and return the path to it
    d = tmp_path / "sub"

    if not os.path.isdir(d):
        d.mkdir()

    p = d / f"{name}"
    p.write_text("hi!")

    return p
